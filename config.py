"""시스템 설정 및 상수 정의"""

import os
from datetime import datetime
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 🚀 서버 시작 시간 (토큰 무효화용)
SERVER_START_TIME = datetime.utcnow().timestamp()

# API 설정
UPBIT_BASE = "https://api.upbit.com"

# 시장 설정 - MTFA 최적화된 10개 코인
DEFAULT_MARKETS = os.getenv("MARKETS", "KRW-IOTA,KRW-WCT,KRW-GMT,KRW-BTC,KRW-MEW,KRW-ETH,KRW-SHIB,KRW-PEPE,KRW-ANIME,KRW-LPT").split(",")
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

# 📊 신뢰도별 TP/SL 정책 시스템 (PDF 리뷰 기반 개선)
CONFIDENCE_RISK_POLICY = [
    # (최소신뢰도, 최대신뢰도, (TP%, SL%))
    (0.80, 0.85, (0.6, -0.4)),    # 낮은 신뢰도: 보수적 접근
    (0.85, 0.92, (0.9, -0.45)),   # 중간 신뢰도: 균형 접근
    (0.92, 1.01, (1.2, -0.5)),    # 높은 신뢰도: 적극적 접근
]

def get_risk_reward_from_confidence(confidence: float) -> tuple:
    """신뢰도 기반 TP/SL 정책 조회"""
    for min_conf, max_conf, (tp_pct, sl_pct) in CONFIDENCE_RISK_POLICY:
        if min_conf <= confidence < max_conf:
            return (tp_pct, sl_pct)
    
    # 기본값 (최소 신뢰도 미달시)
    return (0.5, -0.3)  # 보수적 기본값

# MTFA 최적화 설정 (Excel 결과 기반)
MTFA_OPTIMIZED_CONFIG = {
    "KRW-IOTA": {
        "profit_target": 2.5,     # 2.5% 익절
        "stop_loss": -1.0,        # -1.0% 손절
        "max_hold_minutes": 5,    # 5분 최대보유
        "mtfa_threshold": 0.80,   # 80% 신뢰도
        "expected_return": 141.3, # 예상 수익률 141.3%
        "expected_win_rate": 50.3 # 예상 승률 50.3%
    },
    "KRW-WCT": {
        "profit_target": 3.0, "stop_loss": -1.0, "max_hold_minutes": 20, 
        "mtfa_threshold": 0.80, "expected_return": 134.5, "expected_win_rate": 50.0
    },
    "KRW-GMT": {
        "profit_target": 2.5, "stop_loss": -1.0, "max_hold_minutes": 5,
        "mtfa_threshold": 0.85, "expected_return": 121.6, "expected_win_rate": 50.8
    },
    "KRW-BTC": {
        "profit_target": 3.0, "stop_loss": -1.0, "max_hold_minutes": 30,
        "mtfa_threshold": 0.80, "expected_return": 111.2, "expected_win_rate": 52.5
    },
    "KRW-MEW": {
        "profit_target": 3.0, "stop_loss": -0.2, "max_hold_minutes": 5,
        "mtfa_threshold": 0.82, "expected_return": 110.9, "expected_win_rate": 50.8
    },
    "KRW-ETH": {
        "profit_target": 2.5, "stop_loss": -1.0, "max_hold_minutes": 10,
        "mtfa_threshold": 0.80, "expected_return": 68.8, "expected_win_rate": 50.0
    },
    "KRW-SHIB": {
        "profit_target": 2.5, "stop_loss": -1.0, "max_hold_minutes": 10,
        "mtfa_threshold": 0.83, "expected_return": 47.8, "expected_win_rate": 50.8
    },
    "KRW-PEPE": {
        "profit_target": 1.5, "stop_loss": -0.6, "max_hold_minutes": 10,
        "mtfa_threshold": 0.85, "expected_return": 32.7, "expected_win_rate": 51.8
    },
    "KRW-ANIME": {
        "profit_target": 3.0, "stop_loss": -0.8, "max_hold_minutes": 5,
        "mtfa_threshold": 0.82, "expected_return": 31.7, "expected_win_rate": 50.0
    },
    "KRW-LPT": {
        "profit_target": 2.5, "stop_loss": -1.0, "max_hold_minutes": 60,
        "mtfa_threshold": 0.80, "expected_return": 26.7, "expected_win_rate": 51.4
    }
}

# 웹서버 설정
WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8001,
    "reload": False,
    "workers": 1,
}