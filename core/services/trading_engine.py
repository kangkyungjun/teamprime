"""멀티 코인 거래 엔진"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List

from ..models.trading import Position, TradingState
from .signal_analyzer import signal_analyzer
from ..utils.api_manager import api_manager, APIPriority
from config import DEFAULT_MARKETS

logger = logging.getLogger(__name__)

# 업비트 API 클라이언트 참조 (레거시 호환성)
def get_upbit_client():
    """업비트 클라이언트 참조 가져오기 - 레거시 호환성"""
    try:
        from ..api.system import upbit_client
        return upbit_client
    except ImportError:
        return None

# 사용자별 업비트 클라이언트 참조
def get_user_upbit_client(user_session):
    """사용자별 업비트 클라이언트 참조 가져오기"""
    if user_session and hasattr(user_session, 'upbit_client'):
        return user_session.upbit_client
    return None

# 거래 상태 인스턴스 (싱글톤)
trading_state = TradingState()

class MultiCoinTradingEngine:
    """멀티 코인 동시 거래 엔진 - 초고속 단타 최적화"""
    
    def __init__(self):
        self.is_running = False
        self.signal_check_interval = 60   # 🕐 1분마다 신호 확인 (REST API 기반)
        self.monitoring_task = None
        self.signal_task = None
        self.trading_start_time = None  # 거래 시작 시간 추적 (자동 중단시 초기화될 수 있음)
        self.session_start_time = None  # 세션 시작 시간 추적 (수동 중단시에만 초기화)
        
        # REST API 기반 데이터 관리
        self.rest_api_mode = True  # REST API 안정성 모드
        self.last_signal_check = {}   # 코인별 마지막 신호 확인 시간
        
        # 사이클 상태 추적
        self.cycle_info = {
            "cycle_number": 0,
            "cycle_start_time": 0,
            "current_phase": "idle",  # idle, processing, completed
            "total_progress": 0.0,
            "estimated_completion": 0,
            "phase_details": {
                "current_coin": None,
                "coin_progress": 0.0,
                "coins_completed": [],
                "coins_remaining": [],
                "processing_start_time": 0
            }
        }
        
        # 활성 코인 상태 (처리중/완료만 추적)
        self.active_coins = {}
        self.recent_completed = {}
        
        # 단타 전용 설정
        self.scalping_mode = True  # 단타 모드 활성화
        self.scalping_params = {
            "min_signal_strength": 60,    # 최소 신호 강도
            "min_confidence": 50,         # 최소 신뢰도
            "max_hold_time": 300,         # 최대 보유 시간 (5분)
            "quick_profit_target": 0.5,   # 빠른 익절 목표 (0.5%)
            "tight_stop_loss": -0.3,     # 타이트한 손절가 (-0.3%)
            "volume_spike_threshold": 2.0 # 거래량 급증 기준
        }
        
        # API 호출 관리 (업비트 규정 준수 - 429 에러 방지 강화)
        self.api_call_scheduler = {
            "last_call_times": {},  # 코인별 마지막 호출 시간
            "call_intervals": {     # 코인별 호출 간격 (초) - 보수적으로 증가
                "BTC": 15,  # 15초 간격 (기존 10초 → 15초)
                "XRP": 18,  # 18초 간격 (기존 12초 → 18초)
                "ETH": 21,  # 21초 간격 (기존 14초 → 21초)
                "DOGE": 24, # 24초 간격 (기존 16초 → 24초)
                "BTT": 27   # 27초 간격 (기존 18초 → 27초)
            },
            "min_global_interval": 3.0,  # 모든 API 호출간 최소 간격 (3초)
            "last_global_call": 0        # 마지막 전역 API 호출 시간
        }
        
        # 최적화된 매개변수 (검증된 승률 56.7%)
        self.optimized_params = {
            "BTC": {"volume_mult": 1.3, "price_change": 0.15, "candle_pos": 0.6, "profit_target": 0.8, "stop_loss": -0.4},
            "XRP": {"volume_mult": 1.4, "price_change": 0.2, "candle_pos": 0.7, "profit_target": 1.2, "stop_loss": -0.3},
            "ETH": {"volume_mult": 1.3, "price_change": 0.15, "candle_pos": 0.6, "profit_target": 0.9, "stop_loss": -0.4},
            "DOGE": {"volume_mult": 1.8, "price_change": 0.3, "candle_pos": 0.8, "profit_target": 1.5, "stop_loss": -0.3},
            "BTT": {"volume_mult": 2.2, "price_change": 0.4, "candle_pos": 0.8, "profit_target": 2.0, "stop_loss": -0.3}
        }
    
    async def start_trading(self):
        """거래 시작"""
        if self.is_running:
            logger.warning("⚠️ 거래가 이미 실행 중입니다")
            return
        
        self.is_running = True
        self.trading_start_time = time.time()
        if self.session_start_time is None:
            self.session_start_time = time.time()
        
        logger.info("🚀 멀티 코인 거래 엔진 시작")
        
        # API 매니저 워커 시작
        await api_manager.start_worker()
        
        # 신호 감지 태스크 시작
        self.signal_task = asyncio.create_task(self._signal_monitoring_loop())
        
        # 포지션 모니터링 태스크 시작
        self.monitoring_task = asyncio.create_task(self._position_monitoring_loop())
    
    async def stop_trading(self, manual_stop: bool = True):
        """거래 중지"""
        if not self.is_running:
            logger.warning("⚠️ 거래가 실행 중이 아닙니다")
            return
        
        self.is_running = False
        
        if manual_stop:
            # 수동 중지 시에는 session_start_time까지 초기화
            self.session_start_time = None
            self.trading_start_time = None
        else:
            # 자동 중지 시에는 trading_start_time만 초기화하고 session_start_time은 보존
            self.trading_start_time = None
        
        if self.signal_task:
            self.signal_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        # API 매니저 워커 중지
        await api_manager.stop_worker()
        
        logger.info("⏹️ 자동거래 중단")
    
    async def _signal_monitoring_loop(self):
        """신호 모니터링 루프"""
        while self.is_running:
            try:
                await self._detect_signals()
                await asyncio.sleep(self.signal_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"⚠️ 신호 모니터링 오류: {str(e)}")
                await asyncio.sleep(30)  # 오류 시 30초 대기
    
    async def _position_monitoring_loop(self):
        """포지션 모니터링 루프"""
        while self.is_running:
            try:
                await self._monitor_positions()
                await asyncio.sleep(10)  # 10초마다 포지션 체크
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"⚠️ 포지션 모니터링 오류: {str(e)}")
                await asyncio.sleep(30)  # 오류 시 30초 대기
    
    async def _detect_signals(self):
        """REST API 기반 신호 감지"""
        current_time = time.time()
        
        # 사이클 시작 처리
        self._start_new_cycle(current_time)
        
        # 전체 코인 리스트 준비
        all_markets = list(DEFAULT_MARKETS)
        total_coins = len(all_markets)
        
        for i, market in enumerate(all_markets):
            try:
                coin_symbol = market.split('-')[1]
                
                # API 호출 간격 확인 (코인별 + 전역 간격)
                last_call = self.api_call_scheduler["last_call_times"].get(coin_symbol, 0)
                required_interval = self.api_call_scheduler["call_intervals"].get(coin_symbol, 15)
                last_global_call = self.api_call_scheduler["last_global_call"]
                min_global_interval = self.api_call_scheduler["min_global_interval"]
                
                # 코인별 간격 확인
                if current_time - last_call < required_interval:
                    logger.debug(f"🕐 {coin_symbol} API 호출 간격 대기 중 ({current_time - last_call:.1f}초 < {required_interval}초)")
                    continue
                
                # 전역 간격 확인 (모든 API 호출간 최소 간격)
                if current_time - last_global_call < min_global_interval:
                    logger.debug(f"🕐 전역 API 호출 간격 대기 중 ({current_time - last_global_call:.1f}초 < {min_global_interval}초)")
                    await asyncio.sleep(min_global_interval - (current_time - last_global_call))
                    current_time = time.time()  # 시간 업데이트
                
                # 코인 처리 시작 상태 업데이트
                self._start_coin_processing(coin_symbol, i, total_coins)
                
                # 로그인 상태 및 거래 가능 여부 확인
                if trading_state.available_budget <= 0:
                    logger.warning("⚠️ 업비트 로그인이 필요합니다. 거래를 중단합니다.")
                    self._complete_coin_processing(coin_symbol, "error", "로그인 필요")
                    return
                
                investment_amount = min(200000, trading_state.available_budget * 0.2)
                
                if not trading_state.can_trade_coin(coin_symbol, investment_amount):
                    self._complete_coin_processing(coin_symbol, "skipped", "거래 불가")
                    continue
                
                # 신호 분석 실행
                params = self.optimized_params.get(coin_symbol, self.optimized_params["BTC"])
                signal = await signal_analyzer.check_buy_signal(market, params)
                
                # API 호출 시간 기록 (코인별 + 전역)
                self.api_call_scheduler["last_call_times"][coin_symbol] = current_time
                self.api_call_scheduler["last_global_call"] = current_time
                
                if signal and signal["should_buy"]:
                    logger.info(f"📈 {coin_symbol} 매수 신호 감지!")
                    logger.info(f"   신호 강도: {signal['signal_strength']}")
                    logger.info(f"   사유: {signal['reason']}")
                    
                    # 매수 주문 실행
                    await self._execute_buy_order(market, coin_symbol, investment_amount, signal)
                    self.api_call_scheduler["last_global_call"] = time.time()  # 주문 후 시간 갱신
                    self._complete_coin_processing(coin_symbol, "success", "매수 신호 감지")
                else:
                    self._complete_coin_processing(coin_symbol, "success", "신호 없음")
                
                # 코인간 안전 간격 (8초 대기로 증가)
                await asyncio.sleep(8)
                
            except Exception as e:
                logger.error(f"⚠️ {market} 신호 감지 오류: {str(e)}")
                coin_symbol = market.split('-')[1]
                self._complete_coin_processing(coin_symbol, "error", str(e))
                continue
        
        # 사이클 완료 처리
        self._complete_cycle()
    
    async def _monitor_positions(self):
        """보유 포지션 모니터링 및 청산 신호 확인"""
        positions_to_close = []
        
        for coin, position in trading_state.positions.items():
            try:
                market = f"KRW-{coin}"
                
                # 현재 가격 업데이트
                current_price = await self._get_current_price(market)
                if current_price:
                    position.update_current_price(current_price)
                    
                    # 익절 조건 확인
                    if current_price >= position.profit_target:
                        logger.info(f"🎯 {coin} 익절 조건 달성 (목표가: {position.profit_target:,.0f})")
                        positions_to_close.append(coin)
                        continue
                    
                    # 손절 조건 확인
                    if current_price <= position.stop_loss:
                        logger.info(f"🛑 {coin} 손절 조건 달성 (손절가: {position.stop_loss:,.0f})")
                        positions_to_close.append(coin)
                        continue
                    
                    # 최대 보유 시간 확인 (5분)
                    holding_time = (datetime.now() - position.timestamp).total_seconds()
                    if holding_time > self.scalping_params["max_hold_time"]:
                        logger.info(f"⏰ {coin} 최대 보유 시간 초과 ({holding_time:.0f}초)")
                        positions_to_close.append(coin)
                        continue
                    
                    # 로그 출력 (30초마다)
                    if int(holding_time) % 30 == 0:
                        pnl_percent = ((current_price - position.buy_price) / position.buy_price) * 100
                        logger.info(f"📊 {coin} 포지션 상태: {pnl_percent:+.2f}% (보유시간: {holding_time:.0f}초)")
                
            except Exception as e:
                logger.error(f"⚠️ {coin} 포지션 모니터링 오류: {str(e)}")
        
        # 청산할 포지션들 처리
        for coin in positions_to_close:
            try:
                await self._close_position(coin)
            except Exception as e:
                logger.error(f"⚠️ {coin} 포지션 청산 오류: {str(e)}")
    
    async def _execute_buy_order(self, market: str, coin_symbol: str, investment_amount: float, signal: Dict):
        """매수 주문 실행"""
        try:
            upbit_client = get_upbit_client()
            if not upbit_client:
                logger.error("⚠️ 업비트 클라이언트가 연결되지 않았습니다")
                return
            
            # 현재 가격 조회
            current_price = await self._get_current_price(market)
            if not current_price:
                logger.error(f"⚠️ {market} 현재 가격 조회 실패")
                return
            
            # 매수 수량 계산
            buy_amount = investment_amount / current_price
            
            logger.info(f"💰 {coin_symbol} 매수 주문 실행")
            logger.info(f"   투자 금액: {investment_amount:,.0f} KRW")
            logger.info(f"   매수 가격: {current_price:,.0f} KRW")
            logger.info(f"   매수 수량: {buy_amount:.8f}")
            
            # 실제 매수 주문 (시장가)
            order_result = await upbit_client.place_market_buy_order(market, investment_amount)
            
            if order_result.get("success", False):
                # 포지션 생성
                profit_target_price = current_price * (1 + self.scalping_params["quick_profit_target"] / 100)
                stop_loss_price = current_price * (1 + self.scalping_params["tight_stop_loss"] / 100)
                
                position = Position(
                    coin=coin_symbol,
                    buy_price=current_price,
                    amount=buy_amount,
                    timestamp=datetime.now(),
                    profit_target=profit_target_price,
                    stop_loss=stop_loss_price
                )
                
                # 거래 상태 업데이트
                trading_state.positions[coin_symbol] = position
                trading_state.available_budget -= investment_amount
                trading_state.reserved_budget += investment_amount
                trading_state.daily_trades += 1
                trading_state.last_trade_time[coin_symbol] = datetime.now()
                
                logger.info(f"✅ {coin_symbol} 매수 완료!")
                logger.info(f"   익절가: {profit_target_price:,.0f} KRW")
                logger.info(f"   손절가: {stop_loss_price:,.0f} KRW")
                
            else:
                logger.error(f"❌ {coin_symbol} 매수 주문 실패: {order_result.get('error', '알 수 없는 오류')}")
                
        except Exception as e:
            logger.error(f"⚠️ {coin_symbol} 매수 주문 오류: {str(e)}")
    
    async def _get_current_price(self, market: str) -> Optional[float]:
        """현재 가격 조회 (API 매니저 사용)"""
        try:
            upbit_client = get_upbit_client()
            if not upbit_client:
                return None
            
            # API 매니저를 통한 안전한 호출 (포지션 모니터링 우선순위)
            ticker_data = await api_manager.safe_api_call(
                upbit_client, 
                'get_single_ticker', 
                market,
                priority=APIPriority.POSITION_MONITORING
            )
            
            if ticker_data and "trade_price" in ticker_data:
                return float(ticker_data["trade_price"])
            
            return None
            
        except Exception as e:
            logger.error(f"⚠️ {market} 가격 조회 오류: {str(e)}")
            return None
    
    async def _close_position(self, coin: str):
        """포지션 청산"""
        try:
            if coin not in trading_state.positions:
                logger.warning(f"⚠️ {coin} 포지션이 존재하지 않습니다")
                return
            
            position = trading_state.positions[coin]
            upbit_client = get_upbit_client()
            
            if not upbit_client:
                logger.error("⚠️ 업비트 클라이언트가 연결되지 않았습니다")
                return
            
            market = f"KRW-{coin}"
            
            logger.info(f"💰 {coin} 포지션 청산 시도")
            logger.info(f"   보유 수량: {position.amount:.8f}")
            logger.info(f"   매수 가격: {position.buy_price:,.0f} KRW")
            
            # 실제 매도 주문 (시장가)
            order_result = await upbit_client.place_market_sell_order(market, position.amount)
            
            if order_result.get("success", False):
                # 수익 계산
                current_price = position.current_price or position.buy_price
                realized_pnl = (current_price - position.buy_price) * position.amount
                
                # 거래 상태 업데이트
                trading_state.available_budget += (current_price * position.amount)
                trading_state.reserved_budget -= (position.buy_price * position.amount)
                
                if realized_pnl < 0:
                    trading_state.daily_loss += abs(realized_pnl)
                
                # 포지션 제거
                del trading_state.positions[coin]
                
                logger.info(f"✅ {coin} 매도 완료!")
                logger.info(f"   매도 가격: {current_price:,.0f} KRW")
                logger.info(f"   실현 손익: {realized_pnl:,.0f} KRW")
                
            else:
                logger.error(f"❌ {coin} 매도 주문 실패: {order_result.get('error', '알 수 없는 오류')}")
            
        except Exception as e:
            logger.error(f"⚠️ {coin} 포지션 청산 오류: {str(e)}")
    
    def get_status(self) -> dict:
        """거래 엔진 상태 조회"""
        return {
            "is_running": self.is_running,
            "positions_count": len(trading_state.positions),
            "available_budget": trading_state.available_budget,
            "daily_trades": trading_state.daily_trades,
            "daily_loss": trading_state.daily_loss,
            "uptime_seconds": time.time() - self.session_start_time if self.session_start_time else 0
        }
    
    def get_coin_api_status(self) -> dict:
        """실시간 API 호출 상태 조회"""
        return {
            "cycle_info": self.cycle_info.copy(),
            "active_coins": self.active_coins.copy(),
            "recent_completed": self.recent_completed.copy()
        }
    
    def _start_new_cycle(self, current_time: float):
        """새 사이클 시작"""
        self.cycle_info["cycle_number"] += 1
        self.cycle_info["cycle_start_time"] = current_time
        self.cycle_info["current_phase"] = "processing"
        self.cycle_info["total_progress"] = 0.0
        
        # 예상 완료 시간 계산 (대략 75초 예상)
        estimated_duration = 75  # API 호출 + 대기시간
        self.cycle_info["estimated_completion"] = current_time + estimated_duration
        
        # 초기화
        self.cycle_info["phase_details"] = {
            "current_coin": None,
            "coin_progress": 0.0,
            "coins_completed": [],
            "coins_remaining": [market.split('-')[1] for market in DEFAULT_MARKETS],
            "processing_start_time": current_time
        }
        
        # 이전 활성 코인들을 recent_completed로 이동
        for coin_symbol, coin_data in self.active_coins.items():
            self.recent_completed[coin_symbol] = {
                "completion_time": current_time,
                "duration": current_time - coin_data.get("start_time", current_time),
                "result": coin_data.get("result", "unknown")
            }
        
        self.active_coins.clear()
        
        logger.info(f"🔄 사이클 #{self.cycle_info['cycle_number']} 시작")
    
    def _start_coin_processing(self, coin_symbol: str, coin_index: int, total_coins: int):
        """코인 처리 시작"""
        current_time = time.time()
        
        # 사이클 진행률 업데이트
        self.cycle_info["total_progress"] = coin_index / total_coins
        self.cycle_info["phase_details"]["current_coin"] = coin_symbol
        self.cycle_info["phase_details"]["coin_progress"] = 0.0
        self.cycle_info["phase_details"]["processing_start_time"] = current_time
        
        # 남은 코인 목록에서 제거
        if coin_symbol in self.cycle_info["phase_details"]["coins_remaining"]:
            self.cycle_info["phase_details"]["coins_remaining"].remove(coin_symbol)
        
        # 활성 코인 상태 추가
        self.active_coins[coin_symbol] = {
            "status": "processing",
            "api_type": "signal_analysis",
            "start_time": current_time,
            "progress": 0.0,
            "estimated_completion": current_time + self.api_call_scheduler["call_intervals"].get(coin_symbol, 15)
        }
        
        logger.info(f"🔍 {coin_symbol} 신호 분석 시작 ({coin_index + 1}/{total_coins})")
    
    def _complete_coin_processing(self, coin_symbol: str, result: str, message: str = ""):
        """코인 처리 완료"""
        current_time = time.time()
        
        # 완료된 코인 목록에 추가
        if coin_symbol not in self.cycle_info["phase_details"]["coins_completed"]:
            self.cycle_info["phase_details"]["coins_completed"].append(coin_symbol)
        
        # 활성 코인에서 recent_completed로 이동
        if coin_symbol in self.active_coins:
            coin_data = self.active_coins[coin_symbol]
            duration = current_time - coin_data.get("start_time", current_time)
            
            self.recent_completed[coin_symbol] = {
                "completion_time": current_time,
                "duration": duration,
                "result": result,
                "message": message
            }
            
            del self.active_coins[coin_symbol]
        
        # 사이클 진행률 업데이트
        total_coins = len(DEFAULT_MARKETS)
        completed_count = len(self.cycle_info["phase_details"]["coins_completed"])
        self.cycle_info["total_progress"] = completed_count / total_coins
        
        logger.info(f"✅ {coin_symbol} 처리 완료: {result} - {message}")
    
    def _complete_cycle(self):
        """사이클 완료"""
        current_time = time.time()
        cycle_duration = current_time - self.cycle_info["cycle_start_time"]
        
        self.cycle_info["current_phase"] = "completed"
        self.cycle_info["total_progress"] = 1.0
        self.cycle_info["phase_details"]["current_coin"] = None
        
        # 완료 통계
        completed_count = len(self.cycle_info["phase_details"]["coins_completed"])
        total_count = len(DEFAULT_MARKETS)
        
        logger.info(f"✅ 사이클 #{self.cycle_info['cycle_number']} 완료: {completed_count}/{total_count} 코인 처리 ({cycle_duration:.1f}초)")


# 전역 거래 엔진 인스턴스
trading_engine = MultiCoinTradingEngine()