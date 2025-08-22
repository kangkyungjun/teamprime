"""
🔐 모바일 인증 서비스

⚠️ 기존 시스템 호환성:
- 기존 웹 인증 시스템과 동일한 사용자 데이터베이스를 사용합니다.
- JWT 토큰 기반 인증으로 보안을 보장합니다.
- 모바일 기기 정보를 추가로 관리합니다.
"""

import jwt
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import secrets
import mysql.connector
from mysql.connector import Error

from ..models.mobile_user import MobileUser, MobileAuthRequest, MobileAuthResponse, MobileDeviceInfo, MobileSessionInfo

logger = logging.getLogger(__name__)

class MobileAuthService:
    """모바일 인증 서비스"""
    
    def __init__(self):
        # JWT 설정
        self.jwt_secret = "teamprime_mobile_secret_key_2024"  # 실제 환경에서는 환경변수 사용
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = 60  # 1시간
        self.refresh_token_expire_days = 30    # 30일
        
        # 데이터베이스 설정 (기존 시스템과 동일)
        self.db_config = {
            "host": "localhost",
            "database": "teamprime",
            "user": "teamprime", 
            "password": "teamprime123!",
            "charset": "utf8mb4",
            "autocommit": True
        }
        
        # 모바일 디바이스 관리
        self.active_sessions: Dict[str, MobileSessionInfo] = {}
        
        logger.info("🔐 모바일 인증 서비스 초기화")
    
    def _get_database_connection(self):
        """데이터베이스 연결 생성"""
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
            return None
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해시화"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return self._hash_password(password) == hashed_password
    
    def _generate_jwt_token(self, payload: Dict[str, Any], expire_minutes: int) -> str:
        """JWT 토큰 생성"""
        payload["exp"] = datetime.utcnow() + timedelta(minutes=expire_minutes)
        payload["iat"] = datetime.utcnow()
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ JWT 토큰 만료")
            return None
        except jwt.InvalidTokenError:
            logger.warning("⚠️ 유효하지 않은 JWT 토큰")
            return None
    
    async def authenticate_user(self, auth_request: MobileAuthRequest) -> MobileAuthResponse:
        """사용자 인증"""
        try:\n            connection = self._get_database_connection()\n            if not connection:\n                return MobileAuthResponse(\n                    success=False,\n                    error="데이터베이스 연결 실패",\n                    error_code="SYSTEM_DATABASE_ERROR"\n                )\n            \n            cursor = connection.cursor(dictionary=True)\n            \n            # 사용자 정보 조회\n            cursor.execute(\n                "SELECT * FROM users WHERE username = %s",\n                (auth_request.username,)\n            )\n            user_data = cursor.fetchone()\n            \n            if not user_data:\n                return MobileAuthResponse(\n                    success=False,\n                    error="존재하지 않는 사용자입니다",\n                    error_code="AUTH_INVALID_CREDENTIALS"\n                )\n            \n            # 비밀번호 검증\n            if not self._verify_password(auth_request.password, user_data["password"]):\n                return MobileAuthResponse(\n                    success=False,\n                    error="비밀번호가 일치하지 않습니다",\n                    error_code="AUTH_INVALID_CREDENTIALS"\n                )\n            \n            # 계정 활성화 상태 확인\n            if not user_data.get("is_active", True):\n                return MobileAuthResponse(\n                    success=False,\n                    error="비활성화된 계정입니다",\n                    error_code="AUTH_INVALID_CREDENTIALS"\n                )\n            \n            # 모바일 사용자 정보 생성\n            mobile_user = MobileUser(\n                user_id=str(user_data["id"]),\n                username=user_data["username"],\n                email=user_data.get("email"),\n                is_active=user_data.get("is_active", True),\n                created_at=user_data["created_at"].isoformat() if user_data.get("created_at") else datetime.utcnow().isoformat(),\n                last_login=datetime.utcnow().isoformat(),\n                mobile_settings={},\n                push_notification=True,\n                biometric_enabled=auth_request.biometric_token is not None\n            )\n            \n            # JWT 토큰 생성\n            access_token_payload = {\n                "user_id": mobile_user.user_id,\n                "username": mobile_user.username,\n                "device_id": auth_request.device_id,\n                "token_type": "access"\n            }\n            \n            refresh_token_payload = {\n                "user_id": mobile_user.user_id,\n                "username": mobile_user.username,\n                "device_id": auth_request.device_id,\n                "token_type": "refresh"\n            }\n            \n            access_token = self._generate_jwt_token(access_token_payload, self.access_token_expire_minutes)\n            refresh_token = self._generate_jwt_token(refresh_token_payload, self.refresh_token_expire_days * 24 * 60)\n            \n            # 디바이스 정보 등록/업데이트\n            await self._register_device(mobile_user.user_id, auth_request)\n            \n            # 세션 정보 생성\n            session_id = secrets.token_urlsafe(32)\n            session_info = MobileSessionInfo(\n                session_id=session_id,\n                user_id=mobile_user.user_id,\n                device_id=auth_request.device_id,\n                is_active=True,\n                created_at=datetime.utcnow().isoformat(),\n                expires_at=(datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)).isoformat(),\n                last_activity=datetime.utcnow().isoformat()\n            )\n            \n            self.active_sessions[session_id] = session_info\n            \n            # 마지막 로그인 시간 업데이트\n            cursor.execute(\n                "UPDATE users SET last_login = %s WHERE id = %s",\n                (datetime.utcnow(), user_data["id"])\n            )\n            \n            connection.close()\n            \n            logger.info(f"✅ 모바일 로그인 성공: {auth_request.username} ({auth_request.device_id})")\n            \n            return MobileAuthResponse(\n                success=True,\n                access_token=access_token,\n                refresh_token=refresh_token,\n                token_type="bearer",\n                expires_in=self.access_token_expire_minutes * 60,\n                user=mobile_user,\n                permissions=["trading:read", "portfolio:read", "trading:write"]  # 기본 권한\n            )\n            \n        except Exception as e:\n            logger.error(f"❌ 인증 처리 중 오류: {e}")\n            return MobileAuthResponse(\n                success=False,\n                error="인증 처리 중 오류가 발생했습니다",\n                error_code="UNKNOWN_ERROR"\n            )\n    \n    async def refresh_token(self, refresh_token: str) -> MobileAuthResponse:\n        """리프레시 토큰으로 액세스 토큰 갱신"""\n        try:\n            # 리프레시 토큰 검증\n            payload = self._verify_jwt_token(refresh_token)\n            if not payload:\n                return MobileAuthResponse(\n                    success=False,\n                    error="유효하지 않은 리프레시 토큰입니다",\n                    error_code="AUTH_TOKEN_EXPIRED"\n                )\n            \n            if payload.get("token_type") != "refresh":\n                return MobileAuthResponse(\n                    success=False,\n                    error="잘못된 토큰 타입입니다",\n                    error_code="AUTH_INVALID_CREDENTIALS"\n                )\n            \n            # 새로운 액세스 토큰 생성\n            access_token_payload = {\n                "user_id": payload["user_id"],\n                "username": payload["username"],\n                "device_id": payload["device_id"],\n                "token_type": "access"\n            }\n            \n            access_token = self._generate_jwt_token(access_token_payload, self.access_token_expire_minutes)\n            \n            return MobileAuthResponse(\n                success=True,\n                access_token=access_token,\n                token_type="bearer",\n                expires_in=self.access_token_expire_minutes * 60\n            )\n            \n        except Exception as e:\n            logger.error(f"❌ 토큰 갱신 중 오류: {e}")\n            return MobileAuthResponse(\n                success=False,\n                error="토큰 갱신 중 오류가 발생했습니다",\n                error_code="UNKNOWN_ERROR"\n            )\n    \n    async def verify_access_token(self, access_token: str) -> Optional[Dict[str, Any]]:\n        """액세스 토큰 검증 및 사용자 정보 반환"""\n        try:\n            payload = self._verify_jwt_token(access_token)\n            if not payload:\n                return None\n            \n            if payload.get("token_type") != "access":\n                return None\n            \n            # 세션 활성화 상태 확인\n            for session_info in self.active_sessions.values():\n                if (session_info.user_id == payload["user_id"] and \n                    session_info.device_id == payload["device_id"]):\n                    session_info.last_activity = datetime.utcnow().isoformat()\n                    break\n            \n            return payload\n            \n        except Exception as e:\n            logger.error(f"❌ 토큰 검증 중 오류: {e}")\n            return None\n    \n    async def logout(self, access_token: str) -> bool:\n        """로그아웃 처리"""\n        try:\n            payload = self._verify_jwt_token(access_token)\n            if not payload:\n                return False\n            \n            # 활성 세션에서 제거\n            sessions_to_remove = []\n            for session_id, session_info in self.active_sessions.items():\n                if (session_info.user_id == payload["user_id"] and \n                    session_info.device_id == payload["device_id"]):\n                    sessions_to_remove.append(session_id)\n            \n            for session_id in sessions_to_remove:\n                del self.active_sessions[session_id]\n            \n            logger.info(f"✅ 모바일 로그아웃: {payload['username']} ({payload['device_id']})")\n            return True\n            \n        except Exception as e:\n            logger.error(f"❌ 로그아웃 처리 중 오류: {e}")\n            return False\n    \n    async def _register_device(self, user_id: str, auth_request: MobileAuthRequest):\n        """모바일 기기 등록/업데이트"""\n        try:\n            device_info = MobileDeviceInfo(\n                device_id=auth_request.device_id,\n                device_name=auth_request.device_name,\n                platform="unknown",  # 실제 구현시 파악\n                os_version="unknown",\n                app_version=auth_request.app_version,\n                registered_at=datetime.utcnow().isoformat(),\n                last_active=datetime.utcnow().isoformat()\n            )\n            \n            # 실제 구현시 데이터베이스에 디바이스 정보 저장\n            logger.info(f"📱 기기 등록: {user_id} - {auth_request.device_name}")\n            \n        except Exception as e:\n            logger.error(f"❌ 기기 등록 중 오류: {e}")\n    \n    def get_active_sessions(self, user_id: str) -> List[MobileSessionInfo]:\n        """사용자의 활성 세션 목록 조회"""\n        sessions = []\n        for session_info in self.active_sessions.values():\n            if session_info.user_id == user_id:\n                sessions.append(session_info)\n        return sessions\n    \n    def get_session_count(self) -> int:\n        """현재 활성 세션 수"""\n        return len(self.active_sessions)\n    \n    async def cleanup_expired_sessions(self):\n        """만료된 세션 정리"""\n        try:\n            current_time = datetime.utcnow()\n            expired_sessions = []\n            \n            for session_id, session_info in self.active_sessions.items():\n                expires_at = datetime.fromisoformat(session_info.expires_at.replace('Z', '+00:00'))\n                if current_time > expires_at:\n                    expired_sessions.append(session_id)\n            \n            for session_id in expired_sessions:\n                del self.active_sessions[session_id]\n                \n            if expired_sessions:\n                logger.info(f"🧹 만료된 세션 정리: {len(expired_sessions)}개")\n                \n        except Exception as e:\n            logger.error(f"❌ 세션 정리 중 오류: {e}")