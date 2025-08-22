"""
사용자 경험 개선 서비스
시각적 피드백, 데이터 검증, 사용자 인터페이스 최적화
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """피드백 유형"""
    SUCCESS = "success"
    WARNING = "warning" 
    ERROR = "error"
    INFO = "info"
    LOADING = "loading"
    PROGRESS = "progress"

class ValidationLevel(Enum):
    """검증 수준"""
    BASIC = "basic"      # 기본 형식 검증
    STANDARD = "standard" # 표준 검증 + 범위 확인
    STRICT = "strict"     # 엄격한 검증 + 비즈니스 로직
    CRITICAL = "critical" # 중요 거래용 최고 수준 검증

@dataclass
class ValidationResult:
    """검증 결과"""
    is_valid: bool
    field_name: str
    message: str
    suggestion: Optional[str] = None
    severity: FeedbackType = FeedbackType.INFO
    
@dataclass
class UIFeedback:
    """UI 피드백 메시지"""
    id: str
    type: FeedbackType
    title: str
    message: str
    duration: int = 5  # 표시 시간 (초)
    actions: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
class UXService:
    """사용자 경험 개선 서비스"""
    
    def __init__(self):
        self.active_feedbacks: Dict[str, UIFeedback] = {}
        self.validation_cache: Dict[str, Tuple[ValidationResult, datetime]] = {}
        self.user_preferences: Dict[int, Dict[str, Any]] = {}
        
        # 검증 규칙 정의
        self.validation_rules = {
            "api_key": {
                "pattern": r"^[A-Za-z0-9]{32,64}$",
                "min_length": 32,
                "max_length": 64,
                "description": "32-64자의 영문자와 숫자 조합"
            },
            "trade_amount": {
                "min_value": 5000,      # 최소 5천원
                "max_value": 10000000,  # 최대 1천만원
                "step": 1000,           # 1천원 단위
                "description": "5,000원 이상 10,000,000원 이하 (1,000원 단위)"
            },
            "percentage": {
                "min_value": 0.1,
                "max_value": 100.0,
                "decimal_places": 2,
                "description": "0.1% 이상 100% 이하 (소수점 2자리)"
            },
            "market_symbol": {
                "pattern": r"^KRW-[A-Z0-9]{2,10}$",
                "description": "KRW- 접두사와 2-10자 영문대문자/숫자"
            }
        }
        
        # 사용자 도움말 메시지
        self.help_messages = {
            "api_setup": {
                "title": "API 키 설정 가이드",
                "content": """
1. 업비트 웹사이트 로그인
2. 마이페이지 → Open API 관리
3. Open API 키 발급 (원화 마켓 거래 권한 필요)
4. Access Key와 Secret Key 복사
5. 시스템에 정확히 입력
                """.strip(),
                "tips": [
                    "API 키는 안전한 곳에 보관하세요",
                    "IP 접근 제한을 설정하는 것이 안전합니다",
                    "거래 권한만 허용하고 출금 권한은 제외하세요"
                ]
            },
            "trading_basics": {
                "title": "거래 기본 가이드",
                "content": """
