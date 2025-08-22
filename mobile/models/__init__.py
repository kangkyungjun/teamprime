"""
📊 Teamprime Mobile Data Models

⚠️ 모바일 전용 데이터 모델:
- 기존 시스템의 모델을 수정하지 않고 모바일용으로 새로 정의합니다.
- 기존 데이터를 모바일 형식으로 변환하기 위한 전용 모델입니다.
- JSON 직렬화 및 Flutter 호환성을 고려한 설계입니다.

📱 모바일 모델 목록:
- mobile_user.py: 모바일 사용자 정보
- mobile_trading.py: 모바일 거래 데이터
- mobile_portfolio.py: 모바일 포트폴리오 데이터  
- mobile_response.py: 모바일 API 응답 모델
"""

from .mobile_user import MobileUser, MobileAuthRequest, MobileAuthResponse
from .mobile_trading import MobileTradingStatus, MobilePosition, MobileTradingControl
from .mobile_portfolio import MobilePortfolioSummary, MobileHolding, MobilePerformance
from .mobile_response import MobileResponse, MobileErrorResponse, MobilePaginatedResponse

__all__ = [
    # User models
    "MobileUser",
    "MobileAuthRequest", 
    "MobileAuthResponse",
    
    # Trading models
    "MobileTradingStatus",
    "MobilePosition",
    "MobileTradingControl",
    
    # Portfolio models  
    "MobilePortfolioSummary",
    "MobileHolding",
    "MobilePerformance",
    
    # Response models
    "MobileResponse",
    "MobileErrorResponse", 
    "MobilePaginatedResponse"
]