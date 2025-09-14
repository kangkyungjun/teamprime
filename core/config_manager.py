"""
향상된 설정 관리 시스템
- 환경별 설정 관리 (개발/운영/테스트)
- 런타임 설정 변경 및 검증
- 설정 캐싱 및 성능 최적화
"""

import os
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class LoggingConfig:
    """로깅 설정"""
    level: str = "INFO"
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: str = 'trading_system.log'
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_enabled: bool = True

@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""
    sqlite_path: str = "./upbit_candles.db"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_database: str = ""
    mysql_user: str = ""
    mysql_password: str = ""
    connection_pool_size: int = 5
    connection_timeout: int = 30

@dataclass
class TradingConfig:
    """거래 설정"""
    profit_target: float = 0.5  # %
    stop_loss: float = -0.3  # %
    max_positions: int = 5
    position_size: int = 100000  # 원
    min_volume_ratio: float = 2.0
    max_holding_time: int = 60  # 분

    # MTFA 설정
    mtfa_enabled: bool = True
    confidence_threshold: float = 0.8

@dataclass
class AnalysisConfig:
    """분석 설정"""
    ema_periods: list = field(default_factory=lambda: [5, 20, 60])
    rsi_period: int = 14
    volume_window: int = 24  # 시간
    surge_threshold: float = 3.0
    pattern_min_confidence: float = 0.7

@dataclass
class WebServerConfig:
    """웹 서버 설정"""
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = False
    workers: int = 1
    cors_enabled: bool = True
    cors_origins: list = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "https://localhost",
    ])

@dataclass
class SystemConfig:
    """시스템 설정"""
    environment: str = "development"  # development, production, testing
    debug: bool = True
    sleep_prevention: bool = True
    process_priority: int = -5
    max_memory_usage: int = 1024  # MB

    # API 설정
    upbit_base_url: str = "https://api.upbit.com"
    api_timeout: int = 30
    rate_limit_enabled: bool = True

