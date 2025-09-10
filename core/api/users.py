"""
사용자 관리 API 엔드포인트
- 사용자 목록 및 권한 관리
- 역할 승급 시스템
- Owner 권한 기능
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import text
from ..database.mysql_connection import get_mysql_session
from ..auth.middleware import require_auth, require_promotion_permission, require_owner
from ..auth.owner_system import owner_system

logger = logging.getLogger(__name__)
router = APIRouter()

# === 데이터 모델들 ===

class UserPromote(BaseModel):
    email: EmailStr = Field(..., description="승급할 사용자 이메일")
    new_role: str = Field(..., pattern="^(prime|manager|member|user)$", description="새로운 역할")
    reason: Optional[str] = Field(None, max_length=500, description="승급 사유")

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

# === 사용자 관리 API ===

@router.get("/api/users/list")
async def get_users(
    request: Request,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    limit: int = 20,
    user: Dict = Depends(require_promotion_permission)
):
    """사용자 목록 조회 (Owner/Prime만 가능)"""
    try:
        offset = (page - 1) * limit
        
        # 기본 쿼리
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        # 필터 조건 추가
        if role:
            where_conditions.append("role = :role")
            params["role"] = role
        if is_active is not None:
            where_conditions.append("is_active = :is_active")
            params["is_active"] = is_active
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        async with get_mysql_session() as session:
            # 사용자 목록 조회
            query = f"""
                SELECT u.id, u.username, u.email, u.role, u.is_active, 
                       u.created_at, u.updated_at, u.last_login,
                       u.promoted_by, u.promoted_at,
                       promoter.username as promoter_name
                FROM users u
                LEFT JOIN users promoter ON u.promoted_by = promoter.id
                {where_clause}
                ORDER BY 
                    CASE 
                        WHEN u.role = 'owner' THEN 1
                        WHEN u.role = 'prime' THEN 2
                        WHEN u.role = 'manager' THEN 3
                        WHEN u.role = 'member' THEN 4
                        WHEN u.role = 'user' THEN 5
                    END,
                    u.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = await session.execute(text(query), params)
            users = []
            
            for row in result.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "role": row[3],
                    "is_active": bool(row[4]),
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat(),
                    "last_login": row[7].isoformat() if row[7] else None,
                    "promoted_by": row[8],
                    "promoted_at": row[9].isoformat() if row[9] else None,
                    "promoter_name": row[10]
                })
            
            # 총 개수 조회
            count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM users u {where_clause}"), 
                count_params
            )
            total = count_result.scalar()
            
            return {
                "success": True,
                "users": users,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            }
            
    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 목록 조회에 실패했습니다")

