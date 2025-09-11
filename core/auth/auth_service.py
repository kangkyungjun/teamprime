"""
인증 서비스 - 간소화 (보안 강화)
- 사용자 등록 및 로그인 (기본 정보만)
- JWT 토큰 기반 세션 관리
- 패스워드 검증
- API 키 저장 제거로 보안 강화
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User
from ..database.mysql_connection import get_mysql_session
from config import SERVER_START_TIME

logger = logging.getLogger(__name__)

class AuthService:
    """인증 관련 서비스 - 간소화 (보안 강화)"""
    
    # JWT 설정
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-this")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))  # 24시간
    
    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, str]:
        """비밀번호 강도 검증"""
        if len(password) < 8:
            return False, "비밀번호는 8자 이상이어야 합니다"
        
        if not any(c.islower() for c in password):
            return False, "비밀번호에 소문자가 포함되어야 합니다"
        
        if not any(c.isupper() for c in password):
            return False, "비밀번호에 대문자가 포함되어야 합니다"
        
        if not any(c.isdigit() for c in password):
            return False, "비밀번호에 숫자가 포함되어야 합니다"
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "비밀번호에 특수문자가 포함되어야 합니다"
        
        return True, "유효한 비밀번호입니다"
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """비밀번호 해싱"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @classmethod
    def verify_password(cls, password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @classmethod
    async def register_user(cls, username: str, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        사용자 등록 - 간소화 (API 키 저장 제거)
        Returns: (success, message, user_data)
        """
        try:
            async with get_mysql_session() as session:
                # 중복 확인
                existing_user = await session.execute(
                    select(User).where(
                        (User.username == username) | (User.email == email)
                    )
                )
                if existing_user.scalar_one_or_none():
                    return False, "이미 존재하는 사용자명 또는 이메일입니다", None
                
                # 비밀번호 강도 검증
                is_valid, msg = cls.validate_password_strength(password)
                if not is_valid:
                    return False, msg, None
                
                # 새 사용자 생성 (API 키 없이)
                password_hash = cls.hash_password(password)
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=password_hash
                )
                
                session.add(new_user)
                await session.commit()
                
                logger.info(f"✅ 사용자 등록 완료 (보안 강화): {username}")
                return True, "회원가입이 완료되었습니다", new_user.to_dict()
                
        except Exception as e:
            logger.error(f"❌ 사용자 등록 실패: {str(e)}")
            return False, f"회원가입 중 오류가 발생했습니다: {str(e)}", None
    
    @classmethod
    async def authenticate_user(cls, username_or_email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        사용자 인증
        Returns: (success, message, user_data)
        """
        try:
            async with get_mysql_session() as session:
                # 사용자 조회 (username 또는 email)
                result = await session.execute(
                    select(User).where(
                        (User.username == username_or_email) | (User.email == username_or_email)
                    ).where(User.is_active == True)
                )
                
                user = result.scalar_one_or_none()
                if not user:
                    return False, "존재하지 않는 사용자입니다", None
                
                # 비밀번호 검증
                if not cls.verify_password(password, user.password_hash):
                    return False, "비밀번호가 틀렸습니다", None
                
                # 최종 로그인 시간 업데이트
                user.last_login = datetime.utcnow()
                await session.commit()
                
                logger.info(f"✅ 사용자 인증 성공: {user.username}")
                return True, "로그인 성공", user.to_dict()
                
        except Exception as e:
            logger.error(f"❌ 사용자 인증 실패: {str(e)}")
            return False, f"로그인 중 오류가 발생했습니다: {str(e)}", None
    
    @classmethod
    async def create_session(cls, user_id: int, remember_me: bool = False) -> Tuple[bool, str, Optional[str]]:
        """
        사용자 세션 생성 - JWT 토큰만 사용 (DB 저장 제거)
        Args:
            user_id: 사용자 ID
            remember_me: 로그인 유지 옵션 (True시 7일, False시 24시간)
        Returns: (success, message, session_token)
        """
        try:
            # 로그인 유지 옵션에 따른 만료 시간 설정
            if remember_me:
                expire_hours = 7 * 24  # 7일
                logger.info(f"🔒 로그인 유지 모드: user_id={user_id}, 7일간 유지")
            else:
                expire_hours = cls.JWT_EXPIRE_HOURS  # 24시간 (기본값)
                logger.info(f"🔒 일반 로그인 모드: user_id={user_id}, 24시간 유지")
            
            # JWT 토큰 생성 (동적 만료 시간 + 서버 시작 시간)
            payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(hours=expire_hours),
                'iat': datetime.utcnow(),
                'remember_me': remember_me,
                'server_start_time': SERVER_START_TIME  # 🚀 서버 재시작 감지용
            }
            
            token = jwt.encode(payload, cls.JWT_SECRET_KEY, algorithm=cls.JWT_ALGORITHM)
            
            logger.info(f"✅ JWT 토큰 생성 완료: user_id={user_id}, 만료시간={expire_hours}시간")
            return True, "세션 생성 완료", token
            
        except Exception as e:
            logger.error(f"❌ 세션 생성 실패: {str(e)}")
            return False, f"세션 생성 중 오류가 발생했습니다: {str(e)}", None
    
    @classmethod
    async def verify_session(cls, token: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        세션 검증
        Returns: (success, message, user_data)
        """
        try:
            # JWT 토큰 검증
            payload = jwt.decode(token, cls.JWT_SECRET_KEY, algorithms=[cls.JWT_ALGORITHM])
            user_id = payload.get('user_id')
            token_server_start_time = payload.get('server_start_time')
            
            if not user_id:
                return False, "유효하지 않은 토큰입니다", None
            
            # 🚀 서버 재시작 감지 활성화 - 재시작 시 모든 토큰 무효화
            if token_server_start_time and token_server_start_time != SERVER_START_TIME:
                logger.warning(f"⚠️ 서버 재시작으로 인한 토큰 무효화: user_id={user_id}")
                return False, "서버가 재시작되어 다시 로그인해주세요", None
            
            async with get_mysql_session() as session:
                # 사용자 정보 조회
                result = await session.execute(
                    select(User).where(User.id == user_id).where(User.is_active == True)
                )
                
                user = result.scalar_one_or_none()
                if not user:
                    return False, "존재하지 않는 사용자입니다", None
                
                return True, "유효한 세션입니다", user.to_dict()
                
        except jwt.ExpiredSignatureError:
            return False, "세션이 만료되었습니다", None
        except jwt.InvalidTokenError:
            return False, "유효하지 않은 토큰입니다", None
        except Exception as e:
            logger.error(f"❌ 세션 검증 실패: {str(e)}")
            return False, f"세션 검증 중 오류가 발생했습니다: {str(e)}", None
    
    @classmethod
    async def refresh_token(cls, current_token: str) -> Tuple[bool, str, Optional[str], bool]:
        """
        토큰 갱신 - 기존 토큰의 remember_me 설정 유지
        Returns: (success, message, new_token, remember_me)
        """
        try:
            # 현재 토큰 검증 및 정보 추출
            success, message, user_data = await cls.verify_session(current_token)
            
            if not success or not user_data:
                return False, "유효하지 않은 토큰입니다", None, False
            
            # 기존 토큰에서 remember_me 설정 추출
            try:
                payload = jwt.decode(current_token, cls.JWT_SECRET_KEY, algorithms=[cls.JWT_ALGORITHM])
                remember_me = payload.get('remember_me', False)
            except:
                remember_me = False  # 기본값
            
            # 새 토큰 생성 (기존 설정 유지)
            new_success, new_message, new_token = await cls.create_session(
                user_data['id'], 
                remember_me=remember_me
            )
            
            if new_success and new_token:
                logger.info(f"🔄 토큰 갱신 완료: user_id={user_data['id']}, remember_me={remember_me}")
                return True, "토큰 갱신 완료", new_token, remember_me
            else:
                return False, new_message, None, remember_me
            
        except jwt.ExpiredSignatureError:
            logger.warning("만료된 토큰으로 갱신 요청됨")
            return False, "토큰이 만료되어 갱신할 수 없습니다", None, False
        except Exception as e:
            logger.error(f"❌ 토큰 갱신 실패: {str(e)}")
            return False, f"토큰 갱신 중 오류가 발생했습니다: {str(e)}", None, False
    
    @classmethod
    async def logout_user(cls, token: str) -> Tuple[bool, str]:
        """
        사용자 로그아웃 - JWT 기반으로 간소화 (클라이언트측 토큰 삭제)
        Returns: (success, message)
        """
        try:
            # JWT는 stateless이므로 서버측에서는 로그아웃 처리가 간단
            # 클라이언트에서 토큰을 삭제하면 됨
            logger.info("✅ 로그아웃 요청 처리 완료")
            return True, "로그아웃 완료"
            
        except Exception as e:
            logger.error(f"❌ 로그아웃 실패: {str(e)}")
            # 로그아웃은 실패해도 성공으로 처리 (보안상)
            return True, "로그아웃 완료"
    
    # API 키 관련 메서드들 제거됨 - 보안 강화를 위해 API 키 저장하지 않음
    
    @classmethod
    async def change_password(cls, user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        비밀번호 변경
        Args:
            user_id: 사용자 ID
            current_password: 현재 비밀번호
            new_password: 새 비밀번호
        Returns:
            (success, message)
        """
        try:
            async with get_mysql_session() as session:
                # 사용자 정보 조회
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False, "사용자를 찾을 수 없습니다"
                
                # 현재 비밀번호 검증
                if not bcrypt.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    return False, "현재 비밀번호가 올바르지 않습니다"
                
                # 새 비밀번호 강도 검증
                is_strong, message = cls.validate_password_strength(new_password)
                if not is_strong:
                    return False, message
                
                # 현재 비밀번호와 새 비밀번호가 같은지 확인
                if bcrypt.checkpw(new_password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    return False, "새 비밀번호는 현재 비밀번호와 달라야 합니다"
                
                # 새 비밀번호 해시화
                new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # 비밀번호 업데이트
                user.password_hash = new_password_hash
                user.updated_at = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"✅ 비밀번호 변경 완료: user_id={user_id}, username={user.username}")
                return True, "비밀번호가 성공적으로 변경되었습니다"
                
        except Exception as e:
            logger.error(f"❌ 비밀번호 변경 실패: {str(e)}")
            return False, f"비밀번호 변경 중 오류가 발생했습니다: {str(e)}"