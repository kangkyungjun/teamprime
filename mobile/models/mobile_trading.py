"""
📈 모바일 거래 데이터 모델

⚠️ 기존 거래 시스템의 데이터를 모바일에 최적화된 형태로 변환하는 모델입니다.
기존 core/models/trading.py의 데이터를 읽어서 모바일용으로 포맷팅합니다.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TradingSide(str, Enum):
    """거래 방향"""
    BUY = "buy"
    SELL = "sell"

class PositionStatus(str, Enum):
    """포지션 상태"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"

class MobilePosition(BaseModel):
    """모바일 포지션 정보 모델"""
    
    # 기본 정보
    symbol: str = Field(..., description="거래 심볼 (예: KRW-BTC)")
    side: TradingSide = Field(..., description="거래 방향")
    amount: float = Field(..., description="거래 수량")
    
    # 가격 정보
    entry_price: float = Field(..., description="진입 가격")
    current_price: float = Field(..., description="현재 가격") 
    target_price: Optional[float] = Field(None, description="목표 가격")
    stop_loss_price: Optional[float] = Field(None, description="손절 가격")
    
    # 수익률 정보
    profit_loss: float = Field(..., description="손익 (KRW)")
    profit_loss_percent: float = Field(..., description="수익률 (%)")
    
    # 시간 정보
    created_at: str = Field(..., description="포지션 생성 시간 (ISO format)")
    duration: str = Field(..., description="보유 시간 (예: 2분 30초)")
    
    # 상태
    status: PositionStatus = Field(PositionStatus.OPEN, description="포지션 상태")
    
    # 모바일 표시용 추가 정보
    display_name: str = Field(..., description="표시용 심볼명 (예: 비트코인)")
    color_indicator: str = Field(..., description="수익률 색상 (green/red/gray)")
    
    @validator('color_indicator', always=True)
    def set_color_indicator(cls, v, values):
        """수익률에 따른 색상 지시자 설정"""
        profit_loss_percent = values.get('profit_loss_percent', 0)
        if profit_loss_percent > 0:
            return 'green'
        elif profit_loss_percent < 0:
            return 'red'
        else:
            return 'gray'
    
    @validator('display_name', always=True)
    def set_display_name(cls, v, values):
        """심볼에 따른 표시명 설정"""
        symbol = values.get('symbol', '')
        symbol_names = {
            'KRW-BTC': '비트코인',
            'KRW-ETH': '이더리움',
            'KRW-XRP': '리플',
            'KRW-DOGE': '도지코인',
            'KRW-ADA': '에이다',
            'KRW-SOL': '솔라나',
            'KRW-AVAX': '아발란체',
            'KRW-DOT': '폴카닷'
        }
        return symbol_names.get(symbol, symbol.replace('KRW-', ''))
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "KRW-BTC",
                "side": "buy",
                "amount": 0.001,
                "entry_price": 52000000.0,
                "current_price": 52500000.0,
                "target_price": 52260000.0,
                "stop_loss_price": 51844000.0,
                "profit_loss": 500.0,
                "profit_loss_percent": 0.96,
                "created_at": "2024-01-20T14:25:30Z",
                "duration": "2분 30초",
                "status": "open",
                "display_name": "비트코인",
                "color_indicator": "green"
            }
        }

class MobileTradingStatus(BaseModel):
    """모바일 거래 시스템 상태 모델"""
    
    # 시스템 상태
    is_running: bool = Field(..., description="거래 시스템 실행 상태")
    is_trading_active: bool = Field(..., description="실제 거래 활성화 상태")
    
    # 자금 정보
    available_budget: float = Field(..., description="사용 가능한 자금 (KRW)")
    invested_amount: float = Field(..., description="투자 중인 금액 (KRW)")
    total_value: float = Field(..., description="총 자산 가치 (KRW)")
    
    # 포지션 정보
    position_count: int = Field(..., description="현재 포지션 수")
    max_positions: int = Field(5, description="최대 동시 포지션 수")
    
    # 수익률 정보
    total_profit_loss: float = Field(..., description="총 손익 (KRW)")
    total_profit_loss_percent: float = Field(..., description="총 수익률 (%)")
    daily_profit_loss: float = Field(..., description="일일 손익 (KRW)")
    
    # 거래 통계
    daily_trades: int = Field(..., description="일일 거래 수")
    win_rate: float = Field(..., description="승률 (%)")
    
    # 시간 정보
    last_signal_time: Optional[str] = Field(None, description="마지막 신호 시간 (ISO format)")
    last_trade_time: Optional[str] = Field(None, description="마지막 거래 시간 (ISO format)")
    uptime: str = Field(..., description="시스템 가동 시간")
    
    # 모바일 표시용
    status_text: str = Field(..., description="상태 텍스트")
    status_color: str = Field(..., description="상태 색상 (green/yellow/red)")
    
    @validator('status_text', always=True)
    def set_status_text(cls, v, values):
        """상태에 따른 텍스트 설정"""
        is_running = values.get('is_running', False)
        is_trading_active = values.get('is_trading_active', False)
        
        if is_running and is_trading_active:
            return "거래 중"
        elif is_running:
            return "대기 중"
        else:
            return "정지"
    
    @validator('status_color', always=True)
    def set_status_color(cls, v, values):
        """상태에 따른 색상 설정"""
        is_running = values.get('is_running', False)
        is_trading_active = values.get('is_trading_active', False)
        
        if is_running and is_trading_active:
            return "green"
        elif is_running:
            return "yellow"
        else:
            return "red"
    
    class Config:
        schema_extra = {
            "example": {
                "is_running": True,
                "is_trading_active": True,
                "available_budget": 1000000.0,
                "invested_amount": 2500000.0,
                "total_value": 3500000.0,
                "position_count": 3,
                "max_positions": 5,
                "total_profit_loss": 125000.0,
                "total_profit_loss_percent": 3.7,
                "daily_profit_loss": 15000.0,
                "daily_trades": 8,
                "win_rate": 72.5,
                "last_signal_time": "2024-01-20T15:10:45Z",
                "last_trade_time": "2024-01-20T15:05:20Z",
                "uptime": "2시간 30분",
                "status_text": "거래 중",
                "status_color": "green"
            }
        }