@router.post("/api/users/promote")
async def promote_user(
    request: Request,
    promote_data: UserPromote,
    user: Dict = Depends(require_promotion_permission)
):
    """사용자 역할 승급 (Owner/Prime만 가능)"""
    try:
        # Owner 시스템을 통한 승급 처리
        result = await owner_system.promote_user(
            promoter_id=user["id"],
            target_email=promote_data.email,
            new_role=promote_data.new_role
        )
        
        if result["success"]:
            logger.info(f"✅ 사용자 승급 완료: {promote_data.email} → {promote_data.new_role} (승급자: {user['username']})")
            
            return {
                "success": True,
                "message": result["message"],
                "promoted_email": promote_data.email,
                "new_role": promote_data.new_role,
                "promoted_by": user["username"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 승급 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 승급에 실패했습니다")

@router.get("/api/users/role-stats")
async def get_role_statistics(
    request: Request,
    user: Dict = Depends(require_promotion_permission)
):
    """역할별 사용자 통계"""
    try:
        async with get_mysql_session() as session:
            # 역할별 통계
            role_stats = await session.execute(text("""
                SELECT role, COUNT(*) as count
                FROM users
                WHERE is_active = 1
                GROUP BY role
                ORDER BY 
                    CASE 
                        WHEN role = 'owner' THEN 1
                        WHEN role = 'prime' THEN 2
                        WHEN role = 'manager' THEN 3
                        WHEN role = 'member' THEN 4
                        WHEN role = 'user' THEN 5
                    END
            """))
            
            role_counts = {}
            total_active_users = 0
            
            for row in role_stats.fetchall():
                role_counts[row[0]] = row[1]
                total_active_users += row[1]
            
            # 최근 승급 현황
            recent_promotions = await session.execute(text("""
                SELECT u.username, u.email, u.role, u.promoted_at, 
                       promoter.username as promoter_name
                FROM users u
                LEFT JOIN users promoter ON u.promoted_by = promoter.id
                WHERE u.promoted_at IS NOT NULL
                ORDER BY u.promoted_at DESC
                LIMIT 10
            """))
            
            promotions = []
            for row in recent_promotions.fetchall():
                promotions.append({
                    "username": row[0],
                    "email": row[1],
                    "role": row[2],
                    "promoted_at": row[3].isoformat() if row[3] else None,
                    "promoter_name": row[4]
                })
            
            return {
                "success": True,
                "total_active_users": total_active_users,
                "role_counts": role_counts,
                "recent_promotions": promotions,
                "vip_users": role_counts.get("owner", 0) + role_counts.get("prime", 0)
            }
            
    except Exception as e:
        logger.error(f"역할 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="역할 통계 조회에 실패했습니다")

@router.get("/api/users/permissions")
async def get_user_permissions(
    request: Request,
    user: Dict = Depends(require_auth)
):
    """현재 사용자 권한 정보"""
    try:
        user_id = user["id"]
        
        # 사용자 권한 조회
        permissions = await owner_system.get_role_permissions(user.get("role", "user"))
        
        # VIP 접근 권한 확인
        has_vip_access = await owner_system.has_vip_access(user_id)
        
        # 승급 권한 확인
        can_promote = await owner_system.can_promote_users(user_id)
        
        return {
            "success": True,
            "user_info": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            },
            "permissions": permissions,
            "special_access": {
                "vip_trading": has_vip_access,
                "user_promotion": can_promote
            }
        }
        
    except Exception as e:
        logger.error(f"권한 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="권한 정보 조회에 실패했습니다")

@router.get("/api/users/{user_id}")
async def get_user_detail(
    request: Request,
    user_id: int,
    user: Dict = Depends(require_promotion_permission)
):
    """특정 사용자 상세 정보"""
    try:
        async with get_mysql_session() as session:
            query = """
                SELECT u.id, u.username, u.email, u.role, u.is_active,
                       u.created_at, u.updated_at, u.last_login,
                       u.promoted_by, u.promoted_at,
                       promoter.username as promoter_name,
                       promoter.email as promoter_email
                FROM users u
                LEFT JOIN users promoter ON u.promoted_by = promoter.id
                WHERE u.id = :user_id
            """
            
            result = await session.execute(text(query), {"user_id": user_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
            
            # 사용자 권한 정보
            permissions = owner_system.get_role_permissions(row[3])
            
            return {
                "success": True,
                "user": {
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "role": row[3],
                    "is_active": bool(row[4]),
                    "created_at": row[5].isoformat(),
                    "updated_at": row[6].isoformat(),
                    "last_login": row[7].isoformat() if row[7] else None,
                    "promoted_by": row[8],
                    "promoted_at": row[9].isoformat() if row[9] else None,
                    "promoter_name": row[10],
                    "promoter_email": row[11]
                },
                "permissions": permissions
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 상세 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 정보 조회에 실패했습니다")

@router.put("/api/users/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    update_data: UserUpdate,
    user: Dict = Depends(require_promotion_permission)
):
    """사용자 정보 수정 (Owner/Prime만 가능)"""
    try:
        async with get_mysql_session() as session:
            # 사용자 존재 확인
            check_result = await session.execute(
                text("SELECT id, role FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            target_user = check_result.fetchone()
            
            if not target_user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
            
            # Owner는 수정 불가 (보안상)
            if target_user[1] == "owner":
                raise HTTPException(status_code=403, detail="Owner 계정은 수정할 수 없습니다")
            
            # 수정할 필드들 동적 구성
            update_fields = []
            params = {"user_id": user_id}
            
            if update_data.username is not None:
                # 중복 확인
                username_check = await session.execute(
                    text("SELECT id FROM users WHERE username = :username AND id != :user_id"),
                    {"username": update_data.username, "user_id": user_id}
                )
                if username_check.fetchone():
                    raise HTTPException(status_code=400, detail="이미 사용 중인 사용자명입니다")
                
                update_fields.append("username = :username")
                params["username"] = update_data.username
                
            if update_data.email is not None:
                # 중복 확인
                email_check = await session.execute(
                    text("SELECT id FROM users WHERE email = :email AND id != :user_id"),
                    {"email": update_data.email, "user_id": user_id}
                )
                if email_check.fetchone():
                    raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
                
                update_fields.append("email = :email")
                params["email"] = update_data.email
                
            if update_data.is_active is not None:
                update_fields.append("is_active = :is_active")
                params["is_active"] = update_data.is_active
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")
            
            # 사용자 정보 수정
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = :user_id"
            
            await session.execute(text(query), params)
            
            logger.info(f"✅ 사용자 정보 수정 완료: ID {user_id} (수정자: {user['username']})")
            
            return {
                "success": True,
                "message": "사용자 정보가 성공적으로 수정되었습니다"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 정보 수정에 실패했습니다")

@router.post("/api/users/{user_id}/toggle-active")
async def toggle_user_active(
    request: Request,
    user_id: int,
    user: Dict = Depends(require_owner)
):
    """사용자 활성화/비활성화 토글 (Owner만 가능)"""
    try:
        async with get_mysql_session() as session:
            # 사용자 정보 조회
            check_result = await session.execute(
                text("SELECT id, role, is_active, username FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            target_user = check_result.fetchone()
            
            if not target_user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
            
            # Owner는 비활성화 불가
            if target_user[1] == "owner":
                raise HTTPException(status_code=403, detail="Owner 계정은 비활성화할 수 없습니다")
            
            # 활성화 상태 토글
            new_active_status = not bool(target_user[2])
            
            await session.execute(
                text("UPDATE users SET is_active = :is_active, updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"),
                {"is_active": new_active_status, "user_id": user_id}
            )
            
            action = "활성화" if new_active_status else "비활성화"
            logger.info(f"✅ 사용자 {action}: {target_user[3]} (ID: {user_id})")
            
            return {
                "success": True,
                "message": f"사용자가 {action}되었습니다",
                "user_id": user_id,
                "is_active": new_active_status
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 활성화 토글 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 상태 변경에 실패했습니다")