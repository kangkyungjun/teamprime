"""모니터링 및 알림 API 엔드포인트"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from ..services.monitoring_service import monitoring_service, AlertSeverity, MetricType
from ..services.notification_service import notification_service, TradingEvent
from ..auth.middleware import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])

# 요청 모델 정의
class AlertRequest(BaseModel):
    title: str
    message: str
    severity: str = "info"
    service: str = "system"
    tags: Optional[Dict[str, str]] = None

class MetricRequest(BaseModel):
    name: str
    value: float
    metric_type: str = "gauge"
    tags: Optional[Dict[str, str]] = None
    unit: str = ""

class ThresholdUpdateRequest(BaseModel):
    thresholds: Dict[str, float]

class NotificationConfigRequest(BaseModel):
    notify_on_trade: Optional[bool] = None
    notify_on_profit: Optional[bool] = None
    notify_on_loss: Optional[bool] = None
    notify_on_system_alerts: Optional[bool] = None
    min_notification_amount: Optional[float] = None
    min_profit_notification: Optional[float] = None
    min_loss_notification: Optional[float] = None

@router.get("/performance-summary")
async def get_performance_summary(
    hours: int = 24,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """성능 요약 정보 조회"""
    try:
        if hours < 1 or hours > 168:  # 1시간 ~ 1주일
            raise HTTPException(status_code=400, detail="시간 범위는 1-168시간 사이여야 합니다")
        
        performance_data = monitoring_service.get_performance_summary(hours)
        
        return {
            "success": True,
            "performance": performance_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 성능 요약 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/current-performance")
async def get_current_performance(current_user: Dict[str, Any] = Depends(require_auth)):
    """현재 성능 스냅샷 조회"""
    try:
        snapshot = await monitoring_service.collect_system_performance()
        
        return {
            "success": True,
            "snapshot": {
                "timestamp": snapshot.timestamp.isoformat(),
                "cpu_percent": snapshot.cpu_percent,
                "memory_percent": snapshot.memory_percent,
                "memory_mb": round(snapshot.memory_mb, 1),
                "disk_percent": snapshot.disk_percent,
                "network_sent": snapshot.network_sent,
                "network_recv": snapshot.network_recv,
                "active_positions": snapshot.active_positions,
                "daily_trades": snapshot.daily_trades,
                "daily_profit": snapshot.daily_profit,
                "api_response_time": snapshot.api_response_time,
                "uptime_hours": round(snapshot.uptime_seconds / 3600, 2),
                "error_rate": snapshot.error_rate
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 현재 성능 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/alerts-summary")
async def get_alerts_summary(
    hours: int = 24,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 요약 정보 조회"""
    try:
        if hours < 1 or hours > 168:  # 1시간 ~ 1주일
            raise HTTPException(status_code=400, detail="시간 범위는 1-168시간 사이여야 합니다")
        
        alert_data = monitoring_service.get_alert_summary(hours)
        
        return {
            "success": True,
            "alerts": alert_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 요약 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 목록 조회"""
    try:
        if limit < 1 or limit > 200:
            raise HTTPException(status_code=400, detail="제한 개수는 1-200 사이여야 합니다")
        
        alerts = list(monitoring_service.alerts.values())
        
        # 필터링
        if severity:
            alerts = [alert for alert in alerts if alert.severity.value == severity]
        if service:
            alerts = [alert for alert in alerts if alert.service == service]
        
        # 최신순 정렬 및 제한
        alerts = sorted(alerts, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                "id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "service": alert.service,
                "timestamp": alert.timestamp.isoformat(),
                "tags": alert.tags,
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            })
        
        return {
            "success": True,
            "alerts": alert_data,
            "total": len(alert_data),
            "filters": {
                "severity": severity,
                "service": service,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 목록 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/send-alert")
async def send_alert(
    request: AlertRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """수동 알림 발송"""
    try:
        # 심각도 검증
        try:
            severity = AlertSeverity(request.severity)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 심각도입니다")
        
        alert_id = await monitoring_service.send_alert(
            title=request.title,
            message=request.message,
            severity=severity,
            service=request.service,
            tags=request.tags
        )
        
        return {
            "success": True,
            "alert_id": alert_id,
            "message": "알림이 성공적으로 발송되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 알림 발송 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/resolve-alert/{alert_id}")
async def resolve_alert(
    alert_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 해결 처리"""
    try:
        if alert_id not in monitoring_service.alerts:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        
        alert = monitoring_service.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        logger.info(f"✅ 알림 해결 처리: {alert.title}")
        
        return {
            "success": True,
            "message": "알림이 해결 처리되었습니다",
            "alert_id": alert_id,
            "resolved_at": alert.resolved_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 알림 해결 처리 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/metrics/{metric_name}")
async def get_metric_data(
    metric_name: str,
    hours: int = 24,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """메트릭 데이터 조회"""
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(status_code=400, detail="시간 범위는 1-168시간 사이여야 합니다")
        
        metric_data = monitoring_service.get_metrics_data(metric_name, hours)
        
        return {
            "success": True,
            "metric": metric_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 메트릭 데이터 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/metrics")
async def get_available_metrics(current_user: Dict[str, Any] = Depends(require_auth)):
    """사용 가능한 메트릭 목록 조회"""
    try:
        available_metrics = []
        
        for name, metrics_list in monitoring_service.metrics.items():
            if metrics_list:
                latest = metrics_list[-1]
                available_metrics.append({
                    "name": name,
                    "type": latest.metric_type.value,
                    "unit": latest.unit,
                    "last_updated": latest.timestamp.isoformat(),
                    "data_points": len(metrics_list),
                    "latest_value": latest.value
                })
        
        return {
            "success": True,
            "metrics": available_metrics,
            "total_metrics": len(available_metrics),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 메트릭 목록 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/add-metric")
async def add_metric(
    request: MetricRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """수동 메트릭 추가"""
    try:
        # 메트릭 유형 검증
        try:
            metric_type = MetricType(request.metric_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 메트릭 유형입니다")
        
        monitoring_service.add_metric(
            name=request.name,
            value=request.value,
            metric_type=metric_type,
            tags=request.tags,
            unit=request.unit
        )
        
        return {
            "success": True,
            "message": "메트릭이 성공적으로 추가되었습니다",
            "metric": {
                "name": request.name,
                "value": request.value,
                "type": request.metric_type,
                "unit": request.unit
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 메트릭 추가 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/thresholds")
async def get_thresholds(current_user: Dict[str, Any] = Depends(require_auth)):
    """성능 임계값 조회"""
    try:
        return {
            "success": True,
            "thresholds": monitoring_service.thresholds,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 임계값 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/thresholds")
async def update_thresholds(
    request: ThresholdUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """성능 임계값 업데이트"""
    try:
        # 유효한 임계값 키 확인
        valid_keys = set(monitoring_service.thresholds.keys())
        invalid_keys = set(request.thresholds.keys()) - valid_keys
        
        if invalid_keys:
            raise HTTPException(
                status_code=400, 
                detail=f"유효하지 않은 임계값 키: {list(invalid_keys)}"
            )
        
        monitoring_service.update_thresholds(request.thresholds)
        
        return {
            "success": True,
            "message": "임계값이 성공적으로 업데이트되었습니다",
            "updated_thresholds": request.thresholds,
            "current_thresholds": monitoring_service.thresholds,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 임계값 업데이트 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/start-monitoring")
async def start_monitoring(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """모니터링 시작"""
    try:
        if monitoring_service.monitoring_active:
            return {
                "success": False,
                "message": "모니터링이 이미 실행 중입니다"
            }
        
        # 백그라운드에서 모니터링 시작
        background_tasks.add_task(monitoring_service.start_monitoring)
        
        logger.info("📊 모니터링 시작 요청")
        
        return {
            "success": True,
            "message": "모니터링이 시작되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 모니터링 시작 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/stop-monitoring")
async def stop_monitoring(current_user: Dict[str, Any] = Depends(require_auth)):
    """모니터링 중지"""
    try:
        await monitoring_service.stop_monitoring()
        
        return {
            "success": True,
            "message": "모니터링이 중지되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 모니터링 중지 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/monitoring-status")
async def get_monitoring_status(current_user: Dict[str, Any] = Depends(require_auth)):
    """모니터링 상태 조회"""
    try:
        status = {
            "monitoring_active": monitoring_service.monitoring_active,
            "performance_interval": monitoring_service.performance_interval,
            "metric_retention_hours": monitoring_service.metric_retention_hours,
            "alert_retention_hours": monitoring_service.alert_retention_hours,
            "total_alerts": len(monitoring_service.alerts),
            "total_metrics": len(monitoring_service.metrics),
            "performance_snapshots": len(monitoring_service.performance_history),
            "uptime_hours": round((datetime.now() - monitoring_service.start_time).total_seconds() / 3600, 2),
            "alert_channels": {
                channel.value: len(handlers) 
                for channel, handlers in monitoring_service.alert_channels.items()
            }
        }
        
        return {
            "success": True,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 모니터링 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/dashboard-data")
async def get_dashboard_data(current_user: Dict[str, Any] = Depends(require_auth)):
    """대시보드용 종합 데이터 조회"""
    try:
        # 현재 성능 스냅샷
        current_snapshot = await monitoring_service.collect_system_performance()
        
        # 최근 24시간 성능 요약
        performance_summary = monitoring_service.get_performance_summary(24)
        
        # 최근 24시간 알림 요약
        alert_summary = monitoring_service.get_alert_summary(24)
        
        # 주요 메트릭 현재값
        key_metrics = {}
        for metric_name in ["system.cpu_percent", "system.memory_percent", "api.response_time", "trading.active_positions"]:
            if metric_name in monitoring_service.metrics and monitoring_service.metrics[metric_name]:
                latest = monitoring_service.metrics[metric_name][-1]
                key_metrics[metric_name] = {
                    "value": latest.value,
                    "unit": latest.unit,
                    "timestamp": latest.timestamp.isoformat()
                }
        
        return {
            "success": True,
            "dashboard": {
                "current_snapshot": {
                    "timestamp": current_snapshot.timestamp.isoformat(),
                    "cpu_percent": current_snapshot.cpu_percent,
                    "memory_percent": current_snapshot.memory_percent,
                    "disk_percent": current_snapshot.disk_percent,
                    "api_response_time": current_snapshot.api_response_time,
                    "active_positions": current_snapshot.active_positions,
                    "daily_trades": current_snapshot.daily_trades,
                    "daily_profit": current_snapshot.daily_profit
                },
                "performance_summary": performance_summary,
                "alert_summary": alert_summary,
                "key_metrics": key_metrics,
                "monitoring_active": monitoring_service.monitoring_active
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 대시보드 데이터 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

# 알림 설정 관련 엔드포인트들
@router.get("/notification-config")
async def get_notification_config(current_user: Dict[str, Any] = Depends(require_auth)):
    """알림 설정 조회"""
    try:
        config = notification_service.get_notification_config()
        
        return {
            "success": True,
            "config": config,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 알림 설정 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/notification-config")
async def update_notification_config(
    request: NotificationConfigRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 설정 업데이트"""
    try:
        # None이 아닌 값들만 딕셔너리로 변환
        config_updates = {
            k: v for k, v in request.dict().items() 
            if v is not None
        }
        
        if not config_updates:
            raise HTTPException(status_code=400, detail="업데이트할 설정이 없습니다")
        
        notification_service.configure_notifications(config_updates)
        updated_config = notification_service.get_notification_config()
        
        return {
            "success": True,
            "message": "알림 설정이 업데이트되었습니다",
            "updated_config": updated_config,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 알림 설정 업데이트 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/test-notification")
async def send_test_notification(
    notification_type: str = "trade",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """테스트 알림 발송"""
    try:
        if notification_type == "trade":
            # 테스트 거래 이벤트
            test_event = TradingEvent(
                event_type="buy",
                market="KRW-BTC",
                amount=100000,
                price=50000000
            )
            await notification_service.notify_trade_event(test_event)
            message = "거래 테스트 알림이 발송되었습니다"
            
        elif notification_type == "system":
            await monitoring_service.send_alert(
                title="🧪 시스템 테스트 알림",
                message="모니터링 시스템 테스트 알림입니다",
                severity=AlertSeverity.INFO,
                service="test"
            )
            message = "시스템 테스트 알림이 발송되었습니다"
            
        elif notification_type == "summary":
            await notification_service.notify_daily_summary()
            message = "일일 요약 테스트 알림이 발송되었습니다"
            
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 알림 유형입니다")
        
        return {
            "success": True,
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 테스트 알림 발송 오류: {str(e)}")
        return {"success": False, "error": str(e)}