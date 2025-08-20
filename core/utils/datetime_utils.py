"""날짜/시간 관련 유틸리티 함수"""

import re
from datetime import datetime, timezone
from typing import Dict

UTC = timezone.utc

def utc_now() -> datetime:
    """현재 UTC 시간 반환"""
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
    # 다양한 포맷 방어
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