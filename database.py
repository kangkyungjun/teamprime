"""
데이터베이스 모듈
- 데이터베이스 연결 및 초기화
- 캔들 데이터 CRUD 함수들
- 데이터 동기화 함수들
"""

import asyncio
import re
import aiohttp
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict
from sqlalchemy import (
    MetaData, Table, Column, String, Integer, Float, create_engine,
    text, select, insert, PrimaryKeyConstraint
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import os
from dotenv import load_dotenv

# 설정 로드
load_dotenv()

# 데이터베이스 설정
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./upbit_candles.db")
UPBIT_BASE = "https://api.upbit.com"
DEFAULT_YEARS = int(os.getenv("YEARS", "3"))
BATCH = 200  # Upbit candles limit

# 데이터베이스 스키마 정의
metadata = MetaData()

candles_table = Table(
    "candles",
    metadata,
    Column("market", String, nullable=False),
    Column("unit", Integer, nullable=False), 
    Column("ts", Integer, nullable=False),
    Column("open", Float, nullable=False),
    Column("high", Float, nullable=False),
    Column("low", Float, nullable=False),
    Column("close", Float, nullable=False),
    Column("volume", Float, nullable=False),
    PrimaryKeyConstraint("market", "unit", "ts")
)

ticks_table = Table(
    "ticks",
    metadata,
    Column("market", String, nullable=False),
    Column("timestamp", Integer, nullable=False),
    Column("trade_price", Float, nullable=False),
    Column("trade_volume", Float, nullable=False),
    Column("ask_bid", String, nullable=False),
    Column("ts_minute", Integer, nullable=False),
    PrimaryKeyConstraint("market", "timestamp")
)

orderbook_snapshots_table = Table(
    "orderbook_snapshots",
    metadata,
    Column("market", String, nullable=False),
    Column("timestamp", Integer, nullable=False),
    # 추가 호가창 데이터 필드들
    PrimaryKeyConstraint("market", "timestamp")
)

trading_logs_table = Table(
    "trading_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", Integer, nullable=False),
    Column("market", String, nullable=False),
    Column("action", String, nullable=False),  # buy, sell
    Column("price", Float, nullable=False),
    Column("amount", Float, nullable=False),
    Column("total", Float, nullable=False),
    Column("profit_loss", Float, nullable=True),
    Column("reason", String, nullable=True),
    Column("signal_data", String, nullable=True)
)

# 데이터베이스 엔진
async_engine: AsyncEngine = create_async_engine(DB_URL, future=True, echo=False)

# FastAPI 의존성용 데이터베이스 세션
async def get_db():
    """FastAPI 의존성용 데이터베이스 세션 생성"""
    async with async_engine.begin() as conn:
        yield conn

# 유틸리티 함수들
UTC = timezone.utc

def utc_now() -> datetime:
    return datetime.now(tz=UTC)

def iso_utc(ts: datetime) -> str:
    """업비트 API용 UTC 시간 문자열 생성"""
    return ts.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")

def dt_to_epoch_s(dt: datetime) -> int:
    """datetime을 epoch 초로 변환"""
    return int(dt.replace(tzinfo=UTC).timestamp())

