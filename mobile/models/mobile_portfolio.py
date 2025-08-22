"""
💼 모바일 포트폴리오 데이터 모델

⚠️ 기존 거래 시스템의 포트폴리오 데이터를 모바일에 최적화된 형태로 변환합니다.
차트 표시와 통계 분석에 최적화된 구조입니다.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TimeRange(str, Enum):
    """시간 범위"""
    HOUR_1 = "1h"
    HOUR_24 = "24h"
    DAY_7 = "7d"
    DAY_30 = "30d"
    DAY_90 = "90d"

class PerformancePeriod(str, Enum):
    """성과 기간"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"

class MobileHolding(BaseModel):
    """모바일 보유 자산 모델"""
    
    # 자산 기본 정보
    symbol: str = Field(..., description="자산 심볼 (예: KRW-BTC)")
    display_name: str = Field(..., description="표시용 자산명")
    
    # 수량 정보
    total_amount: float = Field(..., description="총 보유 수량")
    available_amount: float = Field(..., description="거래 가능 수량")
    locked_amount: float = Field(0.0, description="거래 중인 수량")
    
    # 가격 정보
    average_buy_price: float = Field(..., description="평균 매수가")
    current_price: float = Field(..., description="현재 가격")
    
    # 가치 정보
    total_value: float = Field(..., description="총 가치 (KRW)")
    invested_amount: float = Field(..., description="투자 금액 (KRW)")
    
    # 수익률 정보
    profit_loss: float = Field(..., description="손익 (KRW)")
    profit_loss_percent: float = Field(..., description="수익률 (%)")
    
    # 24시간 변화
    price_change_24h: float = Field(..., description="24시간 가격 변화 (%)")
    value_change_24h: float = Field(..., description="24시간 가치 변화 (KRW)")
    
    # 모바일 표시용
    weight_percent: float = Field(..., description="포트폴리오 내 비중 (%)")
    color_indicator: str = Field(..., description="수익률 색상")
    chart_data: List[Dict[str, float]] = Field(default_factory=list, description="간단한 차트 데이터")
    
    @validator('color_indicator', always=True)
    def set_color_indicator(cls, v, values):
        """수익률에 따른 색상 설정"""
        profit_loss_percent = values.get('profit_loss_percent', 0)
        if profit_loss_percent > 0:
            return 'green'
        elif profit_loss_percent < 0:
            return 'red'
        else:
            return 'gray'
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "KRW-BTC",
                "display_name": "비트코인",
                "total_amount": 0.05,
                "available_amount": 0.047,
                "locked_amount": 0.003,
                "average_buy_price": 50000000.0,
                "current_price": 52000000.0,
                "total_value": 2600000.0,
                "invested_amount": 2500000.0,
                "profit_loss": 100000.0,
                "profit_loss_percent": 4.0,
                "price_change_24h": 2.3,
                "value_change_24h": 59800.0,
                "weight_percent": 74.3,
                "color_indicator": "green",
                "chart_data": [
                    {"time": 1642680000, "price": 51500000.0},
                    {"time": 1642683600, "price": 52000000.0}
                ]
            }
        }

class MobilePortfolioSummary(BaseModel):
    """모바일 포트폴리오 요약 모델"""
    
    # 총 자산 정보
    total_value: float = Field(..., description="총 자산 가치 (KRW)")
    available_balance: float = Field(..., description="사용 가능한 잔고 (KRW)")
    invested_amount: float = Field(..., description="투자 중인 금액 (KRW)")
    
    # 수익률 정보
    total_profit_loss: float = Field(..., description="총 손익 (KRW)")
    total_profit_loss_percent: float = Field(..., description="총 수익률 (%)")
    
    # 24시간 변화
    value_change_24h: float = Field(..., description="24시간 가치 변화 (KRW)")
    value_change_24h_percent: float = Field(..., description="24시간 변화율 (%)")
    
    # 포트폴리오 구성
    holdings_count: int = Field(..., description="보유 자산 개수")
    active_positions: int = Field(..., description="활성 포지션 수")
    
    # 보유 자산 목록
    holdings: List[MobileHolding] = Field(default_factory=list, description="보유 자산 상세")
    
    # 포트폴리오 통계
    portfolio_stats: Dict[str, float] = Field(default_factory=dict, description="포트폴리오 통계")
    
    # 업데이트 시간
    last_updated: str = Field(..., description="마지막 업데이트 시간 (ISO format)")
    
    # 모바일 표시용
    summary_cards: List[Dict[str, Any]] = Field(default_factory=list, description="요약 카드 데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "total_value": 3500000.0,
                "available_balance": 1000000.0,
                "invested_amount": 2500000.0,
                "total_profit_loss": 125000.0,
                "total_profit_loss_percent": 5.0,
                "value_change_24h": 75000.0,
                "value_change_24h_percent": 2.2,
                "holdings_count": 3,
                "active_positions": 2,
                "holdings": [],
                "portfolio_stats": {
                    "sharpe_ratio": 1.2,
                    "max_drawdown": -8.5,
                    "win_rate": 72.5
                },
                "last_updated": "2024-01-20T15:10:45Z",
                "summary_cards": [
                    {
                        "title": "총 자산",
                        "value": "3,500,000원",
                        "change": "+2.2%",
                        "color": "green"
                    }
                ]
            }
        }

