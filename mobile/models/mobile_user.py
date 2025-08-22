"""
📱 모바일 사용자 데이터 모델

⚠️ 기존 시스템과 완전히 분리된 모바일 전용 사용자 모델입니다.
Flutter 앱과의 호환성을 고려하여 설계되었습니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class MobileUser(BaseModel):
    """모바일 사용자 정보 모델"""
    
    user_id: str = Field(..., description="사용자 고유 ID")
    username: str = Field(..., description="사용자명")
    email: Optional[str] = Field(None, description="이메일 주소")
    is_active: bool = Field(True, description="계정 활성화 상태")
    created_at: str = Field(..., description="계정 생성일 (ISO format)")
    last_login: Optional[str] = Field(None, description="마지막 로그인 시간 (ISO format)")
    
    # 모바일 전용 설정
    mobile_settings: Dict[str, Any] = Field(default_factory=dict, description="모바일 앱 설정")
    push_notification: bool = Field(True, description="푸시 알림 허용 여부")
    biometric_enabled: bool = Field(False, description="생체 인증 사용 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_12345",
                "username": "trader_kim",
                "email": "kim@example.com",
                "is_active": True,
                "created_at": "2024-01-15T09:30:00Z",
                "last_login": "2024-01-20T14:25:30Z",
                "mobile_settings": {
                    "theme": "dark",
                    "language": "ko",
                    "currency": "KRW"
                },
                "push_notification": True,
                "biometric_enabled": False
            }
        }

class MobileAuthRequest(BaseModel):
    """모바일 인증 요청 모델"""
    
    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    password: str = Field(..., min_length=6, description="비밀번호")
    device_id: str = Field(..., description="기기 고유 ID")
    device_name: str = Field(..., description="기기명")
    app_version: str = Field(..., description="앱 버전")
    
    # 생체 인증 관련 (선택적)
    biometric_token: Optional[str] = Field(None, description="생체 인증 토큰")
    remember_me: bool = Field(False, description="자동 로그인 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "trader_kim",
                "password": "secure_password123",
                "device_id": "iPhone_12_ABC123",
                "device_name": "Kim의 iPhone",
                "app_version": "1.0.0",
                "biometric_token": None,
                "remember_me": True
            }
        }

class MobileAuthResponse(BaseModel):
    """모바일 인증 응답 모델"""
    
    success: bool = Field(..., description="인증 성공 여부")
    access_token: Optional[str] = Field(None, description="JWT 액세스 토큰")
    refresh_token: Optional[str] = Field(None, description="리프레시 토큰")
    token_type: str = Field("bearer", description="토큰 타입")
    expires_in: Optional[int] = Field(None, description="토큰 만료시간 (초)")
    
    # 사용자 정보
    user: Optional[MobileUser] = Field(None, description="사용자 정보")
    
    # 권한 정보
    permissions: list[str] = Field(default_factory=list, description="사용자 권한 목록")
    
    # 에러 정보 (인증 실패시)
    error: Optional[str] = Field(None, description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "refresh_token_here",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "user_id": "user_12345",
                    "username": "trader_kim",
                    "email": "kim@example.com",
                    "is_active": True,
                    "created_at": "2024-01-15T09:30:00Z",
                    "last_login": "2024-01-20T14:25:30Z"
                },
                "permissions": ["trading:read", "portfolio:read", "trading:write"],
                "error": None,
                "error_code": None
            }
        }

class MobileDeviceInfo(BaseModel):
    """모바일 기기 정보 모델"""
    
    device_id: str = Field(..., description="기기 고유 ID")
    device_name: str = Field(..., description="기기명")
    platform: str = Field(..., description="플랫폼 (iOS/Android)")
    os_version: str = Field(..., description="OS 버전")
    app_version: str = Field(..., description="앱 버전")
    
    # 푸시 알림 관련
    fcm_token: Optional[str] = Field(None, description="Firebase Cloud Messaging 토큰")
    push_enabled: bool = Field(True, description="푸시 알림 활성화 여부")
    
    # 등록 정보
    registered_at: str = Field(..., description="기기 등록 시간 (ISO format)")
    last_active: str = Field(..., description="마지막 활성화 시간 (ISO format)")
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "iPhone_12_ABC123",
                "device_name": "Kim의 iPhone",
                "platform": "iOS",
                "os_version": "17.2.1",
                "app_version": "1.0.0",
                "fcm_token": "fcm_token_here",
                "push_enabled": True,
                "registered_at": "2024-01-15T09:30:00Z",
                "last_active": "2024-01-20T14:25:30Z"
            }
        }

class MobileSessionInfo(BaseModel):
    """모바일 세션 정보 모델"""
    
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    device_id: str = Field(..., description="기기 ID")
    
    # 세션 상태
    is_active: bool = Field(True, description="세션 활성화 상태")
    created_at: str = Field(..., description="세션 생성 시간 (ISO format)")
    expires_at: str = Field(..., description="세션 만료 시간 (ISO format)")
    last_activity: str = Field(..., description="마지막 활동 시간 (ISO format)")
    
    # 세션 메타데이터
    ip_address: Optional[str] = Field(None, description="IP 주소")
    location: Optional[str] = Field(None, description="접속 위치")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "user_id": "user_12345",
                "device_id": "iPhone_12_ABC123",
                "is_active": True,
                "created_at": "2024-01-20T14:25:30Z",
                "expires_at": "2024-01-20T18:25:30Z",
                "last_activity": "2024-01-20T15:10:45Z",
                "ip_address": "192.168.1.100",
                "location": "Seoul, KR"
            }
        }