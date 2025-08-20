"""
데이터 분석 모듈
- 기술적 지표 계산 (EMA, RSI, VWAP)
- 거래량 분석 (폭증 감지, 패턴 분석)
- 매수/매도 비율 분석
- 백테스팅 및 성과 분석
- 패턴 감지 및 신호 생성
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import database

# 유틸리티 함수
UTC = timezone.utc

def utc_now() -> datetime:
    return datetime.now(tz=UTC)

# ===================
# 기술적 지표 계산
# ===================

async def calculate_vwap(market: str, ts_start: int, ts_end: int) -> float:
    """VWAP (거래량 가중 평균가) 계산"""
    sql = """
    SELECT 
        SUM(close * volume) / SUM(volume) as vwap
    FROM candles 
    WHERE market = ? AND unit = 1 AND ts BETWEEN ? AND ?
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, ts_start, ts_end))
        row = result.fetchone()
        return row[0] if row and row[0] else 0


async def calculate_ema(market: str, unit: int, period: int, ts_end: int) -> Optional[float]:
    """EMA 계산 (특정 시점 기준)"""
    sql = """
    SELECT close FROM candles 
    WHERE market = ? AND unit = ? AND ts <= ?
    ORDER BY ts DESC LIMIT ?
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, unit, ts_end, period * 3))
        rows = result.fetchall()
    
    if len(rows) < period:
        return None
    
    # EMA 계산
    prices = [row[0] for row in reversed(rows)]
    multiplier = 2 / (period + 1)
    ema = prices[0]  # 첫 번째 값으로 초기화
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


async def calculate_rsi(market: str, unit: int, period: int, ts_end: int) -> Optional[float]:
    """RSI 계산 (특정 시점 기준)"""
    sql = """
    SELECT close FROM candles 
    WHERE market = ? AND unit = ? AND ts <= ?
    ORDER BY ts DESC LIMIT ?
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, unit, ts_end, period + 1))
        rows = result.fetchall()
    
    if len(rows) < period + 1:
        return None
    
    # 가격 변화량 계산
    prices = [row[0] for row in reversed(rows)]
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    # 초기 평균 계산
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # RSI 계산을 위한 추가 데이터 처리
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


async def calculate_buy_sell_ratio(market: str, ts_start: int, ts_end: int) -> Dict:
    """매수/매도 비율 분석 (틱 데이터 기반)"""
    sql = """
    SELECT 
        ask_bid,
        COUNT(*) as count,
        SUM(trade_volume) as volume,
        SUM(trade_price * trade_volume) as amount
    FROM ticks
    WHERE market = ? AND timestamp BETWEEN ? AND ?
    GROUP BY ask_bid
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, ts_start, ts_end))
        rows = result.fetchall()
    
    buy_data = {"count": 0, "volume": 0, "amount": 0}
    sell_data = {"count": 0, "volume": 0, "amount": 0}
    
    for row in rows:
        ask_bid, count, volume, amount = row
        if ask_bid == "BID":  # 매수
            buy_data = {"count": count, "volume": volume or 0, "amount": amount or 0}
        elif ask_bid == "ASK":  # 매도
            sell_data = {"count": count, "volume": volume or 0, "amount": amount or 0}
    
    total_count = buy_data["count"] + sell_data["count"]
    total_volume = buy_data["volume"] + sell_data["volume"]
    total_amount = buy_data["amount"] + sell_data["amount"]
    
    return {
        "buy_ratio": round(buy_data["count"] / max(total_count, 1) * 100, 2),
        "sell_ratio": round(sell_data["count"] / max(total_count, 1) * 100, 2),
        "buy_volume_ratio": round(buy_data["volume"] / max(total_volume, 1) * 100, 2),
        "sell_volume_ratio": round(sell_data["volume"] / max(total_volume, 1) * 100, 2),
        "buy_amount_ratio": round(buy_data["amount"] / max(total_amount, 1) * 100, 2),
        "sell_amount_ratio": round(sell_data["amount"] / max(total_amount, 1) * 100, 2),
        "total_trades": total_count,
        "analysis_period": f"{datetime.fromtimestamp(ts_start)} ~ {datetime.fromtimestamp(ts_end)}"
    }


# ===================
# 거래량 분석
# ===================

async def volume_surge_analysis(
    market: str,
    surge_threshold: float = 3.0,
    lookback_hours: int = 24
) -> Dict:
    """
    거래량 폭증 분석: 지정된 기간 평균 대비 N배 이상 거래량 폭증한 횟수를 계산
    최적화: 최대 100개 캔들로 제한하여 성능 향상
    """
    
    # 최적화: 최대 100개 캔들로 제한
    lookback_minutes = min(100, lookback_hours * 60)
    
    # SQL 쿼리: 각 시점에서 과거 N시간 평균 거래량 대비 현재 거래량 비율 계산
    sql = f"""
    WITH volume_with_avg AS (
        SELECT 
            ts,
            datetime(ts, 'unixepoch') as time_str,
            volume,
            AVG(volume) OVER (
                ORDER BY ts 
                ROWS BETWEEN {lookback_minutes} PRECEDING AND 1 PRECEDING
            ) as avg_volume_24h
        FROM candles 
        WHERE market = ? AND unit = 1
        ORDER BY ts
    )
    SELECT 
        COUNT(*) as surge_count,
        COUNT(CASE WHEN volume / avg_volume_24h >= ? THEN 1 END) as surge_events,
        MIN(time_str) as data_start,
        MAX(time_str) as data_end,
        AVG(volume / avg_volume_24h) as avg_ratio,
        MAX(volume / avg_volume_24h) as max_ratio
    FROM volume_with_avg 
    WHERE avg_volume_24h > 0
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, surge_threshold))
        row = result.fetchone()
    
    if not row:
        return {"error": "No data found"}
    
    return {
        "market": market,
        "analysis_period": f"{row[2]} ~ {row[3]}",
        "surge_threshold": surge_threshold,
        "lookback_hours": lookback_hours,
        "total_records": row[0],
        "volume_surge_events": row[1],
        "surge_percentage": round((row[1] / row[0]) * 100, 2) if row[0] > 0 else 0,
        "average_volume_ratio": round(row[4], 2) if row[4] else 0,
        "max_volume_ratio": round(row[5], 2) if row[5] else 0,
        "summary": f"지난 기간 동안 {lookback_hours}시간 평균 대비 {surge_threshold}배 이상 거래량 폭증: {row[1]}회"
    }