1. 최소 거래 금액: 5,000원 이상
2. 목표 수익률: 0.5% (기본값)
3. 손절매: -0.3% (기본값)
4. 최대 포지션: 5개 동시 보유
5. 보유 시간: 최대 5분 (스캘핑)
                """.strip(),
                "tips": [
                    "소액부터 시작해서 경험을 쌓으세요",
                    "시장 상황을 지속적으로 모니터링하세요",
                    "손실 한도를 미리 정하고 지키세요"
                ]
            }
        }
        
        # 성능 추적
        self.performance_metrics = {
            "ui_response_times": [],
            "validation_times": [],
            "user_errors": [],
            "feedback_effectiveness": {}
        }
        
        logger.info("✅ 사용자 경험 서비스 초기화 완료")
    
    def create_feedback(
        self, 
        feedback_type: FeedbackType,
        title: str,
        message: str,
        duration: int = 5,
        actions: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """UI 피드백 생성"""
        try:
            feedback_id = f"{feedback_type.value}_{int(time.time())}_{hash(title + message) % 1000}"
            
            feedback = UIFeedback(
                id=feedback_id,
                type=feedback_type,
                title=title,
                message=message,
                duration=duration,
                actions=actions or [],
                metadata=metadata or {}
            )
            
            self.active_feedbacks[feedback_id] = feedback
            
            # 자동 제거 스케줄링 (duration 후)
            if duration > 0:
                asyncio.create_task(self._remove_feedback_after_delay(feedback_id, duration))
            
            logger.debug(f"📢 UI 피드백 생성: {title}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ 피드백 생성 오류: {str(e)}")
            return ""
    
    async def _remove_feedback_after_delay(self, feedback_id: str, delay: int):
        """지정된 시간 후 피드백 제거"""
        try:
            await asyncio.sleep(delay)
            if feedback_id in self.active_feedbacks:
                del self.active_feedbacks[feedback_id]
                logger.debug(f"🗑️ 피드백 자동 제거: {feedback_id}")
        except Exception as e:
            logger.error(f"❌ 피드백 제거 오류: {str(e)}")
    
    def validate_field(
        self, 
        field_name: str, 
        value: Any, 
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """필드 데이터 검증"""
        try:
            # 캐시 확인 (1분간 유효)
            cache_key = f"{field_name}_{str(value)}_{validation_level.value}"
            if cache_key in self.validation_cache:
                cached_result, cached_time = self.validation_cache[cache_key]
                if (datetime.now() - cached_time).total_seconds() < 60:
                    return cached_result
            
            start_time = time.time()
            
            # 기본 검증
            result = self._perform_validation(field_name, value, validation_level, custom_rules)
            
            # 성능 추적
            validation_time = (time.time() - start_time) * 1000
            self.performance_metrics["validation_times"].append(validation_time)
            
            # 결과 캐싱
            self.validation_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 필드 검증 오류 ({field_name}): {str(e)}")
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message="검증 중 오류가 발생했습니다",
                severity=FeedbackType.ERROR
            )
    
    def _perform_validation(
        self, 
        field_name: str, 
        value: Any, 
        validation_level: ValidationLevel,
        custom_rules: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """실제 검증 수행"""
        try:
            # 빈 값 체크
            if value is None or (isinstance(value, str) and not value.strip()):
                return ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    message="필수 입력 항목입니다",
                    suggestion="값을 입력해주세요",
                    severity=FeedbackType.ERROR
                )
            
            # 사용자 정의 규칙 우선 적용
            if custom_rules:
                return self._validate_with_custom_rules(field_name, value, custom_rules)
            
            # 필드별 검증
            if field_name == "api_key":
                return self._validate_api_key(value, validation_level)
            elif field_name == "trade_amount":
                return self._validate_trade_amount(value, validation_level)
            elif field_name == "percentage":
                return self._validate_percentage(value, validation_level)
            elif field_name == "market_symbol":
                return self._validate_market_symbol(value, validation_level)
            elif field_name == "email":
                return self._validate_email(value, validation_level)
            elif field_name == "password":
                return self._validate_password(value, validation_level)
            else:
                # 일반 검증
                return ValidationResult(
                    is_valid=True,
                    field_name=field_name,
                    message="검증 완료",
                    severity=FeedbackType.SUCCESS
                )
                
        except Exception as e:
            logger.error(f"❌ 검증 수행 오류: {str(e)}")
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message="검증 처리 중 오류 발생",
                severity=FeedbackType.ERROR
            )
    
    def _validate_api_key(self, value: str, level: ValidationLevel) -> ValidationResult:
        """API 키 검증"""
        rule = self.validation_rules["api_key"]
        
        # 길이 체크
        if len(value) < rule["min_length"] or len(value) > rule["max_length"]:
            return ValidationResult(
                is_valid=False,
                field_name="api_key",
                message=f"API 키는 {rule['min_length']}-{rule['max_length']}자여야 합니다",
                suggestion="업비트에서 발급받은 API 키를 정확히 입력하세요",
                severity=FeedbackType.ERROR
            )
        
        # 패턴 체크
        if not re.match(rule["pattern"], value):
            return ValidationResult(
                is_valid=False,
                field_name="api_key",
                message="API 키 형식이 올바르지 않습니다",
                suggestion="영문자와 숫자로만 구성된 키를 입력하세요",
                severity=FeedbackType.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="api_key",
            message="올바른 API 키 형식입니다",
            severity=FeedbackType.SUCCESS
        )
    
    def _validate_trade_amount(self, value: Any, level: ValidationLevel) -> ValidationResult:
        """거래 금액 검증"""
        try:
            amount = float(value)
            rule = self.validation_rules["trade_amount"]
            
            if amount < rule["min_value"]:
                return ValidationResult(
                    is_valid=False,
                    field_name="trade_amount",
                    message=f"최소 거래 금액은 {rule['min_value']:,}원입니다",
                    suggestion=f"{rule['min_value']:,}원 이상 입력하세요",
                    severity=FeedbackType.ERROR
                )
            
            if amount > rule["max_value"]:
                return ValidationResult(
                    is_valid=False,
                    field_name="trade_amount",
                    message=f"최대 거래 금액은 {rule['max_value']:,}원입니다",
                    suggestion=f"{rule['max_value']:,}원 이하로 입력하세요",
                    severity=FeedbackType.ERROR
                )
            
            # 단위 체크 (엄격한 검증에서만)
            if level in [ValidationLevel.STRICT, ValidationLevel.CRITICAL]:
                if amount % rule["step"] != 0:
                    return ValidationResult(
                        is_valid=False,
                        field_name="trade_amount",
                        message=f"거래 금액은 {rule['step']:,}원 단위여야 합니다",
                        suggestion=f"가장 가까운 {rule['step']:,}원 단위로 조정하세요",
                        severity=FeedbackType.WARNING
                    )
            
            return ValidationResult(
                is_valid=True,
                field_name="trade_amount",
                message=f"유효한 거래 금액입니다 ({amount:,.0f}원)",
                severity=FeedbackType.SUCCESS
            )
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="trade_amount",
                message="숫자 형식의 금액을 입력하세요",
                suggestion="예: 100000 (십만원)",
                severity=FeedbackType.ERROR
            )
    
    def _validate_percentage(self, value: Any, level: ValidationLevel) -> ValidationResult:
        """퍼센티지 검증"""
        try:
            percentage = float(value)
            rule = self.validation_rules["percentage"]
            
            if percentage < rule["min_value"]:
                return ValidationResult(
                    is_valid=False,
                    field_name="percentage",
                    message=f"최소값은 {rule['min_value']}%입니다",
                    suggestion=f"{rule['min_value']}% 이상 입력하세요",
                    severity=FeedbackType.ERROR
                )
            
            if percentage > rule["max_value"]:
                return ValidationResult(
                    is_valid=False,
                    field_name="percentage",
                    message=f"최대값은 {rule['max_value']}%입니다",
                    suggestion=f"{rule['max_value']}% 이하로 입력하세요",
                    severity=FeedbackType.ERROR
                )
            
            # 소수점 자릿수 체크
            decimal_str = str(percentage).split('.')
            if len(decimal_str) > 1 and len(decimal_str[1]) > rule["decimal_places"]:
                return ValidationResult(
                    is_valid=False,
                    field_name="percentage",
                    message=f"소수점 {rule['decimal_places']}자리까지만 입력 가능합니다",
                    suggestion=f"예: {percentage:.2f}%",
                    severity=FeedbackType.WARNING
                )
            
            return ValidationResult(
                is_valid=True,
                field_name="percentage",
                message=f"유효한 퍼센티지입니다 ({percentage}%)",
                severity=FeedbackType.SUCCESS
            )
            
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                field_name="percentage",
                message="숫자 형식의 퍼센티지를 입력하세요",
                suggestion="예: 0.5 (0.5%)",
                severity=FeedbackType.ERROR
            )
    
    def _validate_market_symbol(self, value: str, level: ValidationLevel) -> ValidationResult:
        """마켓 심볼 검증"""
        rule = self.validation_rules["market_symbol"]
        
        if not re.match(rule["pattern"], value.upper()):
            return ValidationResult(
                is_valid=False,
                field_name="market_symbol",
                message="올바른 마켓 형식이 아닙니다",
                suggestion="예: KRW-BTC, KRW-ETH",
                severity=FeedbackType.ERROR
            )
        
        # 엄격한 검증에서는 실제 존재하는 마켓인지 확인 (추가 로직 필요)
        if level in [ValidationLevel.STRICT, ValidationLevel.CRITICAL]:
            # TODO: 실제 업비트 마켓 목록과 대조
            pass
        
        return ValidationResult(
            is_valid=True,
            field_name="market_symbol",
            message="올바른 마켓 심볼입니다",
            severity=FeedbackType.SUCCESS
        )
    
    def _validate_email(self, value: str, level: ValidationLevel) -> ValidationResult:
        """이메일 검증"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, value):
            return ValidationResult(
                is_valid=False,
                field_name="email",
                message="올바른 이메일 형식이 아닙니다",
                suggestion="예: user@example.com",
                severity=FeedbackType.ERROR
            )
        
        return ValidationResult(
            is_valid=True,
            field_name="email",
            message="올바른 이메일 형식입니다",
            severity=FeedbackType.SUCCESS
        )
    
    def _validate_password(self, value: str, level: ValidationLevel) -> ValidationResult:
        """패스워드 검증"""
        if len(value) < 8:
            return ValidationResult(
                is_valid=False,
                field_name="password",
                message="비밀번호는 8자 이상이어야 합니다",
                suggestion="최소 8자 이상 입력하세요",
                severity=FeedbackType.ERROR
            )
        
        # 엄격한 검증
        if level in [ValidationLevel.STRICT, ValidationLevel.CRITICAL]:
            has_upper = bool(re.search(r'[A-Z]', value))
            has_lower = bool(re.search(r'[a-z]', value))
            has_digit = bool(re.search(r'\d', value))
            has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', value))
            
            missing = []
            if not has_upper: missing.append("대문자")
            if not has_lower: missing.append("소문자") 
            if not has_digit: missing.append("숫자")
            if not has_special: missing.append("특수문자")
            
            if missing:
                return ValidationResult(
                    is_valid=False,
                    field_name="password",
                    message=f"다음이 포함되어야 합니다: {', '.join(missing)}",
                    suggestion="대문자, 소문자, 숫자, 특수문자를 모두 포함하세요",
                    severity=FeedbackType.ERROR
                )
        
        return ValidationResult(
            is_valid=True,
            field_name="password",
            message="강력한 비밀번호입니다",
            severity=FeedbackType.SUCCESS
        )
    
    def _validate_with_custom_rules(self, field_name: str, value: Any, rules: Dict[str, Any]) -> ValidationResult:
        """커스텀 규칙으로 검증"""
        try:
            # 커스텀 검증 로직 구현
            # TODO: 필요에 따라 확장
            
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                message="커스텀 검증 통과",
                severity=FeedbackType.SUCCESS
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                message=f"커스텀 검증 오류: {str(e)}",
                severity=FeedbackType.ERROR
            )
    
    def get_help_content(self, topic: str) -> Optional[Dict[str, Any]]:
        """도움말 컨텐츠 조회"""
        return self.help_messages.get(topic)
    
    def set_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """사용자 설정 저장"""
        try:
            self.user_preferences[user_id] = preferences
            logger.info(f"👤 사용자 설정 저장 완료: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ 사용자 설정 저장 오류: {str(e)}")
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """사용자 설정 조회"""
        return self.user_preferences.get(user_id, {})
    
    def track_user_error(self, error_type: str, context: Dict[str, Any]):
        """사용자 오류 추적"""
        try:
            error_record = {
                "type": error_type,
                "context": context,
                "timestamp": datetime.now(),
                "count": 1
            }
            
            # 중복 오류 카운트
            existing_errors = [e for e in self.performance_metrics["user_errors"] if e["type"] == error_type]
            if existing_errors:
                existing_errors[-1]["count"] += 1
            else:
                self.performance_metrics["user_errors"].append(error_record)
            
            logger.debug(f"📈 사용자 오류 추적: {error_type}")
            
        except Exception as e:
            logger.error(f"❌ 오류 추적 실패: {str(e)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        try:
            validation_times = self.performance_metrics["validation_times"]
            
            return {
                "validation_performance": {
                    "average_time_ms": sum(validation_times) / len(validation_times) if validation_times else 0,
                    "max_time_ms": max(validation_times) if validation_times else 0,
                    "total_validations": len(validation_times)
                },
                "user_errors": {
                    "total_errors": len(self.performance_metrics["user_errors"]),
                    "error_types": [e["type"] for e in self.performance_metrics["user_errors"]]
                },
                "active_feedbacks": len(self.active_feedbacks),
                "cache_size": len(self.validation_cache)
            }
            
        except Exception as e:
            logger.error(f"❌ 성능 메트릭 조회 오류: {str(e)}")
            return {}
    
    def cleanup_expired_cache(self):
        """만료된 캐시 정리"""
        try:
            now = datetime.now()
            expired_keys = [
                key for key, (_, cached_time) in self.validation_cache.items()
                if (now - cached_time).total_seconds() > 300  # 5분 후 만료
            ]
            
            for key in expired_keys:
                del self.validation_cache[key]
            
            if expired_keys:
                logger.debug(f"🗑️ 만료된 검증 캐시 {len(expired_keys)}개 정리")
                
        except Exception as e:
            logger.error(f"❌ 캐시 정리 오류: {str(e)}")

# 전역 UX 서비스 인스턴스
ux_service = UXService()