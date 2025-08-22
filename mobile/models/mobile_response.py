"""
📱 모바일 API 응답 모델

⚠️ 모바일 앱과의 일관된 통신을 위한 표준 응답 형식입니다.
Flutter 앱에서 쉽게 처리할 수 있도록 설계되었습니다.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum

# Generic type for response data
T = TypeVar('T')

class ResponseStatus(str, Enum):
    """응답 상태"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ErrorCode(str, Enum):
    """에러 코드"""
    # 인증 관련
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_003"
    AUTH_DEVICE_NOT_REGISTERED = "AUTH_004"
    
    # 거래 관련
    TRADING_SYSTEM_NOT_RUNNING = "TRADING_001"
    TRADING_INSUFFICIENT_BALANCE = "TRADING_002"
    TRADING_POSITION_LIMIT_EXCEEDED = "TRADING_003"
    TRADING_INVALID_SYMBOL = "TRADING_004"
    TRADING_MARKET_CLOSED = "TRADING_005"
    
    # 시스템 관련
    SYSTEM_MAINTENANCE = "SYSTEM_001"
    SYSTEM_OVERLOAD = "SYSTEM_002"
    SYSTEM_API_LIMIT_EXCEEDED = "SYSTEM_003"
    SYSTEM_DATABASE_ERROR = "SYSTEM_004"
    
    # 데이터 관련
    DATA_NOT_FOUND = "DATA_001"
    DATA_INVALID_FORMAT = "DATA_002"
    DATA_OUTDATED = "DATA_003"
    
    # 일반 에러
    UNKNOWN_ERROR = "UNKNOWN_001"
    VALIDATION_ERROR = "VALIDATION_001"
    NETWORK_ERROR = "NETWORK_001"

class MobileResponse(BaseModel, Generic[T]):
    """기본 모바일 API 응답 모델"""
    
    # 응답 메타데이터
    status: ResponseStatus = Field(..., description="응답 상태")
    message: str = Field(..., description="응답 메시지")
    timestamp: str = Field(..., description="응답 시간 (ISO format)")
    
    # 응답 데이터
    data: Optional[T] = Field(None, description="응답 데이터")
    
    # 추가 메타 정보
    request_id: Optional[str] = Field(None, description="요청 ID")
    version: str = Field("v1", description="API 버전")
    
    # 성능 정보
    processing_time: Optional[float] = Field(None, description="처리 시간 (ms)")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """현재 시간으로 타임스탬프 설정"""
        if v is None:
            return datetime.utcnow().isoformat()
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "요청이 성공적으로 처리되었습니다",
                "timestamp": "2024-01-20T15:10:45Z",
                "data": {},
                "request_id": "req_12345",
                "version": "v1",
                "processing_time": 150.5
            }
        }

class MobileErrorResponse(BaseModel):
    """모바일 에러 응답 모델"""
    
    # 기본 응답 정보
    status: ResponseStatus = Field(ResponseStatus.ERROR, description="응답 상태")
    message: str = Field(..., description="에러 메시지")
    timestamp: str = Field(..., description="응답 시간 (ISO format)")
    
    # 에러 상세 정보
    error_code: ErrorCode = Field(..., description="에러 코드")
    error_details: Optional[str] = Field(None, description="에러 상세 설명")
    
    # 디버깅 정보 (개발 환경에서만)
    debug_info: Optional[Dict[str, Any]] = Field(None, description="디버깅 정보")
    stack_trace: Optional[str] = Field(None, description="스택 트레이스")
    
    # 사용자 액션
    user_action: Optional[str] = Field(None, description="사용자가 취할 수 있는 액션")
    retry_after: Optional[int] = Field(None, description="재시도 가능 시간 (초)")
    
    # 요청 정보
    request_id: Optional[str] = Field(None, description="요청 ID")
    version: str = Field("v1", description="API 버전")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """현재 시간으로 타임스탬프 설정"""
        if v is None:
            return datetime.utcnow().isoformat()
        return v
    
    @validator('user_action', always=True)
    def set_user_action(cls, v, values):
        """에러 코드에 따른 사용자 액션 설정"""
        if v is not None:
            return v
            
        error_code = values.get('error_code')
        actions = {
            ErrorCode.AUTH_TOKEN_EXPIRED: "다시 로그인해주세요",
            ErrorCode.AUTH_INVALID_CREDENTIALS: "아이디와 비밀번호를 확인해주세요",
            ErrorCode.TRADING_INSUFFICIENT_BALANCE: "잔고를 확인해주세요",
            ErrorCode.TRADING_SYSTEM_NOT_RUNNING: "거래 시스템을 시작해주세요",
            ErrorCode.NETWORK_ERROR: "네트워크 연결을 확인해주세요",
            ErrorCode.SYSTEM_MAINTENANCE: "잠시 후 다시 시도해주세요"
        }
        return actions.get(error_code, "고객센터에 문의해주세요")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "인증 토큰이 만료되었습니다",
                "timestamp": "2024-01-20T15:10:45Z",
                "error_code": "AUTH_002",
                "error_details": "JWT 토큰의 유효기간이 지났습니다",
                "debug_info": None,
                "stack_trace": None,
                "user_action": "다시 로그인해주세요",
                "retry_after": None,
                "request_id": "req_12345",
                "version": "v1"
            }
        }

class MobilePaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 지원 모바일 응답 모델"""
    
    # 기본 응답 정보
    status: ResponseStatus = Field(ResponseStatus.SUCCESS, description="응답 상태")
    message: str = Field("요청이 성공적으로 처리되었습니다", description="응답 메시지")
    timestamp: str = Field(..., description="응답 시간 (ISO format)")
    
    # 페이지네이션 데이터
    data: List[T] = Field(..., description="응답 데이터 목록")
    
    # 페이지네이션 메타 정보
    pagination: Dict[str, Any] = Field(..., description="페이지네이션 정보")
    
    # 요청 정보
    request_id: Optional[str] = Field(None, description="요청 ID")
    version: str = Field("v1", description="API 버전")
    processing_time: Optional[float] = Field(None, description="처리 시간 (ms)")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """현재 시간으로 타임스탬프 설정"""
        if v is None:
            return datetime.utcnow().isoformat()
        return v
    
    @validator('pagination', always=True)
    def validate_pagination(cls, v, values):
        """페이지네이션 정보 유효성 검사"""
        if not isinstance(v, dict):
            return v
            
        required_fields = ['page', 'per_page', 'total', 'total_pages']
        for field in required_fields:
            if field not in v:
                v[field] = 0
                
        # has_next, has_prev 자동 계산
        v['has_next'] = v['page'] < v['total_pages']
        v['has_prev'] = v['page'] > 1
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "거래 내역을 성공적으로 조회했습니다",
                "timestamp": "2024-01-20T15:10:45Z",
                "data": [],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 156,
                    "total_pages": 8,
                    "has_next": True,
                    "has_prev": False
                },
                "request_id": "req_12345",
                "version": "v1",
                "processing_time": 125.3
            }
        }

class MobileWebSocketMessage(BaseModel):
    """모바일 WebSocket 메시지 모델"""
    
    # 메시지 타입
    type: str = Field(..., description="메시지 타입 (heartbeat/data/error)")
    channel: str = Field(..., description="채널명")
    
    # 메시지 데이터
    data: Optional[Dict[str, Any]] = Field(None, description="메시지 데이터")
    
    # 메타 정보
    timestamp: str = Field(..., description="메시지 시간 (ISO format)")
    sequence: Optional[int] = Field(None, description="시퀀스 번호")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """현재 시간으로 타임스탬프 설정"""
        if v is None:
            return datetime.utcnow().isoformat()
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "type": "data",
                "channel": "trading_status",
                "data": {
                    "is_running": True,
                    "position_count": 3,
                    "total_profit_loss": 125000.0
                },
                "timestamp": "2024-01-20T15:10:45Z",
                "sequence": 12345
            }
        }

class MobileHealthResponse(BaseModel):
    """모바일 시스템 상태 응답 모델"""
    
    # 기본 상태 정보
    status: ResponseStatus = Field(..., description="시스템 상태")
    timestamp: str = Field(..., description="확인 시간 (ISO format)")
    
    # 시스템 구성요소 상태
    components: Dict[str, Dict[str, Any]] = Field(..., description="구성요소별 상태")
    
    # 성능 지표
    performance: Dict[str, float] = Field(..., description="성능 지표")
    
    # 전체 상태
    healthy: bool = Field(..., description="전체 시스템 정상 여부")
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """현재 시간으로 타임스탬프 설정"""
        if v is None:
            return datetime.utcnow().isoformat()
        return v
    
    @validator('healthy', always=True)
    def calculate_healthy(cls, v, values):
        """구성요소 상태로부터 전체 상태 계산"""
        components = values.get('components', {})
        if not components:
            return False
            
        for component_status in components.values():
            if not component_status.get('healthy', False):
                return False
        return True
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "timestamp": "2024-01-20T15:10:45Z",
                "components": {
                    "api_server": {
                        "healthy": True,
                        "status": "running",
                        "response_time": 45.2
                    },
                    "trading_engine": {
                        "healthy": True,
                        "status": "active",
                        "last_update": "2024-01-20T15:10:30Z"
                    },
                    "database": {
                        "healthy": True,
                        "status": "connected",
                        "connection_pool": 8
                    }
                },
                "performance": {
                    "cpu_usage": 15.3,
                    "memory_usage": 42.7,
                    "response_time": 125.5
                },
                "healthy": True
            }
        }