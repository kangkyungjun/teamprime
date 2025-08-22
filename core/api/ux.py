"""사용자 경험 개선 API 엔드포인트"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from ..services.ux_service import ux_service, FeedbackType, ValidationLevel
from ..auth.middleware import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ux"])

# 요청 모델 정의
class ValidationRequest(BaseModel):
    field_name: str
    value: Any
    validation_level: str = "standard"
    custom_rules: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    type: str
    title: str
    message: str
    duration: int = 5
    actions: Optional[List[Dict[str, str]]] = None
    metadata: Optional[Dict[str, Any]] = None

class UserPreferencesRequest(BaseModel):
    preferences: Dict[str, Any]

class UserErrorRequest(BaseModel):
    error_type: str
    context: Dict[str, Any]

@router.post("/validate-field")
async def validate_field(
    request: ValidationRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """필드 데이터 검증"""
    try:
        # 검증 수준 변환
        try:
            validation_level = ValidationLevel(request.validation_level)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 검증 수준입니다")
        
        # 검증 수행
        result = ux_service.validate_field(
            field_name=request.field_name,
            value=request.value,
            validation_level=validation_level,
            custom_rules=request.custom_rules
        )
        
        return {
            "success": True,
            "validation": {
                "is_valid": result.is_valid,
                "field_name": result.field_name,
                "message": result.message,
                "suggestion": result.suggestion,
                "severity": result.severity.value
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 필드 검증 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/validate-multiple")
async def validate_multiple_fields(
    fields: Dict[str, Any],
    validation_level: str = "standard",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """여러 필드 일괄 검증"""
    try:
        # 검증 수준 변환
        try:
            level = ValidationLevel(validation_level)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 검증 수준입니다")
        
        results = {}
        all_valid = True
        
        for field_name, value in fields.items():
            result = ux_service.validate_field(field_name, value, level)
            results[field_name] = {
                "is_valid": result.is_valid,
                "message": result.message,
                "suggestion": result.suggestion,
                "severity": result.severity.value
            }
            
            if not result.is_valid:
                all_valid = False
        
        return {
            "success": True,
            "validation": {
                "all_valid": all_valid,
                "results": results,
                "total_fields": len(fields),
                "valid_fields": sum(1 for r in results.values() if r["is_valid"]),
                "invalid_fields": sum(1 for r in results.values() if not r["is_valid"])
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 다중 필드 검증 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/create-feedback")
async def create_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """UI 피드백 생성"""
    try:
        # 피드백 유형 변환
        try:
            feedback_type = FeedbackType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 피드백 유형입니다")
        
        # 피드백 생성
        feedback_id = ux_service.create_feedback(
            feedback_type=feedback_type,
            title=request.title,
            message=request.message,
            duration=request.duration,
            actions=request.actions,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "feedback_id": feedback_id,
            "message": "피드백이 생성되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 피드백 생성 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/active-feedbacks")
async def get_active_feedbacks(current_user: Dict[str, Any] = Depends(require_auth)):
    """활성 피드백 목록 조회"""
    try:
        feedbacks = []
        
        for feedback in ux_service.active_feedbacks.values():
            feedbacks.append({
                "id": feedback.id,
                "type": feedback.type.value,
                "title": feedback.title,
                "message": feedback.message,
                "duration": feedback.duration,
                "actions": feedback.actions,
                "metadata": feedback.metadata,
                "timestamp": feedback.timestamp.isoformat()
            })
        
        # 최신 순으로 정렬
        feedbacks.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "success": True,
            "feedbacks": feedbacks,
            "total_count": len(feedbacks),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 피드백 목록 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.delete("/feedback/{feedback_id}")
async def remove_feedback(
    feedback_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """피드백 제거"""
    try:
        if feedback_id not in ux_service.active_feedbacks:
            raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다")
        
        del ux_service.active_feedbacks[feedback_id]
        
        return {
            "success": True,
            "message": "피드백이 제거되었습니다",
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 피드백 제거 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/help/{topic}")
async def get_help_content(
    topic: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """도움말 컨텐츠 조회"""
    try:
        help_content = ux_service.get_help_content(topic)
        
        if not help_content:
            raise HTTPException(status_code=404, detail="도움말을 찾을 수 없습니다")
        
        return {
            "success": True,
            "topic": topic,
            "help": help_content,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 도움말 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/help")
async def get_available_help_topics(current_user: Dict[str, Any] = Depends(require_auth)):
    """사용 가능한 도움말 주제 목록"""
    try:
        topics = []
        
        for topic, content in ux_service.help_messages.items():
            topics.append({
                "topic": topic,
                "title": content["title"],
                "description": content["content"][:100] + "..." if len(content["content"]) > 100 else content["content"]
            })
        
        return {
            "success": True,
            "topics": topics,
            "total_topics": len(topics),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 도움말 주제 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/user-preferences")
async def get_user_preferences(current_user: Dict[str, Any] = Depends(require_auth)):
    """사용자 설정 조회"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 정보를 찾을 수 없습니다")
        
        preferences = ux_service.get_user_preferences(user_id)
        
        return {
            "success": True,
            "preferences": preferences,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 설정 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/user-preferences")
async def update_user_preferences(
    request: UserPreferencesRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """사용자 설정 업데이트"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 정보를 찾을 수 없습니다")
        
        ux_service.set_user_preferences(user_id, request.preferences)
        
        return {
            "success": True,
            "message": "사용자 설정이 업데이트되었습니다",
            "preferences": request.preferences,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 사용자 설정 업데이트 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/track-error")
async def track_user_error(
    request: UserErrorRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """사용자 오류 추적"""
    try:
        user_id = current_user.get("id")
        
        # 컨텍스트에 사용자 정보 추가
        context = request.context.copy()
        context["user_id"] = user_id
        context["username"] = current_user.get("username", "unknown")
        
        ux_service.track_user_error(request.error_type, context)
        
        return {
            "success": True,
            "message": "오류가 추적되었습니다",
            "error_type": request.error_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 사용자 오류 추적 실패: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/performance-metrics")
async def get_performance_metrics(current_user: Dict[str, Any] = Depends(require_auth)):
    """UX 성능 메트릭 조회"""
    try:
        metrics = ux_service.get_performance_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 성능 메트릭 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/cleanup-cache")
async def cleanup_validation_cache(current_user: Dict[str, Any] = Depends(require_auth)):
    """검증 캐시 정리"""
    try:
        before_count = len(ux_service.validation_cache)
        ux_service.cleanup_expired_cache()
        after_count = len(ux_service.validation_cache)
        
        cleaned_count = before_count - after_count
        
        return {
            "success": True,
            "message": f"캐시 정리가 완료되었습니다",
            "cleaned_entries": cleaned_count,
            "remaining_entries": after_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 캐시 정리 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/validation-rules")
async def get_validation_rules(current_user: Dict[str, Any] = Depends(require_auth)):
    """검증 규칙 조회"""
    try:
        return {
            "success": True,
            "rules": ux_service.validation_rules,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 검증 규칙 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/quick-validate/{field_type}")
async def quick_validate(
    field_type: str,
    value: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """빠른 검증 (GET 방식)"""
    try:
        result = ux_service.validate_field(
            field_name=field_type,
            value=value,
            validation_level=ValidationLevel.BASIC
        )
        
        return {
            "success": True,
            "is_valid": result.is_valid,
            "message": result.message,
            "suggestion": result.suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 빠른 검증 오류: {str(e)}")
        return {"success": False, "error": str(e)}