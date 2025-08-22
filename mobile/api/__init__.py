"""
📱 Teamprime Mobile API Routers

⚠️ 기존 시스템 보호 규칙:
- 이 모듈의 모든 API는 기존 시스템과 완전히 분리되어 있습니다.
- 기존 데이터는 읽기 전용으로만 접근합니다.
- 새로운 포트(8002)에서 독립적으로 실행됩니다.

🔗 모바일 API 라우터 목록:
- auth.py: 모바일 전용 인증 API
- trading.py: 거래 정보 조회 및 제어 API
- portfolio.py: 포트폴리오 조회 API
- realtime.py: 실시간 데이터 스트리밍 API
"""

from .auth import router as auth_router
from .trading import router as trading_router  
from .portfolio import router as portfolio_router
from .realtime import router as realtime_router

# 모든 모바일 API 라우터 목록
mobile_routers = [
    auth_router,
    trading_router,
    portfolio_router, 
    realtime_router
]

__all__ = [
    "auth_router",
    "trading_router", 
    "portfolio_router",
    "realtime_router",
    "mobile_routers"
]