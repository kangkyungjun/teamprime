"""
거래 실행 검증 서비스
주문 체결 확인, 슬리피지 분석, 거래 성과 검증
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..models.trading import TradeVerification, TradingMetrics
from api_client import UpbitAPI

logger = logging.getLogger(__name__)

class TradeVerificationService:
    """거래 검증 서비스"""
    
    def __init__(self):
        self.pending_verifications: Dict[str, TradeVerification] = {}
        self.completed_verifications: Dict[str, TradeVerification] = {}
        self.trading_metrics = TradingMetrics()
        
        # 검증 설정
        self.max_verification_attempts = 10
        self.verification_interval = 5  # 5초마다 검증
        self.verification_timeout = 300  # 5분 타임아웃
        self.max_acceptable_slippage = 0.2  # 0.2% 최대 허용 슬리피지
        
        # 검증 루프 실행 상태
        self.verification_loop_running = False
        
        logger.info("✅ 거래 검증 서비스 초기화 완료")
    
    async def create_verification(
        self, 
        order_id: str, 
        market: str, 
        side: str, 
        order_type: str,
        requested_amount: float,
        requested_price: Optional[float] = None,
        upbit_client: Optional[UpbitAPI] = None
    ) -> TradeVerification:
        """새로운 거래 검증 생성"""
        try:
            verification = TradeVerification(
                order_id=order_id,
                market=market,
                side=side,
                order_type=order_type,
                requested_amount=requested_amount,
                requested_price=requested_price,
                order_timestamp=datetime.now()
            )
            
            # 시장가 주문의 경우 현재 가격을 기준가로 설정
            if order_type == "market" and not requested_price and upbit_client:
                try:
                    ticker = await upbit_client.get_single_ticker(market)
                    if ticker:
                        verification.requested_price = float(ticker.get("trade_price", 0))
                except Exception as e:
                    logger.warning(f"⚠️ 시장가 기준가 설정 실패 ({market}): {str(e)}")
            
            self.pending_verifications[order_id] = verification
            
            logger.info(f"📋 거래 검증 생성: {market} {side} {requested_amount:.8f}")
            logger.info(f"   주문 ID: {order_id}")
            logger.info(f"   주문 유형: {order_type}")
            
            # 검증 루프가 실행되지 않고 있으면 시작
            if not self.verification_loop_running:
                asyncio.create_task(self._start_verification_loop())
            
            return verification
            
        except Exception as e:
            logger.error(f"❌ 거래 검증 생성 실패: {str(e)}")
            raise
    
    async def _start_verification_loop(self):
        """거래 검증 루프 시작"""
        if self.verification_loop_running:
            return
        
        self.verification_loop_running = True
        logger.info("🔄 거래 검증 루프 시작")
        
        try:
            while self.pending_verifications or self.verification_loop_running:
                if not self.pending_verifications:
                    await asyncio.sleep(10)  # 대기 중인 검증이 없으면 10초 대기
                    continue
                
                # 검증 대상 목록 복사 (중간에 변경될 수 있으므로)
                verifications_to_check = list(self.pending_verifications.values())
                
                for verification in verifications_to_check:
                    try:
                        await self._verify_trade(verification)
                        await asyncio.sleep(1)  # API 요청 간격
                    except Exception as e:
                        logger.error(f"❌ 거래 검증 실패 ({verification.order_id}): {str(e)}")
                
                await asyncio.sleep(self.verification_interval)
                
        except Exception as e:
            logger.error(f"❌ 거래 검증 루프 오류: {str(e)}")
        finally:
            self.verification_loop_running = False
            logger.info("🔄 거래 검증 루프 종료")
    
    async def _verify_trade(self, verification: TradeVerification):
        """개별 거래 검증"""
        try:
            # 타임아웃 확인
            if (datetime.now() - verification.order_timestamp).total_seconds() > self.verification_timeout:
                verification.verification_status = "timeout"
                self._complete_verification(verification, "타임아웃")
                return
            
            # 최대 시도 횟수 확인
            if verification.verification_attempts >= self.max_verification_attempts:
                verification.verification_status = "failed"
                self._complete_verification(verification, "최대 시도 횟수 초과")
                return
            
            verification.verification_attempts += 1
            verification.last_verification = datetime.now()
            
            # 업비트 클라이언트 필요 - 세션에서 가져와야 함
            # 여기서는 검증만 수행하고, 실제 API 호출은 거래 엔진에서 수행
            logger.debug(f"🔍 거래 검증 시도 #{verification.verification_attempts}: {verification.order_id}")
            
        except Exception as e:
            logger.error(f"❌ 거래 검증 오류 ({verification.order_id}): {str(e)}")
            verification.verification_errors.append(str(e))
    
    async def verify_order_with_client(self, order_id: str, upbit_client: UpbitAPI) -> bool:
        """업비트 클라이언트를 사용한 주문 검증"""
        try:
            if order_id not in self.pending_verifications:
                return False
            
            verification = self.pending_verifications[order_id]
            
            # 주문 상태 조회
            order_info = await upbit_client.get_order(order_id)
            
            if not order_info:
                logger.warning(f"⚠️ 주문 정보 조회 실패: {order_id}")
                return False
            
            # 주문 정보 업데이트
            verification.status = order_info.get("state", "pending")
            verification.filled_amount = float(order_info.get("executed_volume", 0))
            verification.average_price = float(order_info.get("avg_price", 0))
            verification.total_fee = float(order_info.get("paid_fee", 0))
            
            logger.info(f"📊 주문 상태 업데이트: {order_id}")
            logger.info(f"   상태: {verification.status}")
            logger.info(f"   체결량: {verification.filled_amount:.8f}")
            logger.info(f"   평균가: {verification.average_price:,.0f}")
            logger.info(f"   수수료: {verification.total_fee:,.0f}")
            
            # 완료된 주문 처리
            if verification.status in ["done", "cancel"]:
                completion_time = datetime.now()
                verification.calculate_execution_time(completion_time)
                verification.calculate_slippage()
                
                # 슬리피지 검증
                if not verification.is_acceptable_slippage(self.max_acceptable_slippage):
                    logger.warning(f"⚠️ 높은 슬리피지 감지: {verification.slippage:.3f}%")
                
                # 검증 완료
                if verification.status == "done":
                    verification.verification_status = "verified"
                    self._complete_verification(verification, "체결 완료")
                else:
                    verification.verification_status = "cancelled"
                    self._complete_verification(verification, "주문 취소")
                
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"❌ 주문 검증 오류 ({order_id}): {str(e)}")
            if order_id in self.pending_verifications:
                self.pending_verifications[order_id].verification_errors.append(str(e))
            return False
    
    def _complete_verification(self, verification: TradeVerification, reason: str):
        """검증 완료 처리"""
        try:
            logger.info(f"✅ 거래 검증 완료: {verification.order_id}")
            logger.info(f"   완료 사유: {reason}")
            logger.info(f"   체결률: {verification.get_fill_rate():.1f}%")
            
            if verification.execution_time:
                logger.info(f"   체결 시간: {verification.execution_time:.1f}초")
            
            if verification.slippage != 0:
                slippage_icon = "📈" if verification.slippage > 0 else "📉"
                logger.info(f"   슬리피지: {slippage_icon} {verification.slippage:+.3f}%")
            
            # 완료된 검증으로 이동
            if verification.order_id in self.pending_verifications:
                del self.pending_verifications[verification.order_id]
            
            self.completed_verifications[verification.order_id] = verification
            
            # 거래 지표 업데이트
            self.trading_metrics.update_metrics(verification)
            
            # 성과 로깅
            self._log_trading_performance()
            
        except Exception as e:
            logger.error(f"❌ 검증 완료 처리 오류: {str(e)}")
    
    def _log_trading_performance(self):
        """거래 성과 로깅"""
        try:
            metrics = self.trading_metrics
            
            if metrics.total_orders > 0 and metrics.total_orders % 10 == 0:  # 10거래마다 로그
                logger.info("📈 거래 성과 요약")
                logger.info(f"   총 주문: {metrics.total_orders}건")
                logger.info(f"   성공률: {metrics.success_rate:.1f}%")
                logger.info(f"   체결률: {metrics.fill_rate:.1f}%")
                logger.info(f"   평균 슬리피지: {metrics.average_slippage:+.3f}%")
                logger.info(f"   평균 체결시간: {metrics.average_execution_time:.1f}초")
                logger.info(f"   총 수수료: {metrics.total_fees:,.0f}원")
            
        except Exception as e:
            logger.error(f"❌ 성과 로깅 오류: {str(e)}")
    
    def get_verification_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """검증 상태 조회"""
        try:
            verification = None
            
            if order_id in self.pending_verifications:
                verification = self.pending_verifications[order_id]
            elif order_id in self.completed_verifications:
                verification = self.completed_verifications[order_id]
            
            if not verification:
                return None
            
            return {
                "order_id": verification.order_id,
                "market": verification.market,
                "side": verification.side,
                "status": verification.status,
                "verification_status": verification.verification_status,
                "fill_rate": verification.get_fill_rate(),
                "slippage": verification.slippage,
                "execution_time": verification.execution_time,
                "verification_attempts": verification.verification_attempts,
                "last_verification": verification.last_verification.isoformat() if verification.last_verification else None
            }
            
        except Exception as e:
            logger.error(f"❌ 검증 상태 조회 오류: {str(e)}")
            return None
    
    def get_trading_metrics(self) -> Dict[str, Any]:
        """거래 지표 조회"""
        try:
            metrics = self.trading_metrics
            
            return {
                "total_orders": metrics.total_orders,
                "successful_orders": metrics.successful_orders,
                "failed_orders": metrics.failed_orders,
                "cancelled_orders": metrics.cancelled_orders,
                "partial_orders": metrics.partial_orders,
                "success_rate": metrics.success_rate,
                "fill_rate": metrics.fill_rate,
                "average_slippage": metrics.average_slippage,
                "average_execution_time": metrics.average_execution_time,
                "total_volume": metrics.total_volume,
                "total_fees": metrics.total_fees,
                "last_updated": metrics.last_updated.isoformat(),
                "pending_verifications": len(self.pending_verifications),
                "completed_verifications": len(self.completed_verifications)
            }
            
        except Exception as e:
            logger.error(f"❌ 거래 지표 조회 오류: {str(e)}")
            return {}
    
    def get_recent_verifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 검증 결과 조회"""
        try:
            # 완료 시간 기준으로 정렬
            recent_verifications = sorted(
                self.completed_verifications.values(),
                key=lambda x: x.last_verification or x.order_timestamp,
                reverse=True
            )[:limit]
            
            results = []
            for verification in recent_verifications:
                results.append({
                    "order_id": verification.order_id,
                    "market": verification.market,
                    "side": verification.side,
                    "order_type": verification.order_type,
                    "requested_amount": verification.requested_amount,
                    "filled_amount": verification.filled_amount,
                    "average_price": verification.average_price,
                    "status": verification.status,
                    "verification_status": verification.verification_status,
                    "fill_rate": verification.get_fill_rate(),
                    "slippage": verification.slippage,
                    "execution_time": verification.execution_time,
                    "total_fee": verification.total_fee,
                    "order_timestamp": verification.order_timestamp.isoformat(),
                    "last_verification": verification.last_verification.isoformat() if verification.last_verification else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 최근 검증 결과 조회 오류: {str(e)}")
            return []
    
    async def stop_verification_loop(self):
        """검증 루프 중지"""
        self.verification_loop_running = False
        logger.info("🛑 거래 검증 루프 중지 요청")

# 전역 거래 검증 서비스 인스턴스
trade_verifier = TradeVerificationService()