"""멀티 코인 거래 엔진"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List

from ..models.trading import Position, TradingState
from .signal_analyzer import signal_analyzer
from .trade_verifier import trade_verifier
from .resilience_service import resilience_service
from .monitoring_service import monitoring_service, AlertSeverity, MetricType
from ..utils.api_manager import api_manager, APIPriority
from config import DEFAULT_MARKETS, MTFA_OPTIMIZED_CONFIG, get_risk_reward_from_confidence

logger = logging.getLogger(__name__)

# 업비트 API 클라이언트 참조 (레거시 호환성)
def get_upbit_client():
    """업비트 클라이언트 참조 가져오기 - 레거시 호환성"""
    try:
        from ..api.system import upbit_client
        return upbit_client
    except ImportError:
        return None


# 거래 상태 인스턴스 (싱글톤)
trading_state = TradingState()

class MultiCoinTradingEngine:
    """멀티 코인 동시 거래 엔진 - 초고속 단타 최적화"""
    
    def __init__(self, user_session=None):
        self.is_running = False
        self.signal_check_interval = 60   # 🕐 1분마다 신호 확인 (REST API 기반)
        self.monitoring_task = None
        self.signal_task = None
        self.trading_start_time = None  # 거래 시작 시간 추적 (자동 중단시 초기화될 수 있음)
        self.session_start_time = None  # 세션 시작 시간 추적 (수동 중단시에만 초기화)
        
        # 사용자 세션 참조 (세션별 격리를 위해)
        self.user_session = user_session
        
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
        
        # MTFA 최적화 설정은 config.py의 MTFA_OPTIMIZED_CONFIG 사용
    
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
    
    async def emergency_stop(self):
        """비상 정지 - 모든 포지션 즉시 청산 및 시스템 완전 중지"""
        logger.critical("🚨 비상 정지 실행 시작")
        
        try:
            # 1. 거래 엔진 즉시 중지
            self.is_running = False
            
            # 2. 모든 진행중인 작업 취소
            if self.signal_task and not self.signal_task.done():
                self.signal_task.cancel()
                try:
                    await self.signal_task
                except asyncio.CancelledError:
                    pass
            
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # 3. API 매니저 즉시 중지
            await api_manager.stop_worker()
            
            # 4. 모든 활성 포지션 강제 청산
            # 사용자 세션 거래 상태 참조
            session_trading_state = self.user_session.trading_state if self.user_session else trading_state
            
            initial_positions_count = len(session_trading_state.positions)
            emergency_close_tasks = []
            positions_to_close = list(session_trading_state.positions.keys())
            
            for coin_symbol in positions_to_close:
                logger.critical(f"🚨 {coin_symbol} 포지션 비상 청산 시작")
                task = asyncio.create_task(self._emergency_close_position(coin_symbol, session_trading_state))
                emergency_close_tasks.append(task)
            
            # 모든 포지션 청산 완료 대기 (최대 30초)
            if emergency_close_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*emergency_close_tasks, return_exceptions=True),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.error("⚠️ 포지션 청산 시간 초과 - 일부 포지션이 청산되지 않았을 수 있습니다")
            
            # 5. 진행중인 주문 취소 시도
            await self._cancel_all_pending_orders()
            
            # 6. 상태 초기화
            self.trading_start_time = None
            self.session_start_time = None
            
            # 7. 청산 결과 검증 및 경고
            remaining_positions = len(session_trading_state.positions)
            successfully_closed = initial_positions_count - remaining_positions
            
            if remaining_positions > 0:
                remaining_coins = list(session_trading_state.positions.keys())
                logger.error(f"⚠️ 비상 정지 후에도 {remaining_positions}개 포지션이 남아있습니다: {remaining_coins}")
                logger.error("🚨 중요: 수동으로 업비트에서 해당 포지션들을 확인하고 필요시 직접 매도하세요")
                
                # 주의: 실제로 매도되지 않은 포지션은 메모리에서 제거하지 않음
                # 사용자가 수동으로 처리할 수 있도록 유지
            
            success_message = f"비상 정지 완료 - {successfully_closed}/{initial_positions_count}개 포지션 청산"
            if remaining_positions > 0:
                success_message += f", {remaining_positions}개 미완료 (수동 확인 필요)"
            
            logger.critical(f"✅ {success_message}")
            return {
                "success": True, 
                "message": success_message,
                "details": {
                    "initial_positions": initial_positions_count,
                    "successfully_closed": successfully_closed,
                    "remaining_positions": remaining_positions,
                    "remaining_coins": list(session_trading_state.positions.keys()) if remaining_positions > 0 else []
                }
            }
            
        except Exception as e:
            logger.critical(f"❌ 비상 정지 중 오류 발생: {str(e)}")
            return {"success": False, "message": f"비상 정지 중 오류: {str(e)}"}
    
    async def _emergency_close_position(self, coin_symbol: str, session_trading_state=None):
        """개별 포지션 비상 청산"""
        try:
            # 사용자 세션 거래 상태 사용 (매개변수로 전달된 것 우선, 없으면 self.user_session 사용)
            if session_trading_state is None:
                session_trading_state = self.user_session.trading_state if self.user_session else trading_state
            
            if coin_symbol not in session_trading_state.positions:
                return
            
            position = session_trading_state.positions[coin_symbol]
            market = f"KRW-{coin_symbol}"
            
            upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
            if not upbit_client:
                logger.error(f"⚠️ {coin_symbol} 비상 청산 실패: 업비트 클라이언트 없음")
                return
            
            logger.critical(f"🚨 {coin_symbol} 시장가 매도 실행 (수량: {position.amount:.8f})")
            
            # 시장가 매도 주문
            sell_result = await upbit_client.place_market_sell_order(market, position.amount)
            
            if sell_result.get("success", False):
                # 실제 매도 가격 및 손익 계산
                sell_price = sell_result.get("avg_price", position.current_price)
                realized_pnl = (sell_price - position.buy_price) * position.amount
                
                logger.critical(f"✅ {coin_symbol} 비상 청산 완료")
                logger.critical(f"   매도 가격: {sell_price:,.0f} KRW")
                logger.critical(f"   실현 손익: {realized_pnl:+,.0f} KRW")
                
                # 포지션 제거
                del session_trading_state.positions[coin_symbol]
                
                # 거래 기록 업데이트
                session_trading_state.daily_trades += 1
                if realized_pnl < 0:
                    session_trading_state.daily_loss += abs(realized_pnl)
                
            else:
                logger.error(f"❌ {coin_symbol} 비상 청산 실패: {sell_result.get('message', '알 수 없는 오류')}")
                
        except Exception as e:
            logger.error(f"❌ {coin_symbol} 비상 청산 중 오류: {str(e)}")
    
    async def _cancel_all_pending_orders(self):
        """모든 미체결 주문 취소"""
        try:
            upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
            if not upbit_client:
                return
            
            # 미체결 주문 조회
            pending_orders = await upbit_client.get_orders(state='wait')
            
            if pending_orders and len(pending_orders) > 0:
                logger.critical(f"🚨 미체결 주문 {len(pending_orders)}개 취소 시작")
                
                for order in pending_orders:
                    try:
                        order_id = order.get('uuid')
                        market = order.get('market')
                        
                        cancel_result = await upbit_client.cancel_order(order_id)
                        if cancel_result.get("success", False):
                            logger.critical(f"✅ 주문 취소 완료: {market} ({order_id})")
                        else:
                            logger.error(f"❌ 주문 취소 실패: {market} ({order_id})")
                            
                    except Exception as e:
                        logger.error(f"❌ 개별 주문 취소 오류: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ 미체결 주문 취소 중 오류: {str(e)}")
    
    async def check_emergency_conditions(self):
        """비상정지 자동 트리거 조건 확인"""
        try:
            # 사용자 세션 거래 상태 참조
            session_trading_state = self.user_session.trading_state if self.user_session else trading_state
            
            # 1. 일일 손실 한도 확인
            if session_trading_state.daily_loss >= 50000:  # 5만원 손실
                logger.critical(f"🚨 일일 손실 한도 도달: {session_trading_state.daily_loss:,.0f}원")
                await self.emergency_stop()
                return True
            
            # 2. 연속 거래 실패 확인 (향후 구현용)
            consecutive_failures = getattr(self, '_consecutive_failures', 0)
            if consecutive_failures >= 5:
                logger.critical(f"🚨 연속 거래 실패 {consecutive_failures}회 도달")
                await self.emergency_stop()
                return True
            
            # 3. 시스템 과부하 확인 (향후 구현용)
            # API 응답시간, 메모리 사용량 등 모니터링
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 비상정지 조건 확인 오류: {str(e)}")
            return False
    
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
                # 비상정지 조건 확인 (우선순위)
                emergency_triggered = await self.check_emergency_conditions()
                if emergency_triggered:
                    break  # 비상정지가 실행되면 루프 중단
                
                await self._monitor_positions()
                await asyncio.sleep(5)  # 5초마다 포지션 체크 (강화)
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
        
        # 사용자 세션 거래 상태 참조
        session_trading_state = self.user_session.trading_state if self.user_session else trading_state
        
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
                if session_trading_state.available_budget <= 0:
                    logger.warning("⚠️ 업비트 로그인이 필요합니다. 거래를 중단합니다.")
                    self._complete_coin_processing(coin_symbol, "error", "로그인 필요")
                    return
                
                investment_amount = min(200000, session_trading_state.available_budget * 0.2)
                
                if not session_trading_state.can_trade_coin(coin_symbol, investment_amount):
                    self._complete_coin_processing(coin_symbol, "skipped", "거래 불가")
                    continue
                
                # 신호 분석 실행 (MTFA 최적화 설정 사용)
                market_config = MTFA_OPTIMIZED_CONFIG.get(market, MTFA_OPTIMIZED_CONFIG["KRW-BTC"])
                
                # SignalAnalyzer가 기대하는 파라미터 형식으로 변환
                signal_params = {
                    "volume_surge": 2.0,
                    "price_change": 0.5, 
                    "mtfa_threshold": market_config.get("mtfa_threshold", 0.80),
                    "rsi_period": 14,
                    "ema_periods": [5, 20],
                    "volume_window": 24
                }
                
                signal = await signal_analyzer.check_buy_signal(market, signal_params)
                
                # API 호출 시간 기록 (코인별 + 전역)
                self.api_call_scheduler["last_call_times"][coin_symbol] = current_time
                self.api_call_scheduler["last_global_call"] = current_time
                
                if signal and signal["should_buy"]:
                    logger.info(f"📈 {coin_symbol} 매수 신호 감지!")
                    logger.info(f"   신호 강도: {signal['signal_strength']}")
                    logger.info(f"   사유: {signal['reason']}")
                    
                    # 매수 주문 실행
                    await self._execute_buy_order(market, coin_symbol, investment_amount, signal, session_trading_state)
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
        """고급 포지션 모니터링 및 자동 손익실현"""
        positions_to_close = []
        positions_for_partial_sale = []
        
        # 사용자 세션 거래 상태 참조
        session_trading_state = self.user_session.trading_state if self.user_session else trading_state
        
        for coin, position in session_trading_state.positions.items():
            try:
                market = f"KRW-{coin}"
                
                # 현재 가격 업데이트
                current_price = await self._get_current_price(market)
                if not current_price:
                    continue
                    
                position.update_current_price(current_price)
                
                # 가격 캐시 저장 (성공시)
                setattr(self, f'_cached_price_{market.replace("-", "_")}', current_price)
                setattr(self, f'_cached_time_{market.replace("-", "_")}', time.time())
                
                # 수익률 및 보유시간 계산
                profit_percent = ((current_price - position.buy_price) / position.buy_price) * 100
                holding_time = (datetime.now() - position.timestamp).total_seconds()
                
                # 고급 포지션 분석 및 액션 결정
                recommended_action = position.get_recommended_action()
                profit_stage_action = position.get_profit_stage_action()
                risk_assessment = position.get_risk_assessment()
                
                # 💎 고급 액션 처리
                if recommended_action == "immediate_sell":
                    logger.warning(f"🚨 {coin} 즉시 매도 - 고위험 상황 (손실: {profit_percent:.2f}%)")
                    positions_to_close.append((coin, "high_risk_sell"))
                    continue
                    
                elif recommended_action == "trailing_stop_sell":
                    trailing_price = position.get_trailing_stop_price()
                    logger.info(f"📉 {coin} 트레일링 스탑 실행 (트레일링가: {trailing_price:,.0f})")
                    positions_to_close.append((coin, "trailing_stop"))
                    continue
                    
                elif recommended_action == "target_reached":
                    logger.success(f"🎯 {coin} 목표 수익률 달성! (수익: {profit_percent:.2f}%)")
                    positions_to_close.append((coin, "target_profit"))
                    continue
                    
                elif recommended_action == "partial_profit":
                    logger.info(f"💰 {coin} 부분 익절 실행 (수익: {profit_percent:.2f}%)")
                    positions_for_partial_sale.append(coin)
                    
                elif recommended_action == "take_profit_now":
                    logger.info(f"⏰ {coin} 시간 기반 익절 (보유시간: {holding_time:.0f}초, 수익: {profit_percent:.2f}%)")
                    positions_to_close.append((coin, "time_based_profit"))
                    continue
                
                # 🎚️ 수익 단계별 알림 처리
                if profit_stage_action == "enable_trailing_stop":
                    logger.info(f"🔄 {coin} 트레일링 스탑 활성화 (수익: {profit_percent:.2f}%)")
                    
                elif profit_stage_action == "suggest_partial_profit":
                    logger.info(f"💡 {coin} 부분 익절 제안 (수익: {profit_percent:.2f}%)")
                    
                elif profit_stage_action == "suggest_full_profit":
                    logger.info(f"💡 {coin} 전체 익절 강력 제안 (수익: {profit_percent:.2f}%)")
                
                # PDF 가이드 적용: TP/SL 동시 발생시 더 보수적인 접근 (실제 캔들 분석 기반)
                tp_hit = current_price >= position.profit_target
                sl_hit = current_price <= position.stop_loss
                
                # PDF 리뷰 적용: TP/SL 시간 기반 우선순위 로직 (실제 캔들 시퀀스 분석)
                if tp_hit and sl_hit:
                    # 시간 기반 우선순위 결정 (PDF 가이드: 실제 발생 순서 추정)
                    
                    # 1) 급락 상황 감지: 최근 가격 변동률로 판단
                    recent_price_change = ((current_price - position.buy_price) / position.buy_price) * 100
                    
                    # 2) 포지션의 최고가 대비 현재가 위치로 추세 판단
                    if hasattr(position, 'highest_price_seen') and position.highest_price_seen > position.buy_price:
                        max_gain_achieved = ((position.highest_price_seen - position.buy_price) / position.buy_price) * 100
                        current_from_peak = ((current_price - position.highest_price_seen) / position.highest_price_seen) * 100
                    else:
                        max_gain_achieved = recent_price_change
                        current_from_peak = 0
                    
                    # 3) 시간 기반 우선순위 로직 (PDF 권장사항)
                    if recent_price_change < -0.5 and current_from_peak < -1.0:
                        # 급락 패턴: SL이 시간상 먼저 발생했을 가능성 높음
                        exit_reason = "time_based_stop_loss"
                        logger.warning(f"📉 {coin} 급락 패턴 감지 - SL 우선 처리")
                        logger.info(f"   가격변동: {recent_price_change:.2f}%, 고점대비: {current_from_peak:.2f}%")
                    elif max_gain_achieved > 0.3 and current_from_peak > -0.3:
                        # 상승 후 조정: TP가 먼저 달성 후 하락했을 가능성
                        exit_reason = "time_based_profit_target"  
                        logger.info(f"📈 {coin} 상승 후 조정 패턴 - TP 우선 처리")
                        logger.info(f"   최대수익: {max_gain_achieved:.2f}%, 고점대비: {current_from_peak:.2f}%")
                    else:
                        # 불분명한 경우: 보수적 접근 (리스크 관리 우선)
                        exit_reason = "conservative_stop_loss"
                        logger.warning(f"⚠️ {coin} TP/SL 동시 달성 - 보수적 SL 처리")
                        logger.info(f"   현재가: {current_price:,.0f}, 익절가: {position.profit_target:,.0f}, 손절가: {position.stop_loss:,.0f}")
                    
                    positions_to_close.append((coin, exit_reason))
                    continue
                elif tp_hit:
                    logger.info(f"🎯 {coin} 익절 조건 달성 (목표가: {position.profit_target:,.0f})")
                    positions_to_close.append((coin, "profit_target"))
                    continue
                elif sl_hit:
                    logger.info(f"🛑 {coin} 손절 조건 달성 (손절가: {position.stop_loss:,.0f})")
                    positions_to_close.append((coin, "stop_loss"))
                    continue
                
                # MTFA 최적화된 개별 코인별 최대 보유 시간 사용
                market_config = MTFA_OPTIMIZED_CONFIG.get(f"KRW-{coin}", {})
                max_hold_minutes = market_config.get("max_hold_minutes", 60)  # 기본값 60분
                max_hold_seconds = max_hold_minutes * 60
                
                if holding_time > max_hold_seconds:
                    logger.info(f"⏰ {coin} 최대 보유 시간 초과 ({holding_time:.0f}초)")
                    positions_to_close.append((coin, "max_time"))
                    continue
                
                # 📊 상세 포지션 로깅 (30초마다)
                if int(holding_time) % 30 == 0:
                    trend_icon = "📈" if position.trend_direction == "up" else "📉" if position.trend_direction == "down" else "➡️"
                    logger.info(f"{trend_icon} {coin} 포지션: {profit_percent:+.2f}% | 위험도: {risk_assessment} | 추세: {position.trend_direction} | 시간: {holding_time:.0f}초")
                
            except Exception as e:
                logger.error(f"⚠️ {coin} 포지션 모니터링 오류: {str(e)}")
        
        # 부분 익절 처리
        for coin in positions_for_partial_sale:
            try:
                await self._execute_partial_sale(coin, 0.5)  # 50% 부분 익절
            except Exception as e:
                logger.error(f"⚠️ {coin} 부분 익절 오류: {str(e)}")
        
        # 전체 청산 처리
        for coin, reason in positions_to_close:
            try:
                await self._close_position(coin, reason)
            except Exception as e:
                logger.error(f"⚠️ {coin} 포지션 청산 오류: {str(e)}")
    
    async def _execute_partial_sale(self, coin: str, sell_ratio: float = 0.5):
        """부분 익절 실행"""
        try:
            session_trading_state = self.user_session.trading_state if self.user_session else trading_state
            if coin not in session_trading_state.positions:
                return
                
            position = session_trading_state.positions[coin]
            market = f"KRW-{coin}"
            
            # 부분 매도 수량 계산
            sell_amount = position.amount * sell_ratio
            remaining_amount = position.amount - sell_amount
            
            upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
            if not upbit_client:
                logger.error(f"⚠️ {coin} 부분 익절 실패: 업비트 클라이언트 없음")
                return
            
            logger.info(f"💰 {coin} 부분 익절 실행 ({sell_ratio*100:.0f}%)")
            logger.info(f"   판매 수량: {sell_amount:.8f}")
            logger.info(f"   잔여 수량: {remaining_amount:.8f}")
            
            # 시장가 매도 주문 실행
            sell_result = await upbit_client.place_market_sell_order(market, sell_amount)
            
            if sell_result.get("success", False):
                # 거래 검증 생성
                order_id = sell_result.get("uuid", f"partial_{int(time.time())}")
                verification = await trade_verifier.create_verification(
                    order_id=order_id,
                    market=market,
                    side="ask",
                    order_type="market",
                    requested_amount=sell_amount,
                    requested_price=position.current_price,
                    upbit_client=upbit_client
                )
                
                sell_price = sell_result.get("avg_price", position.current_price)
                realized_pnl = (sell_price - position.buy_price) * sell_amount
                
                logger.info(f"✅ {coin} 부분 익절 주문 실행")
                logger.info(f"   주문 ID: {order_id}")
                logger.info(f"   매도 가격: {sell_price:,.0f} KRW")
                logger.info(f"   실현 수익: {realized_pnl:+,.0f} KRW")
                
                # 포지션 수량 업데이트
                position.amount = remaining_amount
                position.partial_profit_taken = True
                
                # 잔여 포지션이 너무 작으면 전체 정리
                if remaining_amount < 0.00001:  # 아주 작은 수량
                    logger.info(f"🧹 {coin} 잔여 수량 미미 - 전체 정리")
                    del session_trading_state.positions[coin]
                    session_trading_state.reserved_budget = 0  # 정리
                else:
                    # 예산 일부 해제
                    released_budget = sell_amount * position.buy_price
                    session_trading_state.available_budget += released_budget
                    session_trading_state.reserved_budget -= released_budget
                
                # 거래 통계 업데이트
                session_trading_state.daily_trades += 1
                
                # 비동기로 주문 검증 시작 (1초 후)
                asyncio.create_task(self._verify_order_after_delay(order_id, upbit_client, 1))
                
            else:
                logger.error(f"❌ {coin} 부분 익절 실패: {sell_result.get('message', '알 수 없는 오류')}")
                
        except Exception as e:
            logger.error(f"❌ {coin} 부분 익절 중 오류: {str(e)}")
    
    async def _execute_buy_order(self, market: str, coin_symbol: str, investment_amount: float, signal: Dict, session_trading_state):
        """매수 주문 실행"""
        try:
            upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
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
                # 거래 검증 생성
                order_id = order_result.get("uuid", f"manual_{int(time.time())}")
                verification = await trade_verifier.create_verification(
                    order_id=order_id,
                    market=market,
                    side="bid",
                    order_type="market",
                    requested_amount=buy_amount,
                    requested_price=current_price,
                    upbit_client=upbit_client
                )
                
                logger.info(f"📋 {coin_symbol} 매수 주문 검증 시작 (ID: {order_id})")
                
                # 포지션 생성 - PDF 리뷰 적용: 신뢰도 기반 TP/SL 정책
                signal_confidence = signal.get("confidence", 50) / 100  # 퍼센트를 소수점으로 변환
                
                # 1단계: 신뢰도 기반 TP/SL 정책 우선 적용
                dynamic_tp_pct, dynamic_sl_pct = get_risk_reward_from_confidence(signal_confidence)
                
                # 2단계: MTFA 최적화 설정과 비교하여 더 보수적인 값 선택
                market_config = MTFA_OPTIMIZED_CONFIG.get(market, {})
                static_tp_pct = market_config.get("profit_target", 2.5)  
                static_sl_pct = abs(market_config.get("stop_loss", -1.0))  # 절댓값 변환
                
                # 보수적 접근: 더 작은 TP, 더 큰 SL 선택
                final_tp_pct = min(dynamic_tp_pct, static_tp_pct)
                final_sl_pct = max(dynamic_sl_pct, -static_sl_pct)  # 음수 유지
                
                profit_target_price = current_price * (1 + final_tp_pct / 100)
                stop_loss_price = current_price * (1 + final_sl_pct / 100)
                
                logger.info(f"📊 {coin_symbol} 신뢰도 기반 TP/SL 설정:")
                logger.info(f"   신뢰도: {signal_confidence:.2f} → TP: {dynamic_tp_pct}%, SL: {dynamic_sl_pct}%")
                logger.info(f"   MTFA 설정: TP: {static_tp_pct}%, SL: {-static_sl_pct}%")
                logger.info(f"   최종 적용: TP: {final_tp_pct}%, SL: {final_sl_pct}%")
                
                position = Position(
                    coin=coin_symbol,
                    buy_price=current_price,
                    amount=buy_amount,
                    timestamp=datetime.now(),
                    profit_target=profit_target_price,
                    stop_loss=stop_loss_price
                )
                
                # 포지션에 주문 ID 추가 (검증 추적용)
                position.order_id = order_id
                
                # 거래 상태 업데이트
                session_trading_state.positions[coin_symbol] = position
                session_trading_state.available_budget -= investment_amount
                session_trading_state.reserved_budget += investment_amount
                session_trading_state.daily_trades += 1
                session_trading_state.last_trade_time[coin_symbol] = datetime.now()
                
                logger.info(f"✅ {coin_symbol} 매수 주문 실행!")
                logger.info(f"   주문 ID: {order_id}")
                logger.info(f"   익절가: {profit_target_price:,.0f} KRW")
                logger.info(f"   손절가: {stop_loss_price:,.0f} KRW")
                
                # 비동기로 주문 검증 시작 (1초 후)
                asyncio.create_task(self._verify_order_after_delay(order_id, upbit_client, 1))
                
            else:
                logger.error(f"❌ {coin_symbol} 매수 주문 실패: {order_result.get('error', '알 수 없는 오류')}")
                
        except Exception as e:
            logger.error(f"⚠️ {coin_symbol} 매수 주문 오류: {str(e)}")
    
    async def _get_current_price(self, market: str) -> Optional[float]:
        """현재 가격 조회 (3단계 Fallback 시스템 - PDF 가이드 개선 적용)"""
        max_retries = 2
        
        # 1단계: API 매니저를 통한 조회 (재시도 포함)
        for attempt in range(max_retries):
            try:
                upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
                if not upbit_client:
                    break  # 클라이언트 없으면 2단계로
                
                ticker_data = await asyncio.wait_for(
                    api_manager.safe_api_call(
                        upbit_client, 
                        'get_single_ticker', 
                        market,
                        priority=APIPriority.POSITION_MONITORING
                    ),
                    timeout=5.0  # 5초 타임아웃
                )
                
                # 응답 구조 검증 및 파싱
                if ticker_data:
                    # dict에 error가 있으면 재시도
                    if isinstance(ticker_data, dict) and "error" in ticker_data:
                        logger.warning(f"⚠️ {market} 1단계 가격 조회 실패 (시도 {attempt + 1}): {ticker_data.get('error')}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                    elif isinstance(ticker_data, dict) and "trade_price" in ticker_data:
                        price = float(ticker_data["trade_price"])
                        if price > 0:  # 가격 유효성 검증
                            return price
                    elif isinstance(ticker_data, list) and len(ticker_data) > 0 and "trade_price" in ticker_data[0]:
                        price = float(ticker_data[0]["trade_price"])
                        if price > 0:  # 가격 유효성 검증
                            return price
                
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {market} 1단계 API 호출 타임아웃 (시도 {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
            except (ConnectionError, OSError) as e:
                logger.warning(f"⚠️ {market} 1단계 네트워크 오류 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ {market} 1단계 데이터 타입 오류: {str(e)}")
                break  # 타입 오류는 재시도 의미 없음
            except Exception as e:
                logger.warning(f"⚠️ {market} 1단계 예상치 못한 오류 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
        
        # 2단계: 직접 업비트 클라이언트 호출 (재시도 포함)
        for attempt in range(max_retries):
            try:
                upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
                if not upbit_client:
                    break  # 클라이언트 없으면 3단계로
                
                ticker_result = await asyncio.wait_for(
                    upbit_client.get_ticker([market]),
                    timeout=8.0  # 8초 타임아웃
                )
                
                if ticker_result and len(ticker_result) > 0 and "trade_price" in ticker_result[0]:
                    price = float(ticker_result[0]["trade_price"])
                    if price > 0:  # 가격 유효성 검증
                        logger.info(f"✅ {market} 2단계 가격 조회 성공: {price:,.0f}원")
                        return price
                        
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ {market} 2단계 API 호출 타임아웃 (시도 {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except (ConnectionError, OSError) as e:
                logger.warning(f"⚠️ {market} 2단계 네트워크 오류 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"⚠️ {market} 2단계 데이터 파싱 오류: {str(e)}")
                break  # 파싱 오류는 재시도 의미 없음
            except Exception as e:
                logger.warning(f"⚠️ {market} 2단계 예상치 못한 오류 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
        
        # 3단계: 캐시된 가격 사용 (최대 2분, 가격 유효성 검증 포함)
        try:
            cached_price = getattr(self, f'_cached_price_{market.replace("-", "_")}', None)
            cached_time = getattr(self, f'_cached_time_{market.replace("-", "_")}', 0)
            
            if cached_price and cached_price > 0 and (time.time() - cached_time) < 120:  # 2분 이내 + 가격 유효성
                logger.info(f"💾 {market} 캐시된 가격 사용: {cached_price:,.0f}원 (캐시 나이: {time.time() - cached_time:.0f}초)")
                return cached_price
                
        except (AttributeError, ValueError, TypeError) as e:
            logger.warning(f"⚠️ {market} 캐시 가격 조회 오류: {str(e)}")
        except Exception as e:
            logger.error(f"❌ {market} 캐시 가격 예상치 못한 오류: {str(e)}")
        
        logger.error(f"❌ {market} 모든 가격 조회 방법 실패 - 매수/매도 신호 무시 권장")
        return None
    
    async def _close_position(self, coin: str, reason: str = "manual"):
        """고급 포지션 청산 - 매도 이유 기록"""
        try:
            # 사용자 세션 거래 상태 참조
            session_trading_state = self.user_session.trading_state if self.user_session else trading_state
            
            if coin not in session_trading_state.positions:
                logger.warning(f"⚠️ {coin} 포지션이 존재하지 않습니다")
                return
            
            position = session_trading_state.positions[coin]
            upbit_client = self.user_session.upbit_client if self.user_session else get_upbit_client()
            
            if not upbit_client:
                logger.error("⚠️ 업비트 클라이언트가 연결되지 않았습니다")
                return
            
            market = f"KRW-{coin}"
            
            # 청산 전 상태 분석
            profit_percent = ((position.current_price - position.buy_price) / position.buy_price) * 100
            holding_time = (datetime.now() - position.timestamp).total_seconds()
            
            # 매도 이유별 로그 메시지
            reason_messages = {
                "profit_target": "🎯 목표 수익률 달성",
                "stop_loss": "🛑 손절 실행",
                "trailing_stop": "📉 트레일링 스탑 실행",
                "high_risk_sell": "🚨 고위험 즉시 매도",
                "time_based_profit": "⏰ 시간 기반 익절",
                "target_profit": "🎯 목표가 도달",
                "max_time": "⏰ 최대 보유시간 초과",
                "manual": "👤 수동 청산",
                "emergency": "🚨 비상 청산"
            }
            
            reason_message = reason_messages.get(reason, f"💰 포지션 청산 ({reason})")
            
            logger.info(f"{reason_message}")
            logger.info(f"   코인: {coin}")
            logger.info(f"   보유 수량: {position.amount:.8f}")
            logger.info(f"   매수 가격: {position.buy_price:,.0f} KRW")
            logger.info(f"   현재 가격: {position.current_price:,.0f} KRW")
            logger.info(f"   수익률: {profit_percent:+.2f}%")
            logger.info(f"   보유시간: {holding_time:.0f}초")
            
            if position.trailing_stop_enabled:
                trailing_price = position.get_trailing_stop_price()
                logger.info(f"   트레일링가: {trailing_price:,.0f} KRW (최고가: {position.highest_price_seen:,.0f})")
            
            # 실제 매도 주문 (시장가)
            order_result = await upbit_client.place_market_sell_order(market, position.amount)
            
            if order_result.get("success", False):
                # 거래 검증 생성
                order_id = order_result.get("uuid", f"sell_{int(time.time())}")
                verification = await trade_verifier.create_verification(
                    order_id=order_id,
                    market=market,
                    side="ask",
                    order_type="market",
                    requested_amount=position.amount,
                    requested_price=position.current_price,
                    upbit_client=upbit_client
                )
                
                logger.info(f"📋 {coin} 매도 주문 검증 시작 (ID: {order_id})")
                
                # 실제 매도 가격 (주문 결과에서 가져오기)
                actual_sell_price = order_result.get("avg_price", position.current_price)
                realized_pnl = (actual_sell_price - position.buy_price) * position.amount
                realized_percent = ((actual_sell_price - position.buy_price) / position.buy_price) * 100
                
                # 거래 상태 업데이트
                session_trading_state.available_budget += (actual_sell_price * position.amount)
                session_trading_state.reserved_budget -= (position.buy_price * position.amount)
                
                if realized_pnl < 0:
                    session_trading_state.daily_loss += abs(realized_pnl)
                
                # 포지션 제거
                del session_trading_state.positions[coin]
                session_trading_state.daily_trades += 1
                
                # 성과 분석 로깅
                result_icon = "💚" if realized_pnl > 0 else "❤️" if realized_pnl < 0 else "💛"
                logger.info(f"✅ {coin} 매도 주문 실행! {result_icon}")
                logger.info(f"   주문 ID: {order_id}")
                logger.info(f"   실제 매도가: {actual_sell_price:,.0f} KRW")
                logger.info(f"   실현 손익: {realized_pnl:+,.0f} KRW ({realized_percent:+.2f}%)")
                logger.info(f"   매도 사유: {reason}")
                
                # 트레일링 스탑 성과 분석
                if reason == "trailing_stop":
                    max_potential_profit = (position.highest_price_seen - position.buy_price) * position.amount
                    trailing_efficiency = (realized_pnl / max_potential_profit) * 100 if max_potential_profit > 0 else 0
                    logger.info(f"   트레일링 효율성: {trailing_efficiency:.1f}% (최대 가능 수익 대비)")
                
                # 부분 익절 이력이 있는 경우
                if position.partial_profit_taken:
                    logger.info(f"   📊 부분 익절 완료된 포지션")
                
                # 비동기로 주문 검증 시작 (1초 후)
                asyncio.create_task(self._verify_order_after_delay(order_id, upbit_client, 1))
                
            else:
                logger.error(f"❌ {coin} 매도 주문 실패: {order_result.get('error', '알 수 없는 오류')}")
                logger.error(f"   매도 시도 사유: {reason}")
            
        except Exception as e:
            logger.error(f"⚠️ {coin} 포지션 청산 오류 (사유: {reason}): {str(e)}")
    
    async def _verify_order_after_delay(self, order_id: str, upbit_client, delay: int):
        """지연 후 주문 검증"""
        try:
            await asyncio.sleep(delay)
            
            # 최대 3회까지 검증 시도
            for attempt in range(3):
                success = await trade_verifier.verify_order_with_client(order_id, upbit_client)
                if success:
                    logger.debug(f"✅ 주문 검증 완료: {order_id}")
                    break
                
                if attempt < 2:  # 마지막 시도가 아니면 대기
                    await asyncio.sleep(5)  # 5초 대기 후 재시도
            
        except Exception as e:
            logger.error(f"❌ 주문 검증 오류 ({order_id}): {str(e)}")
    
    def get_verification_summary(self) -> Dict:
        """거래 검증 요약 정보"""
        try:
            return trade_verifier.get_trading_metrics()
        except Exception as e:
            logger.error(f"❌ 검증 요약 조회 오류: {str(e)}")
            return {}
    
    def get_status(self) -> dict:
        """거래 엔진 상태 조회"""
        # 사용자 세션 거래 상태 참조
        session_trading_state = self.user_session.trading_state if self.user_session else trading_state
        
        return {
            "is_running": self.is_running,
            "positions_count": len(session_trading_state.positions),
            "available_budget": session_trading_state.available_budget,
            "daily_trades": session_trading_state.daily_trades,
            "daily_loss": session_trading_state.daily_loss,
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