def parse_minutes_payload(item: dict) -> tuple:
    """업비트 API 응답을 파싱하여 튜플로 변환"""
    k = item["candle_date_time_utc"]  # e.g. "2025-08-15T11:24:00"
    k = re.sub("Z$", "", k).replace("T", " ")
    dt = datetime.strptime(k, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    ts = dt_to_epoch_s(dt)
    return (
        ts,
        float(item["opening_price"]),
        float(item["high_price"]),
        float(item["low_price"]),
        float(item["trade_price"]),
        float(item["candle_acc_trade_volume"]),
    )

async def init_db():
    """데이터베이스 초기화"""
    async with async_engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

async def respect_rate_limit(resp: aiohttp.ClientResponse):
    """API 레이트 리밋 준수"""
    hdr = resp.headers.get("Remaining-Req", "")
    m = re.search(r"sec=(\d+)", hdr)
    if m:
        remaining = int(m.group(1))
        if remaining <= 1:
            await asyncio.sleep(1.0)
        elif remaining <= 3:
            await asyncio.sleep(0.5)
        elif remaining <= 8:
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(0.1)
    else:
        await asyncio.sleep(0.1)

async def fetch_minutes(
    session: aiohttp.ClientSession,
    market: str, unit: int, to_dt: Optional[datetime] = None, count: int = BATCH
) -> List[dict]:
    """업비트에서 분봉 데이터 가져오기"""
    params = {"market": market, "count": str(count)}
    if to_dt is not None:
        params["to"] = iso_utc(to_dt)
    url = f"{UPBIT_BASE}/v1/candles/minutes/{unit}"
    
    # 429 에러 재시도 로직
    for retry in range(3):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 429:
                    wait_time = 2 ** retry
                    print(f"⏳ API 레이트 리밋 - {wait_time}초 대기 중... ({market} {unit}분봉)")
                    await asyncio.sleep(wait_time)
                    continue
                    
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Upbit {unit}m fetch error {resp.status}: {text}")
                    
                data = await resp.json()
                await respect_rate_limit(resp)
                return data
        except asyncio.TimeoutError:
            if retry < 2:
                print(f"⏳ 타임아웃 재시도 중... ({market} {unit}분봉)")
                await asyncio.sleep(1)
                continue
            raise RuntimeError(f"Upbit {unit}m fetch timeout after 3 retries")
    
    raise RuntimeError(f"Upbit {unit}m fetch failed after 3 retries (rate limit)")

async def upsert_candles(rows: List[tuple], market: str, unit: int):
    """캔들 데이터 업서트"""
    if not rows:
        return
    
    async with async_engine.begin() as conn:
        for row in rows:
            ts, o, h, l, c, v = row
            stmt = text("""
                INSERT INTO candles (market, unit, ts, open, high, low, close, volume) 
                VALUES (:market, :unit, :ts, :open, :high, :low, :close, :volume)
                ON CONFLICT(market, unit, ts) DO NOTHING
            """)
            await conn.execute(stmt, {
                "market": market, "unit": unit, "ts": ts,
                "open": o, "high": h, "low": l, "close": c, "volume": v
            })

async def insert_trading_log(
    market: str,
    action: str,
    price: float,
    amount: float,
    total: float,
    profit_loss: Optional[float] = None,
    reason: Optional[str] = None,
    signal_data: Optional[str] = None
):
    """거래 로그 삽입"""
    async with async_engine.begin() as conn:
        stmt = insert(trading_logs_table).values(
            timestamp=int(datetime.now().timestamp()),
            market=market,
            action=action,
            price=price,
            amount=amount,
            total=total,
            profit_loss=profit_loss,
            reason=reason,
            signal_data=signal_data
        )
        await conn.execute(stmt)

async def get_min_max_ts(market: str, unit: int):
    """캔들 데이터의 최소/최대 타임스탬프 조회"""
    async with async_engine.begin() as conn:
        stmt = text("SELECT MIN(ts), MAX(ts) FROM candles WHERE market=:market AND unit=:unit")
        result = await conn.execute(stmt, {"market": market, "unit": unit})
        row = result.fetchone()
        return row if row else (None, None)

async def get_coin_data_range(market: str) -> dict:
    """코인 데이터 범위 조회"""
    result = {}
    units = [1, 5, 15]
    
    async with async_engine.begin() as conn:
        for unit in units:
            stmt = text("""
                SELECT MIN(ts) as min_ts, MAX(ts) as max_ts, COUNT(*) as count
                FROM candles 
                WHERE market = :market AND unit = :unit
            """)
            row = await conn.execute(stmt, {"market": market, "unit": unit})
            data = row.fetchone()
            
            if data and data[0] is not None:
                min_dt = datetime.fromtimestamp(data[0], tz=UTC)
                max_dt = datetime.fromtimestamp(data[1], tz=UTC)
                days = (max_dt - min_dt).days
                result[f"{unit}min"] = {
                    "start": min_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "end": max_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "days": days,
                    "count": data[2]
                }
            else:
                result[f"{unit}min"] = {
                    "start": None,
                    "end": None,
                    "days": 0,
                    "count": 0
                }
    
    return result

async def fetch_tick_data(session: aiohttp.ClientSession, market: str, count: int = 200):
    """틱 데이터 가져오기"""
    url = f"{UPBIT_BASE}/v1/trades/ticks"
    params = {"market": market, "count": str(count)}
    
    for retry in range(3):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 429:
                    wait_time = 2 ** retry
                    print(f"⏳ API 레이트 리밋 - {wait_time}초 대기 중... ({market} 틱)")
                    await asyncio.sleep(wait_time)
                    continue
                    
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Upbit tick fetch error {resp.status}: {text}")
                    
                data = await resp.json()
                await respect_rate_limit(resp)
                return data
        except asyncio.TimeoutError:
            if retry < 2:
                print(f"⏳ 틱 데이터 타임아웃 재시도 중... ({market})")
                await asyncio.sleep(1)
                continue
            raise RuntimeError(f"Upbit tick fetch timeout after 3 retries")
    
    raise RuntimeError(f"Upbit tick fetch failed after 3 retries (rate limit)")

async def fetch_orderbook_data(session: aiohttp.ClientSession, market: str):
    """호가창 데이터 가져오기"""
    url = f"{UPBIT_BASE}/v1/orderbook"
    params = {"markets": market}
    
    for retry in range(3):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 429:
                    wait_time = 2 ** retry
                    print(f"⏳ API 레이트 리밋 - {wait_time}초 대기 중... ({market} 호가창)")
                    await asyncio.sleep(wait_time)
                    continue
                    
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Upbit orderbook fetch error {resp.status}: {text}")
                    
                data = await resp.json()
                await respect_rate_limit(resp)
                return data
        except asyncio.TimeoutError:
            if retry < 2:
                print(f"⏳ 호가창 데이터 타임아웃 재시도 중... ({market})")
                await asyncio.sleep(1)
                continue
            raise RuntimeError(f"Upbit orderbook fetch timeout after 3 retries")
    
    raise RuntimeError(f"Upbit orderbook fetch failed after 3 retries (rate limit)")

async def generate_5min_candles_from_1min(market: str):
    """1분봉에서 5분봉 생성"""
    async with async_engine.begin() as conn:
        stmt = text("""
            INSERT OR IGNORE INTO candles (market, unit, ts, open, high, low, close, volume)
            SELECT 
                market,
                5 as unit,
                (ts / 300) * 300 as ts_5min,
                (SELECT open FROM candles c2 WHERE c2.market = c1.market AND c2.unit = 1 
                 AND c2.ts >= (c1.ts / 300) * 300 AND c2.ts < ((c1.ts / 300) + 1) * 300 
                 ORDER BY c2.ts LIMIT 1) as open,
                MAX(high) as high,
                MIN(low) as low,
                (SELECT close FROM candles c3 WHERE c3.market = c1.market AND c3.unit = 1 
                 AND c3.ts >= (c1.ts / 300) * 300 AND c3.ts < ((c1.ts / 300) + 1) * 300 
                 ORDER BY c3.ts DESC LIMIT 1) as close,
                SUM(volume) as volume
            FROM candles c1 
            WHERE c1.market = :market AND c1.unit = 1
            GROUP BY c1.market, (c1.ts / 300) * 300
            HAVING COUNT(*) >= 4  -- 최소 4개 1분봉 필요
        """)
        await conn.execute(stmt, {"market": market})

async def generate_15min_candles_from_1min(market: str):
    """1분봉에서 15분봉 생성"""
    async with async_engine.begin() as conn:
        stmt = text("""
            INSERT OR IGNORE INTO candles (market, unit, ts, open, high, low, close, volume)
            SELECT 
                market,
                15 as unit,
                (ts / 900) * 900 as ts_15min,
                (SELECT open FROM candles c2 WHERE c2.market = c1.market AND c2.unit = 1 
                 AND c2.ts >= (c1.ts / 900) * 900 AND c2.ts < ((c1.ts / 900) + 1) * 900 
                 ORDER BY c2.ts LIMIT 1) as open,
                MAX(high) as high,
                MIN(low) as low,
                (SELECT close FROM candles c3 WHERE c3.market = c1.market AND c3.unit = 1 
                 AND c3.ts >= (c1.ts / 900) * 900 AND c3.ts < ((c1.ts / 900) + 1) * 900 
                 ORDER BY c3.ts DESC LIMIT 1) as close,
                SUM(volume) as volume
            FROM candles c1 
            WHERE c1.market = :market AND c1.unit = 1
            GROUP BY c1.market, (c1.ts / 900) * 900
            HAVING COUNT(*) >= 10  -- 최소 10개 1분봉 필요
        """)
        await conn.execute(stmt, {"market": market})