class ConfigManager:
    """설정 관리자"""

    def __init__(self, env_file: Optional[str] = None):
        self._config_cache: Dict[str, Any] = {}
        self._env_file = env_file or '.env'
        self._load_environment()
        self._initialize_configs()

    def _load_environment(self):
        """환경 변수 로드"""
        if Path(self._env_file).exists():
            load_dotenv(self._env_file)
            logger.info(f"✅ 환경 설정 로드 완료: {self._env_file}")
        else:
            logger.warning(f"⚠️ 환경 파일 없음: {self._env_file} (기본값 사용)")

    def _initialize_configs(self):
        """설정 초기화"""
        # 환경 감지
        environment = os.getenv('ENVIRONMENT', 'development').lower()

        # 로깅 설정
        self.logging = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            file_path=os.getenv('LOG_FILE', 'trading_system.log'),
            console_enabled=os.getenv('LOG_CONSOLE', 'true').lower() == 'true'
        )

        # 데이터베이스 설정
        self.database = DatabaseConfig(
            sqlite_path=os.getenv('SQLITE_PATH', './upbit_candles.db'),
            mysql_host=os.getenv('MYSQL_HOST', 'localhost'),
            mysql_port=int(os.getenv('MYSQL_PORT', '3306')),
            mysql_database=os.getenv('MYSQL_DATABASE', ''),
            mysql_user=os.getenv('MYSQL_USER', ''),
            mysql_password=os.getenv('MYSQL_PASSWORD', ''),
        )

        # 거래 설정
        self.trading = TradingConfig(
            profit_target=float(os.getenv('PROFIT_TARGET', '0.5')),
            stop_loss=float(os.getenv('STOP_LOSS', '-0.3')),
            max_positions=int(os.getenv('MAX_POSITIONS', '5')),
            position_size=int(os.getenv('POSITION_SIZE', '100000')),
            mtfa_enabled=os.getenv('MTFA_ENABLED', 'true').lower() == 'true',
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.8'))
        )

        # 분석 설정
        ema_periods_str = os.getenv('EMA_PERIODS', '5,20,60')
        ema_periods = [int(x.strip()) for x in ema_periods_str.split(',')]

        self.analysis = AnalysisConfig(
            ema_periods=ema_periods,
            rsi_period=int(os.getenv('RSI_PERIOD', '14')),
            volume_window=int(os.getenv('VOLUME_WINDOW', '24')),
            surge_threshold=float(os.getenv('SURGE_THRESHOLD', '3.0'))
        )

        # 웹 서버 설정
        self.webserver = WebServerConfig(
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '8001')),
            reload=os.getenv('RELOAD', 'false').lower() == 'true',
            workers=int(os.getenv('WORKERS', '1'))
        )

        # 시스템 설정
        self.system = SystemConfig(
            environment=environment,
            debug=os.getenv('DEBUG', 'true').lower() == 'true',
            sleep_prevention=os.getenv('SLEEP_PREVENTION', 'true').lower() == 'true',
            api_timeout=int(os.getenv('API_TIMEOUT', '30')),
            rate_limit_enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        )

        # 마켓 설정
        markets_str = os.getenv("MARKETS", "KRW-IOTA,KRW-WCT,KRW-GMT,KRW-BTC,KRW-MEW,KRW-ETH,KRW-SHIB,KRW-PEPE,KRW-ANIME,KRW-LPT")
        self.markets = [market.strip() for market in markets_str.split(',')]

        logger.info(f"⚙️ 설정 초기화 완료 - 환경: {environment}, 마켓: {len(self.markets)}개")

    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보 반환"""
        return {
            "environment": self.system.environment,
            "debug": self.system.debug,
            "webserver_port": self.webserver.port,
            "markets_count": len(self.markets),
            "trading_config": {
                "profit_target": self.trading.profit_target,
                "stop_loss": self.trading.stop_loss,
                "max_positions": self.trading.max_positions,
                "mtfa_enabled": self.trading.mtfa_enabled
            },
            "database": {
                "mysql_enabled": bool(self.database.mysql_host and self.database.mysql_database),
                "sqlite_path": self.database.sqlite_path
            }
        }

    def validate_config(self) -> Dict[str, Any]:
        """설정 유효성 검증"""
        issues = []
        warnings = []

        # 필수 설정 검증
        if not self.markets:
            issues.append("마켓이 설정되지 않음")

        if self.trading.profit_target <= 0:
            issues.append(f"수익 목표가 유효하지 않음: {self.trading.profit_target}")

        if self.trading.stop_loss >= 0:
            issues.append(f"손절매가 유효하지 않음: {self.trading.stop_loss}")

        # 경고사항 검증
        if self.system.environment == 'production' and self.system.debug:
            warnings.append("운영 환경에서 디버그 모드가 활성화됨")

        if self.trading.max_positions > 10:
            warnings.append(f"최대 포지션 수가 많음: {self.trading.max_positions}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def update_runtime_config(self, section: str, key: str, value: Any) -> bool:
        """런타임 설정 업데이트"""
        try:
            if hasattr(self, section):
                section_obj = getattr(self, section)
                if hasattr(section_obj, key):
                    old_value = getattr(section_obj, key)
                    setattr(section_obj, key, value)
                    logger.info(f"🔄 런타임 설정 업데이트: {section}.{key} = {value} (이전: {old_value})")
                    return True
                else:
                    logger.error(f"❌ 알 수 없는 설정 키: {section}.{key}")
            else:
                logger.error(f"❌ 알 수 없는 설정 섹션: {section}")
            return False
        except Exception as e:
            logger.error(f"❌ 런타임 설정 업데이트 실패: {str(e)}")
            return False

    def is_production(self) -> bool:
        """운영 환경 여부 확인"""
        return self.system.environment == 'production'

    def is_development(self) -> bool:
        """개발 환경 여부 확인"""
        return self.system.environment == 'development'

    def is_testing(self) -> bool:
        """테스트 환경 여부 확인"""
        return self.system.environment == 'testing'

# 전역 설정 관리자 인스턴스
config_manager = ConfigManager()

# 하위 호환성을 위한 기존 설정 변수들
DEFAULT_MARKETS = config_manager.markets
WEB_CONFIG = {
    "port": config_manager.webserver.port,
    "host": config_manager.webserver.host
}
SCALPING_CONFIG = {
    "profit_target": config_manager.trading.profit_target,
    "stop_loss": config_manager.trading.stop_loss,
    "max_positions": config_manager.trading.max_positions,
    "position_size": config_manager.trading.position_size,
    "min_volume_ratio": config_manager.trading.min_volume_ratio,
    "max_holding_time": config_manager.trading.max_holding_time,
}
ANALYSIS_CONFIG = {
    "ema_periods": config_manager.analysis.ema_periods,
    "rsi_period": config_manager.analysis.rsi_period,
    "volume_window": config_manager.analysis.volume_window,
    "surge_threshold": config_manager.analysis.surge_threshold,
    "pattern_min_confidence": config_manager.analysis.pattern_min_confidence,
}