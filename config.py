"""시스템 설정 및 상수 정의"""

import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 설정
UPBIT_BASE = "https://api.upbit.com"

# 시장 설정
DEFAULT_MARKETS = os.getenv("MARKETS", "KRW-BTC,KRW-XRP,KRW-ETH,KRW-DOGE,KRW-BTT").split(",")
DEFAULT_YEARS = int(os.getenv("YEARS", "3"))  # 최초 보장 수집 기간

# 데이터 수집 설정
UNITS = [1, 5, 15]  # 1/5/15분봉
BATCH = 200  # Upbit candles limit
CONCURRENCY = 1  # 안전하게 직렬(레이트리밋 고려)

# 거래 설정 (스캘핑 모드)
SCALPING_CONFIG = {
    "profit_target": 0.5,  # 목표 수익률 0.5%
    "stop_loss": -0.3,  # 손절매 -0.3%
    "max_positions": 5,  # 최대 동시 포지션
    "position_size": 100000,  # 포지션당 10만원
    "min_volume_ratio": 2.0,  # 최소 거래량 배수
    "max_holding_time": 60,  # 최대 보유 시간 (분)
}

# 분석 설정
ANALYSIS_CONFIG = {
    "ema_periods": [5, 20, 60],  # EMA 기간
    "rsi_period": 14,  # RSI 기간
    "volume_window": 24,  # 거래량 분석 윈도우 (시간)
    "surge_threshold": 3.0,  # 거래량 급증 임계값
    "pattern_min_confidence": 0.7,  # 패턴 인식 최소 신뢰도
}

# 자동 최적화 설정
OPTIMIZATION_CONFIG = {
    "enabled": True,  # 자동 최적화 활성화
    "interval_hours": 24,  # 최적화 주기 (시간)
    "min_trades": 20,  # 최적화를 위한 최소 거래 수
    "lookback_days": 7,  # 최적화 데이터 기간
    "target_win_rate": 60,  # 목표 승률 %
    "max_iterations": 100,  # 최대 최적화 반복 횟수
}

# 로깅 설정
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "trading_system.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5,
}

# 웹서버 설정
WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8001,
    "reload": False,
    "workers": 1,
}