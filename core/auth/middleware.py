"""
권한 검증 미들웨어
- JWT 토큰 검증
- 역할 기반 접근 제어 (RBAC)
- VIP 서비스 보호
- API 엔드포인트 권한 검증
"""

import logging
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse

from .auth_service import AuthService
from .owner_system import owner_system

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
    
    # === 역할 기반 권한 검증 메소드들 ===
    
    async def require_role(self, request: Request, required_roles: List[str]) -> Dict[str, Any]:
        """특정 역할 필수"""
        user = await self.require_auth(request)
        user_role = user.get("role")
        
        if user_role not in required_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"접근 권한이 없습니다. 필요 권한: {', '.join(required_roles)}"
            )
        return user
    
    async def require_owner(self, request: Request) -> Dict[str, Any]:
        """Owner 권한 필수"""
        user = await self.require_auth(request)
        
        if user.get("role") != "owner":
            raise HTTPException(status_code=403, detail="Owner 권한이 필요합니다")
        return user
    
    async def require_vip_access(self, request: Request) -> Dict[str, Any]:
        """VIP 서비스 접근 권한 필수 (Owner/Prime만)"""
        user = await self.require_auth(request)
        user_id = user.get("id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
        
        has_vip = await owner_system.has_vip_access(user_id)
        if not has_vip:
            raise HTTPException(
                status_code=403, 
                detail="VIP 서비스 접근 권한이 없습니다. Owner 또는 Prime 권한이 필요합니다."
            )
        return user
    
    async def require_promotion_permission(self, request: Request) -> Dict[str, Any]:
        """사용자 승급 권한 필수 (Owner/Prime만)"""
        user = await self.require_auth(request)
        user_id = user.get("id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
        
        can_promote = await owner_system.can_promote_users(user_id)
        if not can_promote:
            raise HTTPException(
                status_code=403, 
                detail="사용자 승급 권한이 없습니다. Owner 또는 Prime 권한이 필요합니다."
            )
        return user
    
    async def require_expense_approval(self, request: Request) -> Dict[str, Any]:
        """지출 승인 권한 필수 (Owner/Prime/Manager만)"""
        user = await self.require_auth(request)
        user_role = user.get("role")
        
        if user_role not in ["owner", "prime", "manager"]:
            raise HTTPException(
                status_code=403, 
                detail="지출 승인 권한이 없습니다. Manager 이상 권한이 필요합니다."
            )
        return user
    
    async def get_user_permissions(self, user_id: int) -> dict:
        """사용자 권한 정보 조회"""
        try:
            user_role = await owner_system.get_user_role(user_id)
            if not user_role:
                return {}
            
            return owner_system.get_role_permissions(user_role)
            
        except Exception as e:
            logger.error(f"사용자 권한 조회 실패: {str(e)}")
            return {}
    
    async def check_permission(self, request: Request, required_permission: str) -> Dict[str, Any]:
        """특정 권한 확인"""
        user = await self.require_auth(request)
        user_id = user.get("id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="사용자 정보를 찾을 수 없습니다")
        
        permissions = await self.get_user_permissions(user_id)
        if not permissions.get(required_permission, False):
            raise HTTPException(
                status_code=403, 
                detail=f"'{required_permission}' 권한이 필요합니다"
            )
        return user
    
    async def check_api_access(self, request: Request) -> bool:
        """API 엔드포인트별 접근 권한 검증"""
        path = request.url.path
        method = request.method
        
        # 사용자 정보 조회
        user = await self.get_current_user(request)
        if not user:
            return False
        
        user_id = user.get("id")
        if not user_id:
            return False
        
        # VIP 서비스 (암호화폐 거래) 경로 보호
        vip_paths = [
            "/api/start-trading",
            "/api/stop-trading", 
            "/api/emergency-stop",
            "/api/trading-status",
            "/api/trading-logs",
            "/api/mtfa-dashboard-data",
            "/volume-surge-analysis",
            "/backtest-performance"
        ]
        
        if any(path.startswith(vip_path) for vip_path in vip_paths):
            return await owner_system.has_vip_access(user_id)
        
        # 관리자 전용 경로
        admin_paths = [
            "/api/system-admin",
            "/api/user-management",
            "/api/run-manual-optimization"
        ]
        
        if any(path.startswith(admin_path) for admin_path in admin_paths):
            user_role = await owner_system.get_user_role(user_id)
            return user_role == "owner"
        
        # 일반 접근은 로그인만 필요
        return True

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

# 역할 기반 권한 검증 함수들 (의존성 주입용)
async def require_owner(request: Request) -> Dict[str, Any]:
    """Owner 권한 필수"""
    return await auth_middleware.require_owner(request)

async def require_vip_access(request: Request) -> Dict[str, Any]:
    """VIP 서비스 접근 권한 필수 (Owner/Prime만)"""
    return await auth_middleware.require_vip_access(request)

async def require_promotion_permission(request: Request) -> Dict[str, Any]:
    """사용자 승급 권한 필수 (Owner/Prime만)"""
    return await auth_middleware.require_promotion_permission(request)

async def require_expense_approval(request: Request) -> Dict[str, Any]:
    """지출 승인 권한 필수 (Owner/Prime/Manager만)"""
    return await auth_middleware.require_expense_approval(request)

# 특정 권한별 검증 함수들
async def require_crypto_trading(request: Request) -> Dict[str, Any]:
    """암호화폐 거래 권한 필수"""
    return await auth_middleware.check_permission(request, "crypto_trading")

async def require_task_management(request: Request) -> Dict[str, Any]:
    """업무 관리 권한 필수"""
    return await auth_middleware.check_permission(request, "task_management")

async def require_income_management(request: Request) -> Dict[str, Any]:
    """수익 관리 권한 필수"""
    return await auth_middleware.check_permission(request, "income_management")