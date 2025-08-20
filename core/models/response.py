"""API 응답 모델"""

from pydantic import BaseModel

class CandleOut(BaseModel):
    """캔들 데이터 출력 모델"""
    market: str
    unit: int
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float