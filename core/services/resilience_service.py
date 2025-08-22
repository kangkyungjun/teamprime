"""
시스템 복원력 서비스
네트워크 장애 대응, 자동 복구, 서킷 브레이커 패턴
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """시스템 건강 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    CRITICAL = "critical"
    OFFLINE = "offline"

class CircuitState(Enum):
    """서킷 브레이커 상태"""
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단 상태
    HALF_OPEN = "half_open" # 복구 시도 중

@dataclass
class FailureRecord:
    """장애 기록"""
    timestamp: datetime
    service_name: str
    error_type: str
    error_message: str
    retry_count: int = 0
    recovered_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

@dataclass
class CircuitBreaker:
    """서킷 브레이커 설정"""
    service_name: str
    failure_threshold: int = 5          # 연속 실패 임계값
    recovery_timeout: int = 60          # 복구 시도 대기시간 (초)
    success_threshold: int = 3          # 복구 확인 성공 임계값
    
    # 상태
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None

@dataclass
class HealthCheck:
    """건강 점검 설정"""
    service_name: str
    check_function: Callable
    check_interval: int = 30            # 점검 간격 (초)
    timeout: int = 10                   # 타임아웃 (초)
    
    # 상태
    status: HealthStatus = HealthStatus.HEALTHY
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    response_time: float = 0.0