async def advanced_volume_surge_analysis(
    market: str,
    surge_threshold: float = 3.0,
    lookback_hours: int = 24,
    price_change_threshold: float = 0.3,
    enable_advanced_filters: bool = True,
    enable_trend_filters: bool = False
) -> Dict:
    """
    고급 매수세 기반 거래량 폭증 분석
    - 거래량 폭증 + 가격 상승 + 매수세 우위 조건 통합 분석
    최적화: 최대 100개 캔들로 제한하여 성능 향상
    """
    
    # 최적화: 최대 100개 캔들로 제한
    lookback_minutes = min(100, lookback_hours * 60)
    
    if enable_advanced_filters:
        # 고급 필터 적용
        sql = f"""
        WITH volume_with_indicators AS (
            SELECT 
                ts,
                datetime(ts, 'unixepoch') as time_str,
                open, high, low, close, volume,
                AVG(volume) OVER (
                    ORDER BY ts 
                    ROWS BETWEEN {lookback_minutes} PRECEDING AND 1 PRECEDING
                ) as avg_volume_24h,
                
                -- 가격 변동률 계산
                ((close - open) / open * 100) as price_change_pct,
                
                -- 캔들 위치 분석 (종가가 고가 대비 상단 30% 이내)
                CASE WHEN (close - low) / (high - low) >= 0.7 THEN 1 ELSE 0 END as upper_candle
                
            FROM candles 
            WHERE market = ? AND unit = 1
            ORDER BY ts
        )
        SELECT 
            COUNT(*) as total_count,
            COUNT(CASE WHEN volume / avg_volume_24h >= ? 
                      AND price_change_pct >= ? 
                      AND upper_candle = 1 THEN 1 END) as qualified_signals,
            MIN(time_str) as data_start,
            MAX(time_str) as data_end,
            AVG(volume / avg_volume_24h) as avg_volume_ratio,
            AVG(price_change_pct) as avg_price_change,
            COUNT(CASE WHEN upper_candle = 1 THEN 1 END) as upper_candle_count
        FROM volume_with_indicators 
        WHERE avg_volume_24h > 0
        """
        
        async with database.async_engine.begin() as conn:
            result = await conn.exec_driver_sql(sql, (market, surge_threshold, price_change_threshold))
            row = result.fetchone()
        
        if not row:
            return {"error": "No data found"}
        
        return {
            "market": market,
            "analysis_type": "advanced_volume_surge",
            "analysis_period": f"{row[2]} ~ {row[3]}",
            "surge_threshold": surge_threshold,
            "price_change_threshold": price_change_threshold,
            "total_records": row[0],
            "qualified_signals": row[1],
            "signal_rate": round((row[1] / row[0]) * 100, 2) if row[0] > 0 else 0,
            "avg_volume_ratio": round(row[4], 2) if row[4] else 0,
            "avg_price_change": round(row[5], 2) if row[5] else 0,
            "upper_candle_rate": round((row[6] / row[0]) * 100, 2) if row[0] > 0 else 0,
            "summary": f"고급 필터 적용 결과: {row[1]}개 신호 ({round((row[1] / row[0]) * 100, 2)}%)"
        }
    else:
        # 기본 분석 사용
        return await volume_surge_analysis(market, surge_threshold, lookback_hours)


