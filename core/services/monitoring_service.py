"""
모니터링 및 알림 서비스
실시간 성능 모니터링, 알림 발송, 메트릭 수집
"""

import logging
import asyncio
import time
import json
import os
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import psutil
import aiofiles

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(Enum):
    """알림 채널"""
    LOG = "log"
    FILE = "file"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"

class MetricType(Enum):
    """메트릭 유형"""
    COUNTER = "counter"      # 누적값 (거래 횟수 등)
    GAUGE = "gauge"          # 현재값 (CPU 사용률 등)
    HISTOGRAM = "histogram"  # 분포값 (응답 시간 등)
    TIMER = "timer"          # 시간 측정

@dataclass
class Alert:
    """알림 메시지"""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    service: str
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
@dataclass 
class Metric:
    """메트릭 데이터"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

@dataclass
class PerformanceSnapshot:
    """성능 스냅샷"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    network_sent: int
    network_recv: int
    
    # 거래 관련 메트릭
    active_positions: int = 0
    daily_trades: int = 0
    daily_profit: float = 0.0
    api_response_time: float = 0.0
    
    # 시스템 상태
    uptime_seconds: float = 0.0
    error_rate: float = 0.0

class MonitoringService:
    """모니터링 및 알림 서비스"""
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.metrics: Dict[str, List[Metric]] = {}
        self.performance_history: List[PerformanceSnapshot] = []
        self.alert_channels: Dict[AlertChannel, List[Callable]] = {
            AlertChannel.LOG: [],
            AlertChannel.FILE: [],
            AlertChannel.EMAIL: [],
            AlertChannel.WEBHOOK: [],
            AlertChannel.SLACK: []
        }
        
        # 모니터링 설정
        self.monitoring_active = False
        self.performance_interval = 30  # 30초마다 성능 수집
        self.metric_retention_hours = 24  # 24시간 메트릭 보관
        self.alert_retention_hours = 168  # 7일간 알림 보관
        
        # 임계값 설정
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "api_response_time": 5.0,
            "error_rate": 5.0
        }
        
        # 알림 제한 (중복 방지)
        self.alert_cooldown = 300  # 5분간 같은 알림 방지
        self.last_alert_time: Dict[str, datetime] = {}
        
        # 성능 모니터링 시작 시간
        self.start_time = datetime.now()
        
        logger.info("✅ 모니터링 서비스 초기화 완료")
    
    def register_alert_handler(self, channel: AlertChannel, handler: Callable):
        """알림 핸들러 등록"""
        try:
            self.alert_channels[channel].append(handler)
            logger.info(f"📢 알림 핸들러 등록: {channel.value}")
            
        except Exception as e:
            logger.error(f"❌ 알림 핸들러 등록 실패 ({channel.value}): {str(e)}")
    
    async def send_alert(
        self, 
        title: str, 
        message: str, 
        severity: AlertSeverity = AlertSeverity.INFO,
        service: str = "system",
        tags: Optional[Dict[str, str]] = None,
        channels: Optional[List[AlertChannel]] = None
    ) -> str:
        """알림 발송"""
        try:
            # 알림 ID 생성
            alert_id = f"{service}_{int(time.time())}_{hash(title + message) % 1000}"
            
            # 중복 알림 방지 (쿨다운 체크)
            cooldown_key = f"{service}_{title}"
            now = datetime.now()
            
            if cooldown_key in self.last_alert_time:
                last_time = self.last_alert_time[cooldown_key]
                if (now - last_time).total_seconds() < self.alert_cooldown:
                    logger.debug(f"알림 쿨다운 중: {title}")
                    return alert_id
            
            self.last_alert_time[cooldown_key] = now
            
            # 알림 객체 생성
            alert = Alert(
                id=alert_id,
                title=title,
                message=message,
                severity=severity,
                timestamp=now,
                service=service,
                tags=tags or {}
            )
            
            # 알림 저장
            self.alerts[alert_id] = alert
            
            # 채널별 알림 발송
            if channels is None:
                channels = [AlertChannel.LOG, AlertChannel.FILE]  # 기본 채널
            
            for channel in channels:
                handlers = self.alert_channels.get(channel, [])
                for handler in handlers:
                    try:
                        await handler(alert)
                    except Exception as e:
                        logger.error(f"❌ 알림 핸들러 실행 오류 ({channel.value}): {str(e)}")
            
            # 심각도별 로깅
            log_msg = f"🚨 [{severity.value.upper()}] {title}: {message}"
            if severity == AlertSeverity.CRITICAL:
                logger.critical(log_msg)
            elif severity == AlertSeverity.ERROR:
                logger.error(log_msg)
            elif severity == AlertSeverity.WARNING:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)
            
            return alert_id
            
        except Exception as e:
            logger.error(f"❌ 알림 발송 오류: {str(e)}")
            return ""
    
    def add_metric(
        self, 
        name: str, 
        value: float, 
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
        unit: str = ""
    ):
        """메트릭 추가"""
        try:
            metric = Metric(
                name=name,
                value=value,
                metric_type=metric_type,
                timestamp=datetime.now(),
                tags=tags or {},
                unit=unit
            )
            
            if name not in self.metrics:
                self.metrics[name] = []
            
            self.metrics[name].append(metric)
            
            # 메트릭 보관 기간 관리
            cutoff_time = datetime.now() - timedelta(hours=self.metric_retention_hours)
            self.metrics[name] = [
                m for m in self.metrics[name] 
                if m.timestamp >= cutoff_time
            ]
            
            logger.debug(f"📊 메트릭 추가: {name} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"❌ 메트릭 추가 오류: {str(e)}")
    
    async def collect_system_performance(self) -> PerformanceSnapshot:
        """시스템 성능 수집"""
        try:
            # 기본 시스템 메트릭
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # 거래 관련 메트릭 수집
            active_positions = 0
            daily_trades = 0
            daily_profit = 0.0
            
            try:
                from ..services.trading_engine import trading_state
                active_positions = len(trading_state.positions)
                daily_trades = trading_state.daily_trades
                daily_profit = -trading_state.daily_loss  # 손실을 수익으로 변환
            except Exception:
                pass  # 거래 엔진 연결 실패시 기본값 사용
            
            # API 응답 시간 측정
            api_response_time = 0.0
            try:
                start_time = time.time()
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.upbit.com/v1/market/all", timeout=5) as response:
                        if response.status == 200:
                            api_response_time = (time.time() - start_time) * 1000  # ms
            except Exception:
                api_response_time = 9999.0  # 연결 실패 표시
            
            # 성능 스냅샷 생성
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_percent=disk.percent,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv,
                active_positions=active_positions,
                daily_trades=daily_trades,
                daily_profit=daily_profit,
                api_response_time=api_response_time,
                uptime_seconds=(datetime.now() - self.start_time).total_seconds(),
                error_rate=0.0  # TODO: 실제 오류율 계산
            )
            
            # 메트릭으로 추가
            self.add_metric("system.cpu_percent", cpu_percent, MetricType.GAUGE, unit="%")
            self.add_metric("system.memory_percent", memory.percent, MetricType.GAUGE, unit="%")
            self.add_metric("system.disk_percent", disk.percent, MetricType.GAUGE, unit="%")
            self.add_metric("trading.active_positions", active_positions, MetricType.GAUGE)
            self.add_metric("trading.daily_trades", daily_trades, MetricType.COUNTER)
            self.add_metric("trading.daily_profit", daily_profit, MetricType.GAUGE, unit="KRW")
            self.add_metric("api.response_time", api_response_time, MetricType.HISTOGRAM, unit="ms")
            
            # 성능 히스토리에 추가
            self.performance_history.append(snapshot)
            
            # 히스토리 크기 제한 (최근 1000개)
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            # 임계값 확인 및 알림
            await self._check_performance_thresholds(snapshot)
            
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ 성능 수집 오류: {str(e)}")
            # 기본 스냅샷 반환
            return PerformanceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                disk_percent=0.0,
                network_sent=0,
                network_recv=0
            )
    
    async def _check_performance_thresholds(self, snapshot: PerformanceSnapshot):
        """성능 임계값 확인 및 알림"""
        try:
            # CPU 사용률 확인
            if snapshot.cpu_percent > self.thresholds["cpu_percent"]:
                await self.send_alert(
                    f"높은 CPU 사용률",
                    f"CPU 사용률이 {snapshot.cpu_percent:.1f}%로 임계값 {self.thresholds['cpu_percent']}%를 초과했습니다",
                    AlertSeverity.WARNING,
                    "system"
                )
            
            # 메모리 사용률 확인
            if snapshot.memory_percent > self.thresholds["memory_percent"]:
                await self.send_alert(
                    f"높은 메모리 사용률",
                    f"메모리 사용률이 {snapshot.memory_percent:.1f}%로 임계값 {self.thresholds['memory_percent']}%를 초과했습니다",
                    AlertSeverity.WARNING,
                    "system"
                )
            
            # 디스크 사용률 확인
            if snapshot.disk_percent > self.thresholds["disk_percent"]:
                await self.send_alert(
                    f"높은 디스크 사용률",
                    f"디스크 사용률이 {snapshot.disk_percent:.1f}%로 임계값 {self.thresholds['disk_percent']}%를 초과했습니다",
                    AlertSeverity.ERROR,
                    "system"
                )
            
            # API 응답 시간 확인
            if snapshot.api_response_time > self.thresholds["api_response_time"] * 1000:  # ms로 변환
                await self.send_alert(
                    f"느린 API 응답",
                    f"업비트 API 응답 시간이 {snapshot.api_response_time:.0f}ms로 임계값 {self.thresholds['api_response_time']}초를 초과했습니다",
                    AlertSeverity.WARNING,
                    "upbit_api"
                )
                
        except Exception as e:
            logger.error(f"❌ 임계값 확인 오류: {str(e)}")
    
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        logger.info("📊 성능 모니터링 시작")
        
        # 기본 알림 핸들러 등록
        await self._setup_default_alert_handlers()
        
        # 성능 수집 루프 시작
        performance_task = asyncio.create_task(self._performance_monitoring_loop())
        
        # 알림 정리 루프 시작
        cleanup_task = asyncio.create_task(self._cleanup_old_data_loop())
        
        # 모든 태스크 실행
        await asyncio.gather(performance_task, cleanup_task, return_exceptions=True)
    
    async def _performance_monitoring_loop(self):
        """성능 모니터링 루프"""
        while self.monitoring_active:
            try:
                await self.collect_system_performance()
                await asyncio.sleep(self.performance_interval)
                
            except Exception as e:
                logger.error(f"❌ 성능 모니터링 루프 오류: {str(e)}")
                await asyncio.sleep(self.performance_interval)
    
    async def _cleanup_old_data_loop(self):
        """오래된 데이터 정리 루프"""
        while self.monitoring_active:
            try:
                await self._cleanup_old_alerts()
                await self._cleanup_old_metrics()
                await asyncio.sleep(3600)  # 1시간마다 정리
                
            except Exception as e:
                logger.error(f"❌ 데이터 정리 루프 오류: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_alerts(self):
        """오래된 알림 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.alert_retention_hours)
            
            old_alerts = [
                alert_id for alert_id, alert in self.alerts.items()
                if alert.timestamp < cutoff_time
            ]
            
            for alert_id in old_alerts:
                del self.alerts[alert_id]
            
            if old_alerts:
                logger.info(f"🗑️ 오래된 알림 {len(old_alerts)}개 정리 완료")
                
        except Exception as e:
            logger.error(f"❌ 알림 정리 오류: {str(e)}")
    
    async def _cleanup_old_metrics(self):
        """오래된 메트릭 정리"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.metric_retention_hours)
            cleaned_count = 0
            
            for name in list(self.metrics.keys()):
                old_count = len(self.metrics[name])
                self.metrics[name] = [
                    m for m in self.metrics[name]
                    if m.timestamp >= cutoff_time
                ]
                cleaned_count += old_count - len(self.metrics[name])
                
                # 빈 메트릭 제거
                if not self.metrics[name]:
                    del self.metrics[name]
            
            if cleaned_count > 0:
                logger.info(f"🗑️ 오래된 메트릭 {cleaned_count}개 정리 완료")
                
        except Exception as e:
            logger.error(f"❌ 메트릭 정리 오류: {str(e)}")
    
    async def _setup_default_alert_handlers(self):
        """기본 알림 핸들러 설정"""
        try:
            # 파일 알림 핸들러
            async def file_alert_handler(alert: Alert):
                try:
                    alert_data = {
                        "id": alert.id,
                        "timestamp": alert.timestamp.isoformat(),
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity.value,
                        "service": alert.service,
                        "tags": alert.tags
                    }
                    
                    os.makedirs("logs", exist_ok=True)
                    async with aiofiles.open("logs/alerts.jsonl", "a", encoding="utf-8") as f:
                        await f.write(json.dumps(alert_data, ensure_ascii=False) + "\n")
                        
                except Exception as e:
                    logger.error(f"❌ 파일 알림 핸들러 오류: {str(e)}")
            
            self.register_alert_handler(AlertChannel.FILE, file_alert_handler)
            
        except Exception as e:
            logger.error(f"❌ 기본 알림 핸들러 설정 오류: {str(e)}")
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """알림 요약 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_alerts = [
                alert for alert in self.alerts.values()
                if alert.timestamp >= cutoff_time
            ]
            
            # 심각도별 집계
            severity_counts = {}
            for severity in AlertSeverity:
                severity_counts[severity.value] = len([
                    alert for alert in recent_alerts
                    if alert.severity == severity
                ])
            
            # 서비스별 집계
            service_counts = {}
            for alert in recent_alerts:
                service_counts[alert.service] = service_counts.get(alert.service, 0) + 1
            
            return {
                "period_hours": hours,
                "total_alerts": len(recent_alerts),
                "by_severity": severity_counts,
                "by_service": service_counts,
                "recent_alerts": [
                    {
                        "id": alert.id,
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity.value,
                        "service": alert.service,
                        "timestamp": alert.timestamp.isoformat()
                    }
                    for alert in sorted(recent_alerts, key=lambda x: x.timestamp, reverse=True)[:10]
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ 알림 요약 조회 오류: {str(e)}")
            return {"error": str(e)}
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """성능 요약 조회"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_snapshots = [
                snapshot for snapshot in self.performance_history
                if snapshot.timestamp >= cutoff_time
            ]
            
            if not recent_snapshots:
                return {"error": "성능 데이터가 없습니다"}
            
            # 평균값 계산
            avg_cpu = sum(s.cpu_percent for s in recent_snapshots) / len(recent_snapshots)
            avg_memory = sum(s.memory_percent for s in recent_snapshots) / len(recent_snapshots)
            avg_api_time = sum(s.api_response_time for s in recent_snapshots) / len(recent_snapshots)
            
            # 최신 데이터
            latest = recent_snapshots[-1]
            
            return {
                "period_hours": hours,
                "snapshot_count": len(recent_snapshots),
                "averages": {
                    "cpu_percent": round(avg_cpu, 2),
                    "memory_percent": round(avg_memory, 2),
                    "api_response_time": round(avg_api_time, 2)
                },
                "latest": {
                    "timestamp": latest.timestamp.isoformat(),
                    "cpu_percent": latest.cpu_percent,
                    "memory_percent": latest.memory_percent,
                    "memory_mb": round(latest.memory_mb, 1),
                    "disk_percent": latest.disk_percent,
                    "active_positions": latest.active_positions,
                    "daily_trades": latest.daily_trades,
                    "daily_profit": latest.daily_profit,
                    "api_response_time": latest.api_response_time,
                    "uptime_hours": round(latest.uptime_seconds / 3600, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 성능 요약 조회 오류: {str(e)}")
            return {"error": str(e)}
    
    def get_metrics_data(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """특정 메트릭 데이터 조회"""
        try:
            if metric_name not in self.metrics:
                return {"error": f"메트릭을 찾을 수 없습니다: {metric_name}"}
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                metric for metric in self.metrics[metric_name]
                if metric.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {"error": "메트릭 데이터가 없습니다"}
            
            # 통계 계산
            values = [m.value for m in recent_metrics]
            
            return {
                "metric_name": metric_name,
                "period_hours": hours,
                "data_points": len(recent_metrics),
                "statistics": {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1]
                },
                "unit": recent_metrics[-1].unit if recent_metrics else "",
                "data": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value,
                        "tags": m.tags
                    }
                    for m in recent_metrics[-100:]  # 최근 100개만
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ 메트릭 데이터 조회 오류: {str(e)}")
            return {"error": str(e)}
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        logger.info("🛑 성능 모니터링 중지")
    
    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """임계값 업데이트"""
        try:
            self.thresholds.update(new_thresholds)
            logger.info(f"⚙️ 임계값 업데이트: {new_thresholds}")
            
        except Exception as e:
            logger.error(f"❌ 임계값 업데이트 오류: {str(e)}")

# 전역 모니터링 서비스 인스턴스
monitoring_service = MonitoringService()