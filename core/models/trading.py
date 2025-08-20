"""거래 관련 데이터 모델"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class Position:
    """거래 포지션 클래스"""
    coin: str
    buy_price: float
    amount: float
    timestamp: datetime
    profit_target: float
    stop_loss: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    def update_current_price(self, price: float):
        """현재 가격 업데이트 및 손익 계산"""
        self.current_price = price
        price_change = (price - self.buy_price) / self.buy_price * 100
        self.unrealized_pnl = (price - self.buy_price) * self.amount

@dataclass 
class TradingState:
    """거래 상태 관리 클래스"""
    positions: Dict[str, Position] = field(default_factory=dict)
    daily_trades: int = 0
    daily_loss: float = 0.0
    available_budget: float = 0.0  # 실제 업비트 계좌 잔고에서 가져옴
    reserved_budget: float = 0.0
    last_trade_time: Dict[str, datetime] = field(default_factory=dict)
    
    def can_trade_coin(self, coin: str, amount: float) -> bool:
        """코인별 거래 가능 여부 확인"""
        # 0. 로그인 상태 확인 (잔고가 0이면 로그인하지 않은 상태)
        if self.available_budget <= 0:
            return False
        
        # 1. 예산 확인
        if self.available_budget < amount:
            return False
        
        # 2. 최대 포지션 수 확인
        if len(self.positions) >= 5:  # trading_config["max_positions"]
            return False
        
        # 3. 해당 코인 포지션 중복 확인
        if coin in self.positions:
            return False
        
        # 4. 일일 손실 한도 확인
        if self.daily_loss >= 50000:  # trading_config["daily_loss_limit"]
            return False
        
        # 5. 코인별 쿨다운 확인 (같은 코인 5분 간격)
        if coin in self.last_trade_time:
            time_diff = datetime.now() - self.last_trade_time[coin]
            if time_diff.total_seconds() < 300:  # 5분
                return False
        
        return True

@dataclass
class ManualPosition:
    """수동 거래 포지션 클래스"""
    market: str
    amount: float  # 보유 수량
    buy_price: float  # 매수 가격 (KRW)
    buy_amount: float  # 매수 금액 (KRW)
    buy_time: datetime
    current_price: float = 0.0
    
    @property
    def current_value(self) -> float:
        """현재 가치 (KRW)"""
        return self.amount * self.current_price
    
    @property
    def profit_loss(self) -> float:
        """손익 (KRW)"""
        return self.current_value - self.buy_amount
    
    @property
    def profit_rate(self) -> float:
        """수익률 (%)"""
        if self.buy_amount == 0:
            return 0.0
        return (self.profit_loss / self.buy_amount) * 100
    
    def update_current_price(self, price: float):
        """현재 가격 업데이트"""
        self.current_price = price

# 수동 거래 포지션 관리 (전역 변수)
manual_positions: Dict[str, ManualPosition] = {}

def add_manual_position(market: str, amount: float, buy_price: float, buy_amount: float) -> bool:
    """수동 거래 포지션 추가"""
    try:
        position = ManualPosition(
            market=market,
            amount=amount,
            buy_price=buy_price, 
            buy_amount=buy_amount,
            buy_time=datetime.now(),
            current_price=buy_price
        )
        manual_positions[market] = position
        return True
    except Exception:
        return False

def remove_manual_position(market: str) -> bool:
    """수동 거래 포지션 제거"""
    try:
        if market in manual_positions:
            del manual_positions[market]
            return True
        return False
    except Exception:
        return False

def get_manual_position(market: str) -> Optional[ManualPosition]:
    """특정 수동 거래 포지션 조회"""
    return manual_positions.get(market)

def get_all_manual_positions() -> Dict[str, ManualPosition]:
    """모든 수동 거래 포지션 조회"""
    return manual_positions.copy()