# ===================
# 백테스팅 및 성과 분석
# ===================

async def calculate_trade_performance(
    market: str, 
    buy_signals: list, 
    profit_target: float = 2.0, 
    stop_loss: float = -1.0, 
    holding_period: int = 60
) -> Dict:
    """거래 성과 분석 (백테스팅)"""
    
    if not buy_signals:
        return {"error": "No buy signals provided"}
    
    trades = []
    total_profit = 0
    winning_trades = 0
    losing_trades = 0
    
    for signal in buy_signals:
        try:
            buy_ts = signal["timestamp"]
            buy_price = signal["close"]
            
            # 보유 기간 내 최고가/최저가 조회
            sql = """
            SELECT MAX(high) as max_high, MIN(low) as min_low, 
                   close as final_close
            FROM candles 
            WHERE market = ? AND unit = 1 
              AND ts BETWEEN ? AND ?
            """
            
            sell_ts = buy_ts + (holding_period * 60)  # 분 단위를 초 단위로 변환
            
            async with database.async_engine.begin() as conn:
                result = await conn.exec_driver_sql(sql, (market, buy_ts, sell_ts))
                row = result.fetchone()
            
            if not row:
                continue
            
            max_high, min_low, final_close = row
            
            # 익절/손절 조건 확인
            max_gain = ((max_high - buy_price) / buy_price) * 100
            max_loss = ((min_low - buy_price) / buy_price) * 100
            final_return = ((final_close - buy_price) / buy_price) * 100
            
            # 거래 결과 결정
            if max_gain >= profit_target:
                # 익절 달성
                profit_pct = profit_target
                sell_reason = "profit_target"
            elif max_loss <= stop_loss:
                # 손절 실행
                profit_pct = stop_loss
                sell_reason = "stop_loss"
            else:
                # 보유 기간 만료
                profit_pct = final_return
                sell_reason = "holding_period_end"
            
            trades.append({
                "buy_timestamp": buy_ts,
                "buy_price": buy_price,
                "profit_pct": profit_pct,
                "sell_reason": sell_reason,
                "max_gain": max_gain,
                "max_loss": max_loss
            })
            
            total_profit += profit_pct
            if profit_pct > 0:
                winning_trades += 1
            else:
                losing_trades += 1
                
        except Exception as e:
            print(f"Trade calculation error: {e}")
            continue
    
    total_trades = len(trades)
    if total_trades == 0:
        return {"error": "No valid trades calculated"}
    
    win_rate = (winning_trades / total_trades) * 100
    avg_return = total_profit / total_trades
    
    return {
        "market": market,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_return": round(total_profit, 2),
        "average_return": round(avg_return, 2),
        "profit_target": profit_target,
        "stop_loss": stop_loss,
        "holding_period_minutes": holding_period,
        "trades": trades[:10]  # 최근 10개 거래만 반환
    }


