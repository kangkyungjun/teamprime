"""
인증 미들웨어
- JWT 토큰 검증
- 보호된 라우트 접근 제어
- 현재 사용자 정보 주입
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse

from .auth_service import AuthService

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """인증 미들웨어"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    async def get_current_user(self, request: Request) -> Optional[Dict[str, Any]]:
        """현재 로그인한 사용자 정보 조회"""
        try:
            # Authorization 헤더에서 토큰 추출
            authorization = request.headers.get("Authorization")
            if not authorization:
                # 쿠키에서 토큰 추출 시도
                token = request.cookies.get("auth_token")
                if not token:
                    return None
            else:
                # "Bearer " 접두사 제거
                if authorization.startswith("Bearer "):
                    token = authorization[7:]
                else:
                    return None
            
            # 토큰 검증
            success, message, user_data = await AuthService.verify_session(token)
            
            if success and user_data:
                # 요청 객체에 사용자 정보 저장
                request.state.current_user = user_data
                return user_data
            else:
                logger.warning(f"토큰 검증 실패: {message}")
                return None
                
        except Exception as e:
            logger.error(f"사용자 인증 처리 오류: {str(e)}")
            return None
    
    async def require_auth(self, request: Request) -> Dict[str, Any]:
        """인증이 필요한 엔드포인트용 - 인증되지 않으면 401 오류"""
        user = await self.get_current_user(request)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증이 필요합니다",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    def require_auth_redirect(self, request: Request, redirect_url: str = "/login"):
        """인증이 필요한 페이지용 - 인증되지 않으면 로그인 페이지로 리다이렉트"""
        async def auth_check() -> Optional[RedirectResponse]:
            user = await self.get_current_user(request)
            
            if not user:
                # 현재 URL을 next 파라미터로 추가
                current_url = str(request.url)
                return RedirectResponse(
                    url=f"{redirect_url}?next={current_url}",
                    status_code=status.HTTP_302_FOUND
                )
            
            return None
        
        return auth_check()
    
    async def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """토큰으로부터 직접 사용자 정보 조회"""
        try:
            success, message, user_data = await AuthService.verify_session(token)
            
            if success and user_data:
                return user_data
            else:
                logger.warning(f"토큰 검증 실패: {message}")
                return None
                
        except Exception as e:
            logger.error(f"토큰 검증 오류: {str(e)}")
            return None
    
    def is_authenticated(self, request: Request) -> bool:
        """인증 상태 확인 (간단한 boolean 반환)"""
        return hasattr(request.state, 'current_user') and request.state.current_user is not None
    
    async def logout_user(self, request: Request) -> bool:
        """현재 사용자 로그아웃"""
        try:
            # Authorization 헤더 또는 쿠키에서 토큰 추출
            authorization = request.headers.get("Authorization")
            token = None
            
            if authorization and authorization.startswith("Bearer "):
                token = authorization[7:]
            else:
                token = request.cookies.get("auth_token")
            
            if token:
                success, message = await AuthService.logout_user(token)
                
                # 요청 상태에서 사용자 정보 제거
                if hasattr(request.state, 'current_user'):
                    delattr(request.state, 'current_user')
                
                logger.info(f"사용자 로그아웃: {message}")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"로그아웃 처리 오류: {str(e)}")
            return False

# 전역 인스턴스
auth_middleware = AuthMiddleware()

# FastAPI Depends용 함수들
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """현재 사용자 정보 조회 (의존성 주입용)"""
    return await auth_middleware.get_current_user(request)

async def require_auth(request: Request) -> Dict[str, Any]:
    """인증 필수 (의존성 주입용)"""
    return await auth_middleware.require_auth(request)

def optional_auth(request: Request) -> Optional[Dict[str, Any]]:
    """선택적 인증 (의존성 주입용)"""
    return getattr(request.state, 'current_user', None)