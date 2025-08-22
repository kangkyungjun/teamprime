"""거래 관련 데이터 모델"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class Position:
    """거래 포지션 클래스 - 고급 손익실현 기능 강화"""
    coin: str
    buy_price: float
    amount: float
    timestamp: datetime
    profit_target: float
    stop_loss: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    
    # 거래 검증용
    order_id: Optional[str] = None
    
    # 고급 손익실현 필드
    trailing_stop_enabled: bool = False
    trailing_stop_percent: float = 0.0
    highest_price_seen: float = 0.0
    partial_profit_taken: bool = False
    profit_stages: Dict[str, bool] = field(default_factory=lambda: {"stage1": False, "stage2": False, "stage3": False})
    price_alerts: Dict[str, float] = field(default_factory=dict)
    last_price_update: Optional[datetime] = None
    price_volatility: float = 0.0
    trend_direction: str = "neutral"  # "up", "down", "neutral"
    consecutive_up_ticks: int = 0
    consecutive_down_ticks: int = 0
    
    def __post_init__(self):
        """초기화 후 처리"""
        self.highest_price_seen = self.buy_price
        self.last_price_update = self.timestamp
        
        # 기본 가격 알림 설정
        self.price_alerts = {
            "quick_profit": self.buy_price * 1.003,  # 0.3% 빠른 수익
            "target_profit": self.profit_target,     # 목표 수익 (0.5%)
            "warning_loss": self.buy_price * 0.998,  # -0.2% 경고
            "stop_loss": self.stop_loss              # -0.3% 손절
        }
    
    def update_current_price(self, price: float):
        """현재 가격 업데이트 및 고급 분석"""
        previous_price = self.current_price if self.current_price > 0 else self.buy_price
        self.current_price = price
        self.unrealized_pnl = (price - self.buy_price) * self.amount
        
        # 최고가 업데이트 (트레일링 스탑용)
        if price > self.highest_price_seen:
            self.highest_price_seen = price
            
        # 가격 변화 방향 추적
        if price > previous_price:
            self.consecutive_up_ticks += 1
            self.consecutive_down_ticks = 0
            if self.consecutive_up_ticks >= 3:
                self.trend_direction = "up"
        elif price < previous_price:
            self.consecutive_down_ticks += 1
            self.consecutive_up_ticks = 0
            if self.consecutive_down_ticks >= 3:
                self.trend_direction = "down"
        else:
            # 가격 변화 없음 - 추세 유지
            pass
            
        # 변동성 계산 (단순 버전)
        if previous_price > 0:
            price_change_percent = abs((price - previous_price) / previous_price) * 100
            self.price_volatility = price_change_percent
            
        self.last_price_update = datetime.now()
    
    def should_take_partial_profit(self) -> bool:
        """부분 익절 조건 확인"""
        profit_percent = ((self.current_price - self.buy_price) / self.buy_price) * 100
        
        # 0.3% 수익에서 50% 부분 익절 (한번만)
        if not self.partial_profit_taken and profit_percent >= 0.3:
            return True
            
        return False
    
    def get_trailing_stop_price(self) -> Optional[float]:
        """트레일링 스탑 가격 계산"""
        if not self.trailing_stop_enabled:
            return None
            
        if self.highest_price_seen > self.buy_price * 1.002:  # 0.2% 이상 수익일 때만 활성화
            return self.highest_price_seen * (1 - self.trailing_stop_percent / 100)
        
        return None
    
    def should_execute_trailing_stop(self) -> bool:
        """트레일링 스탑 실행 조건"""
        trailing_price = self.get_trailing_stop_price()
        if trailing_price and self.current_price <= trailing_price:
            return True
        return False
    
    def get_profit_stage_action(self) -> Optional[str]:
        """수익 단계별 액션 결정"""
        profit_percent = ((self.current_price - self.buy_price) / self.buy_price) * 100
        
        # 0.2% 수익 - 트레일링 스탑 활성화
        if profit_percent >= 0.2 and not self.profit_stages["stage1"]:
            self.profit_stages["stage1"] = True
            self.trailing_stop_enabled = True
            self.trailing_stop_percent = 0.1  # 0.1% 트레일링
            return "enable_trailing_stop"
        
        # 0.4% 수익 - 부분 익절 제안
        elif profit_percent >= 0.4 and not self.profit_stages["stage2"]:
            self.profit_stages["stage2"] = True
            return "suggest_partial_profit"
        
        # 0.6% 수익 - 전체 익절 강력 제안
        elif profit_percent >= 0.6 and not self.profit_stages["stage3"]:
            self.profit_stages["stage3"] = True
            return "suggest_full_profit"
        
        return None
    
    def get_risk_assessment(self) -> str:
        """리스크 평가"""
        profit_percent = ((self.current_price - self.buy_price) / self.buy_price) * 100
        holding_time = (datetime.now() - self.timestamp).total_seconds()
        
        if profit_percent <= -0.25:
            return "high_risk"
        elif profit_percent <= -0.1:
            return "medium_risk"  
        elif holding_time > 240:  # 4분 이상 보유
            return "time_risk"
        elif profit_percent >= 0.3:
            return "profit_secure"
        else:
            return "normal"
    
    def get_recommended_action(self) -> str:
        """추천 액션"""
        risk = self.get_risk_assessment()
        profit_percent = ((self.current_price - self.buy_price) / self.buy_price) * 100
        
        if risk == "high_risk":
            return "immediate_sell"
        elif risk == "time_risk" and profit_percent > 0:
            return "take_profit_now"
        elif self.should_execute_trailing_stop():
            return "trailing_stop_sell"
        elif profit_percent >= 0.5:
            return "target_reached"
        elif self.should_take_partial_profit():
            return "partial_profit"
        else:
            return "hold"

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

@dataclass
class TradeVerification:
    """거래 검증 클래스"""
    order_id: str
    market: str
    side: str  # "bid" or "ask"
    order_type: str  # "market" or "limit"
    requested_amount: float
    requested_price: Optional[float]
    order_timestamp: datetime
    
    # 체결 정보
    filled_amount: float = 0.0
    filled_price: float = 0.0
    average_price: float = 0.0
    total_fee: float = 0.0
    status: str = "pending"  # pending, partial, completed, cancelled, failed
    
    # 검증 상태
    verification_status: str = "pending"  # pending, verified, failed, timeout
    verification_attempts: int = 0
    last_verification: Optional[datetime] = None
    verification_errors: list = field(default_factory=list)
    
    # 성과 분석
    expected_outcome: Optional[float] = None
    actual_outcome: Optional[float] = None
    slippage: float = 0.0
    execution_time: Optional[float] = None
    
    def calculate_slippage(self):
        """슬리피지 계산"""
        if self.requested_price and self.average_price:
            if self.side == "bid":  # 매수
                self.slippage = ((self.average_price - self.requested_price) / self.requested_price) * 100
            else:  # 매도
                self.slippage = ((self.requested_price - self.average_price) / self.requested_price) * 100
    
    def calculate_execution_time(self, completion_time: datetime):
        """체결 시간 계산"""
        self.execution_time = (completion_time - self.order_timestamp).total_seconds()
    
    def is_acceptable_slippage(self, max_slippage: float = 0.1) -> bool:
        """허용 가능한 슬리피지인지 확인"""
        return abs(self.slippage) <= max_slippage
    
    def get_fill_rate(self) -> float:
        """체결률 계산"""
        if self.requested_amount == 0:
            return 0.0
        return (self.filled_amount / self.requested_amount) * 100

@dataclass
class TradingMetrics:
    """거래 성과 지표"""
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    cancelled_orders: int = 0
    partial_orders: int = 0
    
    total_volume: float = 0.0
    total_fees: float = 0.0
    average_slippage: float = 0.0
    average_execution_time: float = 0.0
    
    success_rate: float = 0.0
    fill_rate: float = 0.0
    
    # 시간대별 성과
    last_updated: datetime = field(default_factory=datetime.now)
    daily_metrics: Dict[str, int] = field(default_factory=dict)
    
    def update_metrics(self, verification: TradeVerification):
        """거래 검증 결과로 지표 업데이트"""
        self.total_orders += 1
        
        if verification.status == "completed":
            self.successful_orders += 1
        elif verification.status == "failed":
            self.failed_orders += 1
        elif verification.status == "cancelled":
            self.cancelled_orders += 1
        elif verification.status == "partial":
            self.partial_orders += 1
        
        self.total_volume += verification.filled_amount * verification.average_price
        self.total_fees += verification.total_fee
        
        # 평균 슬리피지 업데이트
        if verification.slippage != 0:
            self.average_slippage = ((self.average_slippage * (self.total_orders - 1)) + verification.slippage) / self.total_orders
        
        # 평균 체결 시간 업데이트
        if verification.execution_time:
            self.average_execution_time = ((self.average_execution_time * (self.total_orders - 1)) + verification.execution_time) / self.total_orders
        
        # 성공률 계산
        self.success_rate = (self.successful_orders / self.total_orders) * 100 if self.total_orders > 0 else 0
        
        # 체결률 계산 (부분 체결 포함)
        filled_orders = self.successful_orders + self.partial_orders
        self.fill_rate = (filled_orders / self.total_orders) * 100 if self.total_orders > 0 else 0
        
        self.last_updated = datetime.now()