async def backtest_performance(
    market: str,
    days: int = 30,
    volume_mult: float = 1.5,
    price_change: float = 0.2,
    candle_pos: float = 0.7,
    profit_target: float = 1.0,
    stop_loss: float = -0.5
) -> Dict:
    """백테스팅 성과 분석"""
    
    # 기간 계산
    end_time = int(time.time())
    start_time = end_time - (days * 24 * 60 * 60)
    
    # 매수 신호 생성
    sql = f"""
    WITH signals AS (
        SELECT 
            ts,
            open, high, low, close, volume,
            AVG(volume) OVER (
                ORDER BY ts 
                ROWS BETWEEN 24 PRECEDING AND 1 PRECEDING
            ) as avg_volume,
            ((close - open) / open * 100) as price_change_pct,
            CASE WHEN (close - low) / (high - low) >= ? THEN 1 ELSE 0 END as upper_candle
        FROM candles 
        WHERE market = ? AND unit = 1 
          AND ts BETWEEN ? AND ?
        ORDER BY ts
    )
    SELECT ts, close, volume, avg_volume, price_change_pct, upper_candle
    FROM signals 
    WHERE volume / avg_volume >= ?
      AND price_change_pct >= ?
      AND upper_candle = 1
      AND avg_volume > 0
    ORDER BY ts
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (
            candle_pos, market, start_time, end_time,
            volume_mult, price_change
        ))
        signals = result.fetchall()
    
    if not signals:
        return {
            "error": "No buy signals found",
            "market": market,
            "days": days,
            "parameters": {
                "volume_mult": volume_mult,
                "price_change": price_change,
                "candle_pos": candle_pos,
                "profit_target": profit_target,
                "stop_loss": stop_loss
            }
        }
    
    # 신호를 딕셔너리 형태로 변환
    buy_signals = []
    for signal in signals:
        buy_signals.append({
            "timestamp": signal[0],
            "close": signal[1],
            "volume": signal[2],
            "avg_volume": signal[3],
            "price_change_pct": signal[4],
            "upper_candle": signal[5]
        })
    
    # 성과 분석 실행
    performance = await calculate_trade_performance(
        market, buy_signals, profit_target, stop_loss, 60
    )
    
    # 백테스팅 메타데이터 추가
    performance["backtest_period"] = f"{days} days"
    performance["signal_count"] = len(buy_signals)
    performance["parameters"] = {
        "volume_mult": volume_mult,
        "price_change": price_change,
        "candle_pos": candle_pos,
        "profit_target": profit_target,
        "stop_loss": stop_loss
    }
    
    return performance


# ===================
# 패턴 분석
# ===================

async def analyze_trade_patterns(
    market: str,
    lookback_days: int = 30
) -> Dict:
    """거래 패턴 분석"""
    
    end_time = int(time.time())
    start_time = end_time - (lookback_days * 24 * 60 * 60)
    
    # 시간대별 거래량 패턴 분석
    sql = """
    SELECT 
        strftime('%H', datetime(ts, 'unixepoch')) as hour,
        AVG(volume) as avg_volume,
        AVG(((close - open) / open * 100)) as avg_price_change,
        COUNT(*) as candle_count
    FROM candles 
    WHERE market = ? AND unit = 1 
      AND ts BETWEEN ? AND ?
    GROUP BY strftime('%H', datetime(ts, 'unixepoch'))
    ORDER BY hour
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, start_time, end_time))
        hourly_patterns = result.fetchall()
    
    # 요일별 패턴 분석
    sql = """
    SELECT 
        strftime('%w', datetime(ts, 'unixepoch')) as day_of_week,
        AVG(volume) as avg_volume,
        AVG(((close - open) / open * 100)) as avg_price_change,
        COUNT(*) as candle_count
    FROM candles 
    WHERE market = ? AND unit = 1 
      AND ts BETWEEN ? AND ?
    GROUP BY strftime('%w', datetime(ts, 'unixepoch'))
    ORDER BY day_of_week
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, start_time, end_time))
        daily_patterns = result.fetchall()
    
    # 결과 정리
    hourly_data = []
    for row in hourly_patterns:
        hourly_data.append({
            "hour": int(row[0]),
            "avg_volume": round(row[1], 2),
            "avg_price_change": round(row[2], 4),
            "candle_count": row[3]
        })
    
    daily_data = []
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for row in daily_patterns:
        daily_data.append({
            "day_of_week": int(row[0]),
            "day_name": day_names[int(row[0])],
            "avg_volume": round(row[1], 2),
            "avg_price_change": round(row[2], 4),
            "candle_count": row[3]
        })
    
    return {
        "market": market,
        "analysis_period": f"{lookback_days} days",
        "hourly_patterns": hourly_data,
        "daily_patterns": daily_data,
        "summary": {
            "best_trading_hour": max(hourly_data, key=lambda x: x["avg_volume"])["hour"] if hourly_data else None,
            "best_trading_day": max(daily_data, key=lambda x: x["avg_volume"])["day_name"] if daily_data else None
        }
    }


# ===================
# 실시간 신호 생성
# ===================

async def generate_trading_signal(
    market: str,
    current_price: float,
    volume_data: Dict,
    timeframe: str = "1m"
) -> Dict:
    """실시간 거래 신호 생성"""
    
    current_time = int(time.time())
    
    try:
        # 최근 데이터 기반 분석
        recent_ema = await calculate_ema(market, 1, 12, current_time)
        recent_rsi = await calculate_rsi(market, 1, 14, current_time)
        
        # 거래량 분석
        volume_surge = await volume_surge_analysis(market, 2.0, 1)
        
        # 신호 강도 계산
        signal_strength = 0
        signal_reasons = []
        
        # EMA 신호
        if recent_ema and current_price > recent_ema:
            signal_strength += 30
            signal_reasons.append(f"가격이 EMA12({recent_ema:.2f}) 위에 위치")
        
        # RSI 신호
        if recent_rsi and 30 <= recent_rsi <= 70:
            signal_strength += 20
            signal_reasons.append(f"RSI14({recent_rsi:.1f})가 적정 범위")
        
        # 거래량 신호
        if volume_surge.get("volume_surge_events", 0) > 0:
            signal_strength += 40
            signal_reasons.append("최근 거래량 급증 감지")
        
        # 신호 등급 결정
        if signal_strength >= 70:
            signal_grade = "STRONG_BUY"
        elif signal_strength >= 50:
            signal_grade = "BUY"
        elif signal_strength >= 30:
            signal_grade = "WEAK_BUY"
        else:
            signal_grade = "HOLD"
        
        return {
            "market": market,
            "signal_grade": signal_grade,
            "signal_strength": signal_strength,
            "current_price": current_price,
            "ema12": recent_ema,
            "rsi14": recent_rsi,
            "reasons": signal_reasons,
            "timestamp": current_time,
            "timeframe": timeframe
        }
        
    except Exception as e:
        return {
            "market": market,
            "signal_grade": "ERROR",
            "signal_strength": 0,
            "error": str(e),
            "timestamp": current_time
        }


# ===================
# 데이터 품질 검증
# ===================

async def validate_data_quality(market: str, timeframe_hours: int = 24) -> Dict:
    """데이터 품질 검증"""
    
    end_time = int(time.time())
    start_time = end_time - (timeframe_hours * 60 * 60)
    
    # 데이터 완성도 확인
    sql = """
    SELECT 
        COUNT(*) as total_candles,
        COUNT(CASE WHEN volume > 0 THEN 1 END) as valid_volume_candles,
        MIN(ts) as earliest_data,
        MAX(ts) as latest_data,
        AVG(volume) as avg_volume
    FROM candles 
    WHERE market = ? AND unit = 1 
      AND ts BETWEEN ? AND ?
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, start_time, end_time))
        row = result.fetchone()
    
    if not row:
        return {"error": "No data found"}
    
    expected_candles = timeframe_hours * 60  # 1분봉 기준
    data_completeness = (row[0] / expected_candles) * 100 if expected_candles > 0 else 0
    volume_completeness = (row[1] / max(row[0], 1)) * 100
    
    # 데이터 갭 확인
    sql = """
    SELECT 
        ts,
        LAG(ts) OVER (ORDER BY ts) as prev_ts,
        (ts - LAG(ts) OVER (ORDER BY ts)) as gap_seconds
    FROM candles 
    WHERE market = ? AND unit = 1 
      AND ts BETWEEN ? AND ?
    ORDER BY ts
    """
    
    async with database.async_engine.begin() as conn:
        result = await conn.exec_driver_sql(sql, (market, start_time, end_time))
        gap_data = result.fetchall()
    
    large_gaps = len([gap for gap in gap_data if gap[2] and gap[2] > 120])  # 2분 이상 갭
    
    quality_score = min(100, (data_completeness + volume_completeness) / 2 - (large_gaps * 5))
    
    return {
        "market": market,
        "timeframe_hours": timeframe_hours,
        "data_completeness": round(data_completeness, 2),
        "volume_completeness": round(volume_completeness, 2),
        "quality_score": round(max(0, quality_score), 2),
        "total_candles": row[0],
        "expected_candles": expected_candles,
        "valid_volume_candles": row[1],
        "large_gaps": large_gaps,
        "avg_volume": round(row[4], 2) if row[4] else 0,
        "data_period": f"{datetime.fromtimestamp(row[2])} ~ {datetime.fromtimestamp(row[3])}"
    }