class MobileTradingControl(BaseModel):
    """모바일 거래 제어 요청 모델"""
    
    action: str = Field(..., description="제어 액션 (start/stop/emergency_stop/pause)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="추가 파라미터")
    
    # 보안 관련
    confirmation: bool = Field(False, description="사용자 확인 여부")
    user_id: str = Field(..., description="요청한 사용자 ID")
    device_id: str = Field(..., description="요청한 기기 ID")
    
    class Config:
        schema_extra = {
            "example": {
                "action": "start",
                "parameters": {
                    "budget_limit": 1000000,
                    "max_positions": 3
                },
                "confirmation": True,
                "user_id": "user_12345",
                "device_id": "iPhone_12_ABC123"
            }
        }

class MobileTradingControlResponse(BaseModel):
    """모바일 거래 제어 응답 모델"""
    
    success: bool = Field(..., description="제어 성공 여부")
    message: str = Field(..., description="결과 메시지")
    action: str = Field(..., description="실행된 액션")
    
    # 결과 데이터
    result_data: Optional[Dict[str, Any]] = Field(None, description="결과 데이터")
    
    # 에러 정보
    error_code: Optional[str] = Field(None, description="에러 코드")
    error_details: Optional[str] = Field(None, description="에러 상세 정보")
    
    # 시간 정보
    executed_at: str = Field(..., description="실행 시간 (ISO format)")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "거래 시스템이 성공적으로 시작되었습니다",
                "action": "start",
                "result_data": {
                    "is_running": True,
                    "position_count": 0,
                    "available_budget": 1000000.0
                },
                "error_code": None,
                "error_details": None,
                "executed_at": "2024-01-20T15:10:45Z"
            }
        }

class MobileTradeHistory(BaseModel):
    """모바일 거래 내역 모델"""
    
    # 거래 기본 정보
    trade_id: str = Field(..., description="거래 ID")
    symbol: str = Field(..., description="거래 심볼")
    side: TradingSide = Field(..., description="거래 방향")
    amount: float = Field(..., description="거래 수량")
    price: float = Field(..., description="체결 가격")
    
    # 수익률 정보
    profit_loss: float = Field(..., description="손익 (KRW)")
    profit_loss_percent: float = Field(..., description="수익률 (%)")
    
    # 시간 정보
    executed_at: str = Field(..., description="체결 시간 (ISO format)")
    duration: Optional[str] = Field(None, description="보유 기간")
    
    # 거래 상세
    entry_price: Optional[float] = Field(None, description="진입 가격")
    exit_price: Optional[float] = Field(None, description="청산 가격")
    fees: float = Field(0.0, description="수수료")
    
    # 거래 결과
    status: str = Field(..., description="거래 상태 (completed/failed)")
    result: str = Field(..., description="거래 결과 (profit/loss/break_even)")
    
    # 모바일 표시용
    display_name: str = Field(..., description="표시용 심볼명")
    color_indicator: str = Field(..., description="수익률 색상")
    
    class Config:
        schema_extra = {
            "example": {
                "trade_id": "trade_12345",
                "symbol": "KRW-BTC",
                "side": "buy",
                "amount": 0.001,
                "price": 52000000.0,
                "profit_loss": 2600.0,
                "profit_loss_percent": 0.5,
                "executed_at": "2024-01-20T14:25:30Z",
                "duration": "3분 15초",
                "entry_price": 52000000.0,
                "exit_price": 52260000.0,
                "fees": 520.0,
                "status": "completed",
                "result": "profit",
                "display_name": "비트코인",
                "color_indicator": "green"
            }
        }