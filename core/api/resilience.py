"""시스템 복원력 API 엔드포인트"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any, Optional

from ..services.resilience_service import resilience_service, HealthStatus
from ..auth.middleware import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resilience"])

@router.get("/system-health")
async def get_system_health(current_user: Dict[str, Any] = Depends(require_auth)):
    """시스템 전체 건강 상태 조회"""
    try:
        health_report = resilience_service.get_system_health_report()
        
        return {
            "success": True,
            "system_health": health_report,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 시스템 건강 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/circuit-breakers")
async def get_circuit_breakers(current_user: Dict[str, Any] = Depends(require_auth)):
    """서킷 브레이커 상태 조회"""
    try:
        circuit_status = {}
        
        for name, circuit in resilience_service.circuit_breakers.items():
            circuit_status[name] = {
                "service_name": circuit.service_name,
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "success_count": circuit.success_count,
                "failure_threshold": circuit.failure_threshold,
                "recovery_timeout": circuit.recovery_timeout,
                "success_threshold": circuit.success_threshold,
                "last_failure_time": circuit.last_failure_time.isoformat() if circuit.last_failure_time else None,
                "next_attempt_time": circuit.next_attempt_time.isoformat() if circuit.next_attempt_time else None
            }
        
        return {
            "success": True,
            "circuit_breakers": circuit_status,
            "total_circuits": len(circuit_status),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 서킷 브레이커 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/health-checks")
async def get_health_checks(current_user: Dict[str, Any] = Depends(require_auth)):
    """건강 점검 상태 조회"""
    try:
        health_status = {}
        
        for name, health_check in resilience_service.health_checks.items():
            health_status[name] = {
                "service_name": health_check.service_name,
                "status": health_check.status.value,
                "check_interval": health_check.check_interval,
                "timeout": health_check.timeout,
                "last_check": health_check.last_check.isoformat() if health_check.last_check else None,
                "last_success": health_check.last_success.isoformat() if health_check.last_success else None,
                "consecutive_failures": health_check.consecutive_failures,
                "response_time": health_check.response_time
            }
        
        return {
            "success": True,
            "health_checks": health_status,
            "monitoring_active": resilience_service.monitoring_active,
            "system_status": resilience_service.system_status.value,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 건강 점검 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/failure-statistics")
async def get_failure_statistics(
    hours: int = 24,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """장애 통계 조회"""
    try:
        if hours < 1 or hours > 168:  # 1시간 ~ 1주일
            raise HTTPException(status_code=400, detail="시간 범위는 1-168시간 사이여야 합니다")
        
        statistics = resilience_service.get_failure_statistics(hours)
        
        return {
            "success": True,
            "failure_statistics": statistics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 장애 통계 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/failure-history")
async def get_failure_history(
    limit: int = 50,
    service_name: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """장애 기록 조회"""
    try:
        if limit < 1 or limit > 200:
            raise HTTPException(status_code=400, detail="제한 개수는 1-200 사이여야 합니다")
        
        failures = resilience_service.failure_history
        
        # 서비스 필터링
        if service_name:
            failures = [f for f in failures if f.service_name == service_name]
        
        # 최신 순으로 정렬하고 제한
        failures = sorted(failures, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        failure_data = []
        for failure in failures:
            failure_data.append({
                "timestamp": failure.timestamp.isoformat(),
                "service_name": failure.service_name,
                "error_type": failure.error_type,
                "error_message": failure.error_message,
                "retry_count": failure.retry_count,
                "recovered_at": failure.recovered_at.isoformat() if failure.recovered_at else None,
                "duration_seconds": failure.duration_seconds
            })
        
        return {
            "success": True,
            "failures": failure_data,
            "total_failures": len(failure_data),
            "filtered_by_service": service_name,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 장애 기록 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/start-monitoring")
async def start_monitoring(current_user: Dict[str, Any] = Depends(require_auth)):
    """건강 점검 모니터링 시작"""
    try:
        if resilience_service.monitoring_active:
            return {
                "success": False,
                "message": "건강 점검 모니터링이 이미 실행 중입니다"
            }
        
        # 백그라운드에서 모니터링 시작
        import asyncio
        asyncio.create_task(resilience_service.start_health_monitoring())
        
        logger.info("🏥 건강 점검 모니터링 시작 요청")
        
        return {
            "success": True,
            "message": "건강 점검 모니터링이 시작되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 모니터링 시작 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/stop-monitoring") 
async def stop_monitoring(current_user: Dict[str, Any] = Depends(require_auth)):
    """건강 점검 모니터링 중지"""
    try:
        await resilience_service.stop_monitoring()
        
        return {
            "success": True,
            "message": "건강 점검 모니터링이 중지되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 모니터링 중지 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/reset-circuit-breaker/{service_name}")
async def reset_circuit_breaker(
    service_name: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """서킷 브레이커 수동 리셋"""
    try:
        if service_name not in resilience_service.circuit_breakers:
            raise HTTPException(status_code=404, detail=f"서킷 브레이커를 찾을 수 없습니다: {service_name}")
        
        circuit = resilience_service.circuit_breakers[service_name]
        
        # 서킷 브레이커 리셋
        from ..services.resilience_service import CircuitState
        circuit.state = CircuitState.CLOSED
        circuit.failure_count = 0
        circuit.success_count = 0
        circuit.last_failure_time = None
        circuit.next_attempt_time = None
        
        logger.info(f"🔄 서킷 브레이커 수동 리셋: {service_name}")
        
        return {
            "success": True,
            "message": f"{service_name} 서킷 브레이커가 리셋되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 서킷 브레이커 리셋 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/system-resilience-summary")
async def get_system_resilience_summary(current_user: Dict[str, Any] = Depends(require_auth)):
    """시스템 복원력 요약 정보"""
    try:
        health_report = resilience_service.get_system_health_report()
        
        # 요약 통계 계산
        total_circuits = len(resilience_service.circuit_breakers)
        open_circuits = sum(1 for cb in resilience_service.circuit_breakers.values() 
                          if cb.state.value == "open")
        
        total_health_checks = len(resilience_service.health_checks)
        healthy_services = sum(1 for hc in resilience_service.health_checks.values()
                             if hc.status == HealthStatus.HEALTHY)
        
        recent_failures = len([f for f in resilience_service.failure_history 
                             if (datetime.now() - f.timestamp).total_seconds() < 3600])  # 1시간 이내
        
        return {
            "success": True,
            "summary": {
                "system_status": resilience_service.system_status.value,
                "monitoring_active": resilience_service.monitoring_active,
                "circuit_breakers": {
                    "total": total_circuits,
                    "open": open_circuits,
                    "closed": total_circuits - open_circuits
                },
                "health_checks": {
                    "total": total_health_checks,
                    "healthy": healthy_services,
                    "unhealthy": total_health_checks - healthy_services
                },
                "failures": {
                    "recent_1h": recent_failures,
                    "total_24h": len([f for f in resilience_service.failure_history 
                                   if (datetime.now() - f.timestamp).total_seconds() < 86400])
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 복원력 요약 정보 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/test-resilience/{service_name}")
async def test_resilience(
    service_name: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """복원력 테스트 (개발용)"""
    try:
        # 테스트용 실패 시뮬레이션
        async def test_operation():
            raise Exception(f"테스트 실패 시뮬레이션 - {service_name}")
        
        try:
            await resilience_service.retry_with_backoff(
                test_operation,
                max_attempts=2,
                service_name=service_name
            )
        except Exception:
            pass  # 테스트이므로 예외 무시
        
        return {
            "success": True,
            "message": f"{service_name}에 대한 복원력 테스트가 완료되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 복원력 테스트 오류: {str(e)}")
        return {"success": False, "error": str(e)}