"""
🔧 Teamprime Mobile Services

⚠️ 기존 시스템 안전성 보장:
- 모든 서비스는 기존 시스템의 데이터를 읽기 전용으로만 접근합니다.
- 기존 거래 엔진이나 데이터베이스를 절대 수정하지 않습니다.
- 완전히 독립된 모듈로 동작합니다.

📦 모바일 서비스 모듈:
- data_adapter.py: 기존 데이터 읽기 전용 어댑터
- websocket.py: 모바일용 WebSocket 매니저
- auth_service.py: 모바일 인증 서비스
- notification.py: 푸시 알림 서비스
"""

from .data_adapter import ReadOnlyDataAdapter
from .websocket import MobileWebSocketManager
from .auth_service import MobileAuthService

# 전역 인스턴스 (싱글톤)
data_adapter = ReadOnlyDataAdapter()
websocket_manager = MobileWebSocketManager()
auth_service = MobileAuthService()

__all__ = [
    "ReadOnlyDataAdapter",
    "MobileWebSocketManager", 
    "MobileAuthService",
    "data_adapter",
    "websocket_manager",
    "auth_service"
]