class MobilePerformance(BaseModel):
    """모바일 성과 분석 모델"""
    
    # 기간 정보
    period: PerformancePeriod = Field(..., description="분석 기간")
    start_date: str = Field(..., description="시작일 (ISO format)")
    end_date: str = Field(..., description="종료일 (ISO format)")
    
    # 수익률 정보
    total_return: float = Field(..., description="총 수익률 (%)")
    annual_return: float = Field(..., description="연환산 수익률 (%)")
    daily_return_avg: float = Field(..., description="일평균 수익률 (%)")
    
    # 리스크 지표
    volatility: float = Field(..., description="변동성 (%)")
    sharpe_ratio: float = Field(..., description="샤프 비율")
    max_drawdown: float = Field(..., description="최대 낙폭 (%)")
    
    # 거래 통계
    total_trades: int = Field(..., description="총 거래 수")
    win_trades: int = Field(..., description="수익 거래 수")
    loss_trades: int = Field(..., description="손실 거래 수")
    win_rate: float = Field(..., description="승률 (%)")
    
    # 평균 거래 성과
    avg_win: float = Field(..., description="평균 수익 (KRW)")
    avg_loss: float = Field(..., description="평균 손실 (KRW)")
    profit_factor: float = Field(..., description="프로핏 팩터")
    
    # 성과 차트 데이터
    performance_chart: List[Dict[str, Any]] = Field(default_factory=list, description="성과 차트 데이터")
    drawdown_chart: List[Dict[str, Any]] = Field(default_factory=list, description="낙폭 차트 데이터")
    
    # 모바일 요약
    performance_grade: str = Field(..., description="성과 등급 (A+, A, B+, B, C+, C, D)")
    summary_text: str = Field(..., description="성과 요약 텍스트")
    
    @validator('performance_grade', always=True)
    def calculate_performance_grade(cls, v, values):
        """수익률과 샤프 비율에 따른 성과 등급 계산"""
        total_return = values.get('total_return', 0)
        sharpe_ratio = values.get('sharpe_ratio', 0)
        
        if total_return > 20 and sharpe_ratio > 2.0:
            return 'A+'
        elif total_return > 15 and sharpe_ratio > 1.5:
            return 'A'
        elif total_return > 10 and sharpe_ratio > 1.0:
            return 'B+'
        elif total_return > 5 and sharpe_ratio > 0.5:
            return 'B'
        elif total_return > 0:
            return 'C+'
        elif total_return > -5:
            return 'C'
        else:
            return 'D'
    
    class Config:
        schema_extra = {
            "example": {
                "period": "month",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "total_return": 12.5,
                "annual_return": 150.0,
                "daily_return_avg": 0.41,
                "volatility": 18.3,
                "sharpe_ratio": 1.35,
                "max_drawdown": -8.2,
                "total_trades": 156,
                "win_trades": 113,
                "loss_trades": 43,
                "win_rate": 72.4,
                "avg_win": 15250.0,
                "avg_loss": -8340.0,
                "profit_factor": 1.83,
                "performance_chart": [],
                "drawdown_chart": [],
                "performance_grade": "B+",
                "summary_text": "이번 달 우수한 성과를 보였습니다"
            }
        }

class MobilePortfolioAllocation(BaseModel):
    """모바일 자산 배분 모델"""
    
    # 자산별 배분
    allocations: List[Dict[str, Any]] = Field(..., description="자산별 배분 정보")
    
    # 배분 통계
    diversification_score: float = Field(..., description="분산화 점수 (0-100)")
    concentration_risk: float = Field(..., description="집중도 위험 (0-100)")
    
    # 권장 사항
    recommendations: List[str] = Field(default_factory=list, description="포트폴리오 개선 권장사항")
    
    # 시각화 데이터
    pie_chart_data: List[Dict[str, Any]] = Field(default_factory=list, description="파이 차트 데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "allocations": [
                    {
                        "symbol": "KRW-BTC",
                        "name": "비트코인",
                        "weight": 60.5,
                        "value": 2117500.0,
                        "color": "#F7931A"
                    },
                    {
                        "symbol": "KRW-ETH",
                        "name": "이더리움", 
                        "weight": 25.2,
                        "value": 882000.0,
                        "color": "#627EEA"
                    }
                ],
                "diversification_score": 75.8,
                "concentration_risk": 35.2,
                "recommendations": [
                    "비트코인 비중이 높습니다. 다른 자산으로 분산 투자를 고려해보세요.",
                    "알트코인 비중을 늘려 포트폴리오를 더욱 다양화해보세요."
                ],
                "pie_chart_data": []
            }
        }