"""
통합 알림 서비스
거래 이벤트, 시스템 상태, 성능 알림 통합 관리
실시간 푸시 알림 및 디바이스 관리
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import hashlib
import uuid

from .monitoring_service import monitoring_service, AlertSeverity

logger = logging.getLogger(__name__)

@dataclass
class TradingEvent:
    """거래 이벤트"""
    event_type: str  # buy, sell, position_opened, position_closed, profit_target, stop_loss
    market: str
    amount: float
    price: float
    profit_loss: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class NotificationService:
    """통합 알림 서비스"""
    
    def __init__(self):
        self.trading_event_handlers: List[Callable] = []
        self.system_event_handlers: List[Callable] = []
        
        # 디바이스 및 사용자 관리
        self.registered_devices: Dict[str, Dict] = {}  # user_id -> device_info
        self.user_settings: Dict[str, Dict] = {}       # user_id -> notification_settings
        self.notification_history: Dict[str, List] = {}  # user_id -> notifications
        
        # 알림 설정
        self.notify_on_trade = True
        self.notify_on_profit = True
        self.notify_on_loss = True
        self.notify_on_system_alerts = True
        
        # 최소 알림 금액 (소액 거래는 알림 안함)
        self.min_notification_amount = 50000  # 5만원 이상
        self.min_profit_notification = 1000   # 1천원 이상 수익
        self.min_loss_notification = 3000     # 3천원 이상 손실
        
        # 알림 큐 및 배치 처리
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        self._batch_task: Optional[asyncio.Task] = None
        
        logger.info("✅ 통합 알림 서비스 초기화 완료")
    
    def register_trading_handler(self, handler: Callable):
        """거래 이벤트 핸들러 등록"""
        self.trading_event_handlers.append(handler)
        logger.info("📈 거래 이벤트 핸들러 등록")
    
    def register_system_handler(self, handler: Callable):
        """시스템 이벤트 핸들러 등록"""
        self.system_event_handlers.append(handler)
        logger.info("⚙️ 시스템 이벤트 핸들러 등록")
    
    async def notify_trade_event(self, event: TradingEvent):
        """거래 이벤트 알림"""
        try:
            if not self.notify_on_trade:
                return
            
            # 소액 거래 필터링
            if event.amount < self.min_notification_amount:
                return
            
            # 이벤트별 메시지 생성
            title, message, severity = self._generate_trade_message(event)
            
            # 모니터링 서비스를 통한 알림
            await monitoring_service.send_alert(
                title=title,
                message=message,
                severity=severity,
                service="trading",
                tags={
                    "event_type": event.event_type,
                    "market": event.market,
                    "amount": str(event.amount)
                }
            )
            
            # 메트릭 추가
            from .monitoring_service import MetricType
            monitoring_service.add_metric(
                f"trading.{event.event_type}",
                1,
                MetricType.COUNTER,
                tags={"market": event.market}
            )
            
            if event.profit_loss is not None:
                monitoring_service.add_metric(
                    "trading.profit_loss",
                    event.profit_loss,
                    MetricType.HISTOGRAM,
                    tags={"market": event.market},
                    unit="KRW"
                )
            
            # 커스텀 핸들러 실행
            for handler in self.trading_event_handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"❌ 거래 이벤트 핸들러 오류: {str(e)}")
                    
        except Exception as e:
            logger.error(f"❌ 거래 이벤트 알림 오류: {str(e)}")
    
    def _generate_trade_message(self, event: TradingEvent) -> tuple:
        """거래 이벤트 메시지 생성"""
        try:
            if event.event_type == "buy":
                title = f"🔵 매수 완료 - {event.market}"
                message = f"{event.market}을 {event.amount:,.0f}원에 매수했습니다 (가격: {event.price:,.0f}원)"
                severity = AlertSeverity.INFO
                
            elif event.event_type == "sell":
                title = f"🔴 매도 완료 - {event.market}"
                if event.profit_loss and event.profit_loss > 0:
                    title = f"💰 수익 매도 - {event.market}"
                    message = f"{event.market}을 {event.amount:,.0f}원에 매도했습니다 (수익: +{event.profit_loss:,.0f}원)"
                    severity = AlertSeverity.INFO
                elif event.profit_loss and event.profit_loss < 0:
                    title = f"📉 손절 매도 - {event.market}"
                    message = f"{event.market}을 {event.amount:,.0f}원에 손절했습니다 (손실: {event.profit_loss:,.0f}원)"
                    severity = AlertSeverity.WARNING
                else:
                    message = f"{event.market}을 {event.amount:,.0f}원에 매도했습니다"
                    severity = AlertSeverity.INFO
                    
            elif event.event_type == "position_opened":
                title = f"📈 포지션 오픈 - {event.market}"
                message = f"새로운 포지션이 열렸습니다: {event.market} ({event.amount:,.0f}원)"
                severity = AlertSeverity.INFO
                
            elif event.event_type == "position_closed":
                if event.profit_loss and event.profit_loss > 0:
                    title = f"✅ 수익 포지션 종료 - {event.market}"
                    message = f"포지션이 수익으로 종료되었습니다: {event.market} (+{event.profit_loss:,.0f}원)"
                    severity = AlertSeverity.INFO
                elif event.profit_loss and event.profit_loss < 0:
                    title = f"⚠️ 손실 포지션 종료 - {event.market}"
                    message = f"포지션이 손실로 종료되었습니다: {event.market} ({event.profit_loss:,.0f}원)"
                    severity = AlertSeverity.WARNING
                else:
                    title = f"📊 포지션 종료 - {event.market}"
                    message = f"포지션이 종료되었습니다: {event.market}"
                    severity = AlertSeverity.INFO
                    
            elif event.event_type == "profit_target":
                title = f"🎯 목표 수익 달성 - {event.market}"
                message = f"목표 수익에 도달했습니다: {event.market} (+{event.profit_loss:,.0f}원)"
                severity = AlertSeverity.INFO
                
            elif event.event_type == "stop_loss":
                title = f"🛑 손절매 실행 - {event.market}"
                message = f"손절매가 실행되었습니다: {event.market} ({event.profit_loss:,.0f}원)"
                severity = AlertSeverity.WARNING
                
            else:
                title = f"📊 거래 이벤트 - {event.market}"
                message = f"거래 이벤트가 발생했습니다: {event.event_type}"
                severity = AlertSeverity.INFO
            
            return title, message, severity
            
        except Exception as e:
            logger.error(f"❌ 거래 메시지 생성 오류: {str(e)}")
            return "거래 알림", "거래 이벤트가 발생했습니다", AlertSeverity.INFO
    
    async def notify_daily_summary(self):
        """일일 거래 요약 알림"""
        try:
            from .trading_engine import trading_state
            
            # 일일 통계 수집
            total_trades = trading_state.daily_trades
            total_loss = trading_state.daily_loss
            active_positions = len(trading_state.positions)
            available_budget = trading_state.available_budget
            
            if total_trades == 0:
                return  # 거래가 없으면 알림 안함
            
            # 수익/손실 계산 (음수 손실을 양수 수익으로 변환)
            daily_profit = -total_loss
            profit_emoji = "💰" if daily_profit > 0 else "📉" if daily_profit < 0 else "➖"
            
            title = f"📊 일일 거래 요약 ({datetime.now().strftime('%m/%d')})"
            message = f"""
📈 총 거래 횟수: {total_trades}회
{profit_emoji} 일일 손익: {daily_profit:+,.0f}원
📋 활성 포지션: {active_positions}개
💰 가용 예산: {available_budget:,.0f}원
            """.strip()
            
            severity = AlertSeverity.INFO
            if daily_profit < -10000:  # 1만원 이상 손실
                severity = AlertSeverity.WARNING
            elif daily_profit < -30000:  # 3만원 이상 손실
                severity = AlertSeverity.ERROR
            
            await monitoring_service.send_alert(
                title=title,
                message=message,
                severity=severity,
                service="trading_summary",
                tags={
                    "type": "daily_summary",
                    "trades": str(total_trades),
                    "profit": str(daily_profit)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 일일 요약 알림 오류: {str(e)}")
    
    async def notify_system_start(self):
        """시스템 시작 알림"""
        try:
            await monitoring_service.send_alert(
                title="🚀 거래 시스템 시작",
                message="업비트 자동거래 시스템이 시작되었습니다",
                severity=AlertSeverity.INFO,
                service="system"
            )
            
        except Exception as e:
            logger.error(f"❌ 시스템 시작 알림 오류: {str(e)}")
    
    # 실시간 알림 및 디바이스 관리 기능 추가
    
    async def register_device(self, user_id: str, device_token: str, platform: str, settings: Dict[str, Any]):
        """디바이스 등록"""
        try:
            device_info = {
                "device_token": device_token,
                "platform": platform,
                "registered_at": datetime.now(),
                "last_active": datetime.now(),
                "enabled": True,
            }
            
            self.registered_devices[user_id] = device_info
            self.user_settings[user_id] = {**settings, "updated_at": datetime.now()}
            
            if user_id not in self.notification_history:
                self.notification_history[user_id] = []
            
            logger.info(f"📱 디바이스 등록 완료: {user_id} ({platform})")
            
        except Exception as e:
            logger.error(f"❌ 디바이스 등록 실패: {str(e)}")
    
    async def update_user_settings(self, user_id: str, settings: Dict[str, Any]):
        """사용자 알림 설정 업데이트"""
        try:
            if user_id not in self.user_settings:
                self.user_settings[user_id] = {}
            
            self.user_settings[user_id].update(settings)
            self.user_settings[user_id]["updated_at"] = datetime.now()
            
            logger.info(f"⚙️ 알림 설정 업데이트: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ 알림 설정 업데이트 실패: {str(e)}")
    
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """사용자 알림 설정 조회"""
        return self.user_settings.get(user_id, {})
    
    async def send_notification(
        self, 
        user_id: str, 
        title: str, 
        message: str, 
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """개별 사용자에게 알림 전송"""
        try:
            # 사용자 설정 확인
            user_settings = await self.get_user_settings(user_id)
            device_info = self.registered_devices.get(user_id)
            
            if not device_info or not device_info.get("enabled"):
                logger.debug(f"📵 비활성 디바이스: {user_id}")
                return False
            
            # 알림 유형별 설정 확인
            if not self._should_send_notification(notification_type, user_settings):
                logger.debug(f"🔕 알림 비활성화: {user_id} - {notification_type}")
                return False
            
            # 알림 객체 생성
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notification_type,
                "data": data or {},
                "created_at": datetime.now(),
                "sent": False,
                "device_token": device_info["device_token"],
                "platform": device_info["platform"],
            }
            
            # 알림 히스토리에 추가
            if user_id not in self.notification_history:
                self.notification_history[user_id] = []
            
            self.notification_history[user_id].append(notification)
            
            # 히스토리 크기 제한 (최근 100개)
            if len(self.notification_history[user_id]) > 100:
                self.notification_history[user_id] = self.notification_history[user_id][-100:]
            
            # 알림 큐에 추가 (배치 처리)
            await self.notification_queue.put(notification)
            
            # 배치 처리 태스크 시작
            if not self._batch_task or self._batch_task.done():
                self._batch_task = asyncio.create_task(self._process_notification_batch())
            
            logger.info(f"📤 알림 큐 추가: {user_id} - {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 알림 전송 실패: {str(e)}")
            return False
    
    async def broadcast_notification(
        self, 
        title: str, 
        message: str, 
        notification_type: str = "broadcast",
        data: Optional[Dict[str, Any]] = None,
        filter_func: Optional[Callable] = None
    ):
        """모든 등록된 사용자에게 브로드캐스트 알림"""
        try:
            sent_count = 0
            
            for user_id in self.registered_devices.keys():
                # 필터 함수 적용
                if filter_func and not filter_func(user_id):
                    continue
                
                success = await self.send_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    data=data
                )
                
                if success:
                    sent_count += 1
            
            logger.info(f"📢 브로드캐스트 알림 전송 완료: {sent_count}명")
            return sent_count
            
        except Exception as e:
            logger.error(f"❌ 브로드캐스트 알림 실패: {str(e)}")
            return 0
    
    async def get_notification_history(
        self, 
        user_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """사용자 알림 히스토리 조회"""
        try:
            notifications = self.notification_history.get(user_id, [])
            
            # 날짜 필터링
            if start_date or end_date:
                filtered_notifications = []
                for notif in notifications:
                    notif_date = notif["created_at"]
                    if start_date and notif_date < start_date:
                        continue
                    if end_date and notif_date > end_date:
                        continue
                    filtered_notifications.append(notif)
                notifications = filtered_notifications
            
            # 최신순 정렬
            notifications.sort(key=lambda x: x["created_at"], reverse=True)
            
            # 제한 적용
            notifications = notifications[:limit]
            
            # 직렬화 가능한 형태로 변환
            serialized_notifications = []
            for notif in notifications:
                serialized_notif = {**notif}
                serialized_notif["created_at"] = notif["created_at"].isoformat()
                serialized_notifications.append(serialized_notif)
            
            return serialized_notifications
            
        except Exception as e:
            logger.error(f"❌ 알림 히스토리 조회 실패: {str(e)}")
            return []
    
    def _should_send_notification(self, notification_type: str, user_settings: Dict[str, Any]) -> bool:
        """알림 전송 여부 결정"""
        try:
            # 기본적으로 모든 알림 허용
            if not user_settings:
                return True
            
            # 알림 유형별 설정 확인
            type_mapping = {
                "trade_signal": "trade_signals",
                "position_alert": "position_alerts", 
                "profit_alert": "profit_loss_alerts",
                "loss_alert": "profit_loss_alerts",
                "system_alert": "system_alerts",
                "emergency": "emergency_alerts",
                "test": True,  # 테스트 알림은 항상 허용
                "broadcast": "system_alerts",
            }
            
            setting_key = type_mapping.get(notification_type, True)
            
            if isinstance(setting_key, bool):
                return setting_key
            
            return user_settings.get(setting_key, True)
            
        except Exception as e:
            logger.error(f"❌ 알림 설정 확인 실패: {str(e)}")
            return True  # 오류시 기본으로 허용
    
    async def _process_notification_batch(self):
        """알림 배치 처리"""
        try:
            batch_notifications = []
            batch_timeout = 5  # 5초 배치 처리
            
            while True:
                try:
                    # 5초 타임아웃으로 알림 수집
                    notification = await asyncio.wait_for(
                        self.notification_queue.get(),
                        timeout=batch_timeout
                    )
                    batch_notifications.append(notification)
                    
                    # 큐에서 추가 알림들 즉시 수집 (논블록킹)
                    while not self.notification_queue.empty() and len(batch_notifications) < 10:
                        try:
                            extra_notif = self.notification_queue.get_nowait()
                            batch_notifications.append(extra_notif)
                        except asyncio.QueueEmpty:
                            break
                    
                    # 배치 처리 실행
                    if batch_notifications:
                        await self._send_batch_notifications(batch_notifications)
                        batch_notifications = []
                        
                except asyncio.TimeoutError:
                    # 타임아웃 - 배치가 있다면 처리
                    if batch_notifications:
                        await self._send_batch_notifications(batch_notifications)
                        batch_notifications = []
                    
                    # 큐가 비어있으면 종료
                    if self.notification_queue.empty():
                        break
                        
        except Exception as e:
            logger.error(f"❌ 배치 처리 실패: {str(e)}")
    
    async def _send_batch_notifications(self, notifications: List[Dict[str, Any]]):
        """실제 알림 전송 (배치)"""
        try:
            # 플랫폼별로 그룹핑
            android_notifications = []
            ios_notifications = []
            
            for notif in notifications:
                if notif["platform"] == "android":
                    android_notifications.append(notif)
                elif notif["platform"] == "ios":
                    ios_notifications.append(notif)
            
            # Firebase Cloud Messaging (FCM) 전송
            if android_notifications:
                await self._send_fcm_notifications(android_notifications)
            
            # Apple Push Notification (APNs) 전송
            if ios_notifications:
                await self._send_apns_notifications(ios_notifications)
            
            logger.info(f"📤 배치 알림 전송 완료: {len(notifications)}개")
            
        except Exception as e:
            logger.error(f"❌ 배치 알림 전송 실패: {str(e)}")
    
    async def _send_fcm_notifications(self, notifications: List[Dict[str, Any]]):
        """Firebase Cloud Messaging 전송"""
        try:
            # 실제 구현에서는 firebase-admin SDK 사용
            # 여기서는 로깅으로 대체
            for notif in notifications:
                logger.info(f"🤖 FCM 전송: {notif['title']} -> {notif['device_token'][:10]}...")
                # 실제 FCM 전송 로직
                notif["sent"] = True
                
        except Exception as e:
            logger.error(f"❌ FCM 전송 실패: {str(e)}")
    
    async def _send_apns_notifications(self, notifications: List[Dict[str, Any]]):
        """Apple Push Notification 전송"""
        try:
            # 실제 구현에서는 aioapns 라이브러리 사용
            # 여기서는 로깅으로 대체
            for notif in notifications:
                logger.info(f"🍎 APNs 전송: {notif['title']} -> {notif['device_token'][:10]}...")
                # 실제 APNs 전송 로직
                notif["sent"] = True
                
        except Exception in e:
            logger.error(f"❌ APNs 전송 실패: {str(e)}")

    async def notify_system_stop(self):
        """시스템 종료 알림"""
        try:
            await monitoring_service.send_alert(
                title="🛑 거래 시스템 종료",
                message="업비트 자동거래 시스템이 종료되었습니다",
                severity=AlertSeverity.WARNING,
                service="system"
            )
            
        except Exception as e:
            logger.error(f"❌ 시스템 종료 알림 오류: {str(e)}")
    
    async def notify_emergency_stop(self, reason: str = "수동 정지"):
        """비상 정지 알림"""
        try:
            await monitoring_service.send_alert(
                title="🚨 비상 정지",
                message=f"거래 시스템이 비상 정지되었습니다. 사유: {reason}",
                severity=AlertSeverity.CRITICAL,
                service="emergency"
            )
            
        except Exception as e:
            logger.error(f"❌ 비상 정지 알림 오류: {str(e)}")
    
    async def notify_api_error(self, error_message: str, retry_count: int = 0):
        """API 오류 알림"""
        try:
            severity = AlertSeverity.WARNING
            if retry_count >= 3:
                severity = AlertSeverity.ERROR
            if retry_count >= 5:
                severity = AlertSeverity.CRITICAL
            
            await monitoring_service.send_alert(
                title=f"🔌 API 연결 오류",
                message=f"업비트 API 오류가 발생했습니다 (시도 {retry_count + 1}회): {error_message}",
                severity=severity,
                service="upbit_api",
                tags={
                    "error_type": "api_error",
                    "retry_count": str(retry_count)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ API 오류 알림 실패: {str(e)}")
    
    async def notify_position_risk(self, market: str, risk_level: str, current_loss: float):
        """포지션 리스크 알림"""
        try:
            if abs(current_loss) < self.min_loss_notification:
                return
            
            severity_map = {
                "low": AlertSeverity.INFO,
                "medium": AlertSeverity.WARNING,
                "high": AlertSeverity.ERROR,
                "critical": AlertSeverity.CRITICAL
            }
            
            severity = severity_map.get(risk_level, AlertSeverity.WARNING)
            risk_emoji = {
                "low": "🟢",
                "medium": "🟡", 
                "high": "🟠",
                "critical": "🔴"
            }
            
            emoji = risk_emoji.get(risk_level, "⚠️")
            
            await monitoring_service.send_alert(
                title=f"{emoji} 포지션 리스크 알림 - {market}",
                message=f"{market} 포지션이 {risk_level} 리스크 상태입니다. 현재 손실: {current_loss:,.0f}원",
                severity=severity,
                service="risk_management",
                tags={
                    "market": market,
                    "risk_level": risk_level,
                    "loss_amount": str(current_loss)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 포지션 리스크 알림 오류: {str(e)}")
    
    def configure_notifications(self, config: Dict[str, Any]):
        """알림 설정 업데이트"""
        try:
            self.notify_on_trade = config.get("notify_on_trade", self.notify_on_trade)
            self.notify_on_profit = config.get("notify_on_profit", self.notify_on_profit)
            self.notify_on_loss = config.get("notify_on_loss", self.notify_on_loss)
            self.notify_on_system_alerts = config.get("notify_on_system_alerts", self.notify_on_system_alerts)
            
            self.min_notification_amount = config.get("min_notification_amount", self.min_notification_amount)
            self.min_profit_notification = config.get("min_profit_notification", self.min_profit_notification)
            self.min_loss_notification = config.get("min_loss_notification", self.min_loss_notification)
            
            logger.info("⚙️ 알림 설정이 업데이트되었습니다")
            
        except Exception as e:
            logger.error(f"❌ 알림 설정 업데이트 오류: {str(e)}")
    
    def get_notification_config(self) -> Dict[str, Any]:
        """현재 알림 설정 조회"""
        return {
            "notify_on_trade": self.notify_on_trade,
            "notify_on_profit": self.notify_on_profit,
            "notify_on_loss": self.notify_on_loss,
            "notify_on_system_alerts": self.notify_on_system_alerts,
            "min_notification_amount": self.min_notification_amount,
            "min_profit_notification": self.min_profit_notification,
            "min_loss_notification": self.min_loss_notification
        }

# 전역 알림 서비스 인스턴스
notification_service = NotificationService()