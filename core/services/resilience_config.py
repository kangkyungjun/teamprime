"""
시스템 복원력 설정 관리
건강 점검 및 서킷 브레이커 자동 설정
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime
import aiohttp
import time

from .resilience_service import resilience_service
from ..utils.api_manager import api_manager

logger = logging.getLogger(__name__)

class ResilienceConfigurator:
    """복원력 서비스 설정 관리자"""
    
    def __init__(self):
        self.configured = False
        self.upbit_client = None
        
    async def initialize_resilience_system(self, upbit_client=None):
        """복원력 시스템 초기화"""
        if self.configured:
            return
            
        try:
            self.upbit_client = upbit_client
            
            # 1. 서킷 브레이커 등록
            await self._setup_circuit_breakers()
            
            # 2. 건강 점검 등록
            await self._setup_health_checks()
            
            # 3. 알림 콜백 등록
            await self._setup_alert_callbacks()
            
            # 4. 모니터링 시작
            asyncio.create_task(resilience_service.start_health_monitoring())
            
            self.configured = True
            logger.info("✅ 복원력 시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 복원력 시스템 초기화 실패: {str(e)}")
            
    async def _setup_circuit_breakers(self):
        """서킷 브레이커 설정"""
        try:
            # 업비트 API 서킷 브레이커
            resilience_service.register_circuit_breaker(
                service_name="upbit_api",
                failure_threshold=5,    # 5회 연속 실패시 차단
                recovery_timeout=60,    # 60초 후 복구 시도
                success_threshold=3     # 3회 성공시 완전 복구
            )
            
            # 거래 엔진 서킷 브레이커
            resilience_service.register_circuit_breaker(
                service_name="trading_engine",
                failure_threshold=3,    # 3회 연속 실패시 차단
                recovery_timeout=120,   # 2분 후 복구 시도
                success_threshold=2     # 2회 성공시 완전 복구
            )
            
            # 신호 분석기 서킷 브레이커
            resilience_service.register_circuit_breaker(
                service_name="signal_analyzer",
                failure_threshold=5,    # 5회 연속 실패시 차단
                recovery_timeout=60,    # 60초 후 복구 시도
                success_threshold=3     # 3회 성공시 완전 복구
            )
            
            # 거래 검증 서비스 서킷 브레이커
            resilience_service.register_circuit_breaker(
                service_name="trade_verifier",
                failure_threshold=3,    # 3회 연속 실패시 차단
                recovery_timeout=90,    # 90초 후 복구 시도
                success_threshold=2     # 2회 성공시 완전 복구
            )
            
            logger.info("🔧 서킷 브레이커 설정 완료")
            
        except Exception as e:
            logger.error(f"❌ 서킷 브레이커 설정 실패: {str(e)}")
    
    async def _setup_health_checks(self):
        """건강 점검 설정"""
        try:
            # 업비트 API 건강 점검
            resilience_service.register_health_check(
                service_name="upbit_api",
                check_function=self._check_upbit_api_health,
                check_interval=30,      # 30초마다 점검
                timeout=10             # 10초 타임아웃
            )
            
            # 데이터베이스 건강 점검
            resilience_service.register_health_check(
                service_name="database",
                check_function=self._check_database_health,
                check_interval=60,      # 60초마다 점검
                timeout=5              # 5초 타임아웃
            )
            
            # 거래 엔진 건강 점검
            resilience_service.register_health_check(
                service_name="trading_engine",
                check_function=self._check_trading_engine_health,
                check_interval=30,      # 30초마다 점검
                timeout=5              # 5초 타임아웃
            )
            
            # 신호 분석기 건강 점검
            resilience_service.register_health_check(
                service_name="signal_analyzer",
                check_function=self._check_signal_analyzer_health,
                check_interval=60,      # 60초마다 점검
                timeout=10             # 10초 타임아웃
            )
            
            logger.info("🏥 건강 점검 설정 완료")
            
        except Exception as e:
            logger.error(f"❌ 건강 점검 설정 실패: {str(e)}")
    
    async def _check_upbit_api_health(self) -> bool:
        """업비트 API 건강 점검"""
        try:
            if not self.upbit_client:
                # Public API로 서버 시간 확인
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.upbit.com/v1/market/all") as response:
                        if response.status == 200:
                            data = await response.json()
                            return len(data) > 0
                        return False
            else:
                # 인증된 API로 계좌 정보 확인
                account_info = await self.upbit_client.get_accounts()
                return account_info is not None
                
        except Exception as e:
            logger.debug(f"업비트 API 건강 점검 실패: {str(e)}")
            return False
    
    async def _check_database_health(self) -> bool:
        """데이터베이스 건강 점검"""
        try:
            # SQLite 데이터베이스 연결 테스트 (기본 경로)
            import aiosqlite
            
            db_path = "upbit_candles.db"  # 기본 데이터베이스 파일
            
            async with aiosqlite.connect(db_path) as conn:
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                return result is not None
                
        except Exception as e:
            logger.debug(f"데이터베이스 건강 점검 실패: {str(e)}")
            return False
    
    async def _check_trading_engine_health(self) -> bool:
        """거래 엔진 건강 점검"""
        try:
            # 거래 엔진 상태 확인
            from .trading_engine import trading_state
            
            # 기본 상태 확인
            if hasattr(trading_state, 'available_budget'):
                return True
            return False
            
        except Exception as e:
            logger.debug(f"거래 엔진 건강 점검 실패: {str(e)}")
            return False
    
    async def _check_signal_analyzer_health(self) -> bool:
        """신호 분석기 건강 점검"""
        try:
            # 신호 분석기의 기본 기능 테스트
            from .signal_analyzer import signal_analyzer
            
            # 테스트 코인으로 신호 분석 시도 (KRW-BTC)
            test_result = await signal_analyzer.analyze_buy_conditions_realtime("KRW-BTC")
            return test_result is not None
            
        except Exception as e:
            logger.debug(f"신호 분석기 건강 점검 실패: {str(e)}")
            return False
    
    async def _setup_alert_callbacks(self):
        """알림 콜백 설정"""
        try:
            # 로그 기반 알림 콜백
            async def log_alert(title: str, message: str):
                logger.warning(f"🚨 시스템 알림: {title} - {message}")
                
                # 추가적으로 별도 알림 파일에 기록
                try:
                    with open("system_alerts.log", "a", encoding="utf-8") as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"[{timestamp}] {title}: {message}\n")
                except Exception:
                    pass
            
            resilience_service.add_alert_callback(log_alert)
            
            logger.info("📢 알림 콜백 설정 완료")
            
        except Exception as e:
            logger.error(f"❌ 알림 콜백 설정 실패: {str(e)}")
    
    async def test_resilience_components(self):
        """복원력 구성 요소 테스트"""
        try:
            logger.info("🧪 복원력 구성 요소 테스트 시작")
            
            # 각 건강 점검 한번씩 실행
            for name, health_check in resilience_service.health_checks.items():
                try:
                    start_time = time.time()
                    result = await asyncio.wait_for(
                        health_check.check_function(),
                        timeout=health_check.timeout
                    )
                    duration = time.time() - start_time
                    
                    status = "✅ 성공" if result else "❌ 실패"
                    logger.info(f"   {name}: {status} ({duration:.2f}s)")
                    
                except Exception as e:
                    logger.warning(f"   {name}: ❌ 오류 - {str(e)}")
            
            logger.info("🧪 복원력 구성 요소 테스트 완료")
            
        except Exception as e:
            logger.error(f"❌ 복원력 테스트 실패: {str(e)}")
    
    def get_configuration_status(self) -> dict:
        """설정 상태 조회"""
        try:
            return {
                "configured": self.configured,
                "circuit_breakers_count": len(resilience_service.circuit_breakers),
                "health_checks_count": len(resilience_service.health_checks),
                "monitoring_active": resilience_service.monitoring_active,
                "system_status": resilience_service.system_status.value,
                "alert_callbacks_count": len(resilience_service.alert_callbacks)
            }
        except Exception as e:
            return {"error": str(e)}

# 전역 복원력 설정 관리자
resilience_configurator = ResilienceConfigurator()