class ResilienceService:
    """시스템 복원력 서비스"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_checks: Dict[str, HealthCheck] = {}
        self.failure_history: List[FailureRecord] = []
        
        # 전역 설정
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0      # 기본 재시도 지연 (초)
        self.max_retry_delay = 30.0      # 최대 재시도 지연 (초)
        self.exponential_backoff = True   # 지수 백오프 사용
        
        # 모니터링
        self.monitoring_active = False
        self.system_status: HealthStatus = HealthStatus.HEALTHY
        
        # 알림 설정
        self.alert_callbacks: List[Callable] = []
        self.critical_failure_threshold = 10  # 10개 이상 연속 실패시 중요 경고
        
        logger.info("✅ 시스템 복원력 서비스 초기화 완료")
    
    def register_circuit_breaker(
        self, 
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        """서킷 브레이커 등록"""
        try:
            circuit = CircuitBreaker(
                service_name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold
            )
            
            self.circuit_breakers[service_name] = circuit
            logger.info(f"🔧 서킷 브레이커 등록: {service_name}")
            logger.info(f"   실패 임계값: {failure_threshold}, 복구 대기: {recovery_timeout}초")
            
        except Exception as e:
            logger.error(f"❌ 서킷 브레이커 등록 실패 ({service_name}): {str(e)}")
    
    def register_health_check(
        self,
        service_name: str,
        check_function: Callable,
        check_interval: int = 30,
        timeout: int = 10
    ):
        """건강 점검 등록"""
        try:
            health_check = HealthCheck(
                service_name=service_name,
                check_function=check_function,
                check_interval=check_interval,
                timeout=timeout
            )
            
            self.health_checks[service_name] = health_check
            logger.info(f"🏥 건강 점검 등록: {service_name} (간격: {check_interval}초)")
            
        except Exception as e:
            logger.error(f"❌ 건강 점검 등록 실패 ({service_name}): {str(e)}")
    
    @asynccontextmanager
    async def circuit_protected(self, service_name: str):
        """서킷 브레이커로 보호된 실행 컨텍스트"""
        circuit = self.circuit_breakers.get(service_name)
        if not circuit:
            # 서킷 브레이커가 없으면 그냥 통과
            yield
            return
        
        # 서킷이 열려있는지 확인
        if circuit.state == CircuitState.OPEN:
            if datetime.now() < circuit.next_attempt_time:
                raise Exception(f"서킷 브레이커 OPEN - {service_name} 서비스 일시 차단됨")
            else:
                # 복구 시도 시간이 되었으므로 HALF_OPEN으로 변경
                circuit.state = CircuitState.HALF_OPEN
                circuit.success_count = 0
                logger.info(f"🔄 서킷 브레이커 복구 시도: {service_name}")
        
        try:
            yield
            # 성공시 처리
            await self._on_circuit_success(service_name)
            
        except Exception as e:
            # 실패시 처리
            await self._on_circuit_failure(service_name, e)
            raise
    
    async def _on_circuit_success(self, service_name: str):
        """서킷 브레이커 성공 처리"""
        circuit = self.circuit_breakers.get(service_name)
        if not circuit:
            return
        
        if circuit.state == CircuitState.HALF_OPEN:
            circuit.success_count += 1
            if circuit.success_count >= circuit.success_threshold:
                # 완전 복구
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                circuit.success_count = 0
                logger.info(f"✅ 서킷 브레이커 복구 완료: {service_name}")
                
                # 복구 알림
                await self._send_alert(f"🔄 서비스 복구", f"{service_name} 서비스가 정상 복구되었습니다")
        else:
            # CLOSED 상태에서는 실패 카운터만 리셋
            circuit.failure_count = 0
    
    async def _on_circuit_failure(self, service_name: str, error: Exception):
        """서킷 브레이커 실패 처리"""
        circuit = self.circuit_breakers.get(service_name)
        if not circuit:
            return
        
        circuit.failure_count += 1
        circuit.last_failure_time = datetime.now()
        
        # 장애 기록
        failure = FailureRecord(
            timestamp=datetime.now(),
            service_name=service_name,
            error_type=type(error).__name__,
            error_message=str(error)
        )
        self.failure_history.append(failure)
        
        logger.warning(f"⚠️ 서킷 브레이커 실패 ({service_name}): {circuit.failure_count}/{circuit.failure_threshold}")
        
        # 임계값 초과시 서킷 열기
        if circuit.failure_count >= circuit.failure_threshold:
            circuit.state = CircuitState.OPEN
            circuit.next_attempt_time = datetime.now() + timedelta(seconds=circuit.recovery_timeout)
            
            logger.error(f"🚨 서킷 브레이커 OPEN: {service_name}")
            logger.error(f"   다음 복구 시도: {circuit.next_attempt_time}")
            
            # 중요 경고 알림
            await self._send_alert(
                f"🚨 서킷 브레이커 차단", 
                f"{service_name} 서비스가 연속 {circuit.failure_count}회 실패하여 일시 차단되었습니다"
            )
    
    async def retry_with_backoff(
        self,
        operation: Callable,
        *args,
        max_attempts: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        service_name: Optional[str] = None,
        **kwargs
    ) -> Any:
        """지수 백오프를 사용한 재시도"""
        max_attempts = max_attempts or self.max_retry_attempts
        base_delay = base_delay or self.base_retry_delay
        max_delay = max_delay or self.max_retry_delay
        
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                # 서킷 브레이커 보호
                if service_name and service_name in self.circuit_breakers:
                    async with self.circuit_protected(service_name):
                        return await operation(*args, **kwargs)
                else:
                    return await operation(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                
                if attempt < max_attempts - 1:  # 마지막 시도가 아니면
                    # 지수 백오프 계산
                    if self.exponential_backoff:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                    else:
                        delay = base_delay
                    
                    logger.warning(f"⚠️ 재시도 {attempt + 1}/{max_attempts} ({service_name or 'unknown'})")
                    logger.warning(f"   오류: {str(e)}")
                    logger.warning(f"   {delay}초 후 재시도...")
                    
                    await asyncio.sleep(delay)
                else:
                    # 모든 시도 실패
                    logger.error(f"❌ 최대 재시도 횟수 초과 ({service_name or 'unknown'})")
                    logger.error(f"   최종 오류: {str(e)}")
        
        # 재시도 실패 기록
        if service_name:
            failure = FailureRecord(
                timestamp=datetime.now(),
                service_name=service_name,
                error_type=type(last_exception).__name__ if last_exception else "Unknown",
                error_message=str(last_exception) if last_exception else "Unknown error",
                retry_count=max_attempts
            )
            self.failure_history.append(failure)
        
        raise last_exception
    
    async def start_health_monitoring(self):
        """건강 점검 모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        logger.info("🏥 건강 점검 모니터링 시작")
        
        # 각 건강 점검에 대해 별도 태스크 실행
        tasks = []
        for service_name, health_check in self.health_checks.items():
            task = asyncio.create_task(self._run_health_check_loop(health_check))
            tasks.append(task)
        
        # 전체 시스템 상태 모니터링
        system_task = asyncio.create_task(self._run_system_monitoring())
        tasks.append(system_task)
        
        # 모든 태스크 실행
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_health_check_loop(self, health_check: HealthCheck):
        """개별 건강 점검 루프"""
        while self.monitoring_active:
            try:
                await self._perform_health_check(health_check)
                await asyncio.sleep(health_check.check_interval)
                
            except Exception as e:
                logger.error(f"❌ 건강 점검 루프 오류 ({health_check.service_name}): {str(e)}")
                await asyncio.sleep(health_check.check_interval)
    
    async def _perform_health_check(self, health_check: HealthCheck):
        """개별 건강 점검 실행"""
        start_time = time.time()
        
        try:
            # 타임아웃 적용
            result = await asyncio.wait_for(
                health_check.check_function(),
                timeout=health_check.timeout
            )
            
            # 성공 처리
            health_check.response_time = time.time() - start_time
            health_check.last_check = datetime.now()
            health_check.last_success = datetime.now()
            health_check.consecutive_failures = 0
            
            # 상태 업데이트
            if health_check.response_time > 5.0:  # 5초 이상 응답시 성능 저하
                health_check.status = HealthStatus.DEGRADED
            else:
                health_check.status = HealthStatus.HEALTHY
                
            logger.debug(f"✅ 건강 점검 성공: {health_check.service_name} ({health_check.response_time:.2f}s)")
            
        except asyncio.TimeoutError:
            await self._handle_health_check_failure(health_check, "응답 시간 초과", start_time)
        except Exception as e:
            await self._handle_health_check_failure(health_check, str(e), start_time)
    
    async def _handle_health_check_failure(self, health_check: HealthCheck, error_msg: str, start_time: float):
        """건강 점검 실패 처리"""
        health_check.response_time = time.time() - start_time
        health_check.last_check = datetime.now()
        health_check.consecutive_failures += 1
        
        # 상태 결정
        if health_check.consecutive_failures >= 5:
            health_check.status = HealthStatus.OFFLINE
        elif health_check.consecutive_failures >= 3:
            health_check.status = HealthStatus.CRITICAL
        else:
            health_check.status = HealthStatus.DEGRADED
        
        logger.warning(f"⚠️ 건강 점검 실패: {health_check.service_name}")
        logger.warning(f"   연속 실패: {health_check.consecutive_failures}회")
        logger.warning(f"   오류: {error_msg}")
        
        # 중요 상태 변경시 알림
        if health_check.status in [HealthStatus.CRITICAL, HealthStatus.OFFLINE]:
            await self._send_alert(
                f"🚨 서비스 상태 위험",
                f"{health_check.service_name} 서비스가 {health_check.status.value} 상태입니다"
            )
    
    async def _run_system_monitoring(self):
        """전체 시스템 상태 모니터링"""
        while self.monitoring_active:
            try:
                await self._update_system_status()
                await asyncio.sleep(10)  # 10초마다 전체 시스템 상태 확인
                
            except Exception as e:
                logger.error(f"❌ 시스템 모니터링 오류: {str(e)}")
                await asyncio.sleep(10)
    
    async def _update_system_status(self):
        """전체 시스템 상태 업데이트"""
        if not self.health_checks:
            self.system_status = HealthStatus.HEALTHY
            return
        
        # 모든 건강 점검 상태 분석
        offline_count = sum(1 for hc in self.health_checks.values() if hc.status == HealthStatus.OFFLINE)
        critical_count = sum(1 for hc in self.health_checks.values() if hc.status == HealthStatus.CRITICAL)
        degraded_count = sum(1 for hc in self.health_checks.values() if hc.status == HealthStatus.DEGRADED)
        
        total_services = len(self.health_checks)
        
        # 전체 시스템 상태 결정
        if offline_count > 0:
            self.system_status = HealthStatus.OFFLINE
        elif critical_count > 0 or (critical_count + offline_count) > total_services * 0.3:
            self.system_status = HealthStatus.CRITICAL
        elif degraded_count > 0 or (degraded_count + critical_count) > total_services * 0.5:
            self.system_status = HealthStatus.DEGRADED
        else:
            self.system_status = HealthStatus.HEALTHY
    
    def add_alert_callback(self, callback: Callable[[str, str], None]):
        """알림 콜백 추가"""
        self.alert_callbacks.append(callback)
        logger.info("📢 알림 콜백 등록 완료")
    
    async def _send_alert(self, title: str, message: str):
        """알림 전송"""
        try:
            for callback in self.alert_callbacks:
                try:
                    await callback(title, message)
                except Exception as e:
                    logger.error(f"❌ 알림 콜백 실행 오류: {str(e)}")
            
            logger.warning(f"📢 알림: {title} - {message}")
            
        except Exception as e:
            logger.error(f"❌ 알림 전송 오류: {str(e)}")
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """시스템 건강 상태 보고서"""
        try:
            # 건강 점검 상태
            health_summary = {}
            for name, hc in self.health_checks.items():
                health_summary[name] = {
                    "status": hc.status.value,
                    "last_check": hc.last_check.isoformat() if hc.last_check else None,
                    "last_success": hc.last_success.isoformat() if hc.last_success else None,
                    "consecutive_failures": hc.consecutive_failures,
                    "response_time": hc.response_time
                }
            
            # 서킷 브레이커 상태
            circuit_summary = {}
            for name, cb in self.circuit_breakers.items():
                circuit_summary[name] = {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
                    "next_attempt": cb.next_attempt_time.isoformat() if cb.next_attempt_time else None
                }
            
            # 최근 장애 기록
            recent_failures = []
            cutoff_time = datetime.now() - timedelta(hours=24)  # 24시간 이내
            for failure in self.failure_history:
                if failure.timestamp >= cutoff_time:
                    recent_failures.append({
                        "timestamp": failure.timestamp.isoformat(),
                        "service": failure.service_name,
                        "error_type": failure.error_type,
                        "error_message": failure.error_message,
                        "retry_count": failure.retry_count
                    })
            
            return {
                "system_status": self.system_status.value,
                "monitoring_active": self.monitoring_active,
                "health_checks": health_summary,
                "circuit_breakers": circuit_summary,
                "recent_failures": recent_failures[-20:],  # 최근 20개만
                "total_services": len(self.health_checks),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 건강 상태 보고서 생성 오류: {str(e)}")
            return {"error": str(e)}
    
    def get_failure_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """장애 통계 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_failures = [f for f in self.failure_history if f.timestamp >= cutoff_time]
            
            # 서비스별 장애 통계
            service_stats = {}
            for failure in recent_failures:
                if failure.service_name not in service_stats:
                    service_stats[failure.service_name] = {
                        "failure_count": 0,
                        "error_types": {},
                        "total_retry_attempts": 0
                    }
                
                stats = service_stats[failure.service_name]
                stats["failure_count"] += 1
                stats["total_retry_attempts"] += failure.retry_count
                
                if failure.error_type not in stats["error_types"]:
                    stats["error_types"][failure.error_type] = 0
                stats["error_types"][failure.error_type] += 1
            
            return {
                "period_hours": hours,
                "total_failures": len(recent_failures),
                "service_statistics": service_stats,
                "most_common_errors": self._get_most_common_errors(recent_failures),
                "failure_trend": self._get_failure_trend(recent_failures)
            }
            
        except Exception as e:
            logger.error(f"❌ 장애 통계 조회 오류: {str(e)}")
            return {"error": str(e)}
    
    def _get_most_common_errors(self, failures: List[FailureRecord]) -> List[Dict[str, Any]]:
        """가장 흔한 오류 유형 분석"""
        error_counts = {}
        for failure in failures:
            key = f"{failure.error_type}: {failure.error_message[:50]}"
            error_counts[key] = error_counts.get(key, 0) + 1
        
        # 빈도순 정렬
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"error": error, "count": count} for error, count in sorted_errors[:10]]
    
    def _get_failure_trend(self, failures: List[FailureRecord]) -> List[Dict[str, Any]]:
        """장애 추세 분석 (시간대별)"""
        hourly_counts = {}
        for failure in failures:
            hour = failure.timestamp.strftime("%H:00")
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        return [{"hour": hour, "failures": count} for hour, count in sorted(hourly_counts.items())]
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        logger.info("🛑 건강 점검 모니터링 중지")

# 전역 복원력 서비스 인스턴스
resilience_service = ResilienceService()