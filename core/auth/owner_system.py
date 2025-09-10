"""
Owner 하드코딩 인식 시스템
- kangkyungjun88@gmail.com을 유일한 Owner로 인식
- 역할 기반 권한 시스템
- 자동 Owner 승급 시스템
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy import text
from ..database.mysql_connection import get_mysql_session

logger = logging.getLogger(__name__)

# Owner 이메일 하드코딩 (절대 변경 불가)
OWNER_EMAIL = "kangkyungjun88@gmail.com"
OWNER_USERNAME = "teamprime"

class OwnerRecognitionSystem:
    """Owner 하드코딩 인식 및 권한 관리 시스템"""
    
    def __init__(self):
        self.owner_email = OWNER_EMAIL
        self.owner_username = OWNER_USERNAME
        
    async def is_owner(self, email: str) -> bool:
        """이메일이 Owner인지 확인"""
        return email.lower() == self.owner_email.lower()
    
    async def is_owner_by_username(self, username: str) -> bool:
        """사용자명이 Owner인지 확인"""
        return username.lower() == self.owner_username.lower()
    
    async def get_user_role(self, user_id: int) -> Optional[str]:
        """사용자 역할 조회"""
        try:
            async with get_mysql_session() as session:
                result = await session.execute(text("""
                    SELECT role FROM users WHERE id = :user_id
                """), {"user_id": user_id})
                
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"사용자 역할 조회 실패: {str(e)}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """이메일로 사용자 정보 조회"""
        try:
            async with get_mysql_session() as session:
                result = await session.execute(text("""
                    SELECT id, username, email, role, is_active, created_at
                    FROM users WHERE email = :email
                """), {"email": email})
                
                row = result.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "role": row[3],
                        "is_active": row[4],
                        "created_at": row[5]
                    }
                return None
                
        except Exception as e:
            logger.error(f"사용자 정보 조회 실패: {str(e)}")
            return None
    
    async def ensure_owner_exists(self) -> bool:
        """Owner 계정 존재 확인 및 자동 생성"""
        try:
            # 기존 Owner 계정 확인
            owner_user = await self.get_user_by_email(self.owner_email)
            
            if owner_user:
                # Owner 역할 확인 및 업데이트
                if owner_user["role"] != "owner":
                    await self.promote_to_owner(owner_user["id"])
                    logger.info(f"✅ Owner 역할 업데이트 완료: {self.owner_email}")
                else:
                    logger.info(f"✅ Owner 계정 확인 완료: {self.owner_email}")
                return True
            
            # Owner 계정이 없으면 생성
            return await self.create_owner_account()
            
        except Exception as e:
            logger.error(f"❌ Owner 계정 확인/생성 실패: {str(e)}")
            return False
    
    async def create_owner_account(self) -> bool:
        """Owner 계정 자동 생성"""
        try:
            async with get_mysql_session() as session:
                # 임시 패스워드 해시 (실제로는 초기 설정시 변경 필요)
                temp_password_hash = "$2b$12$temporary.owner.password.hash"
                
                await session.execute(text("""
                    INSERT INTO users (username, email, password_hash, role, is_active)
                    VALUES (:username, :email, :password_hash, 'owner', true)
                """), {
                    "username": self.owner_username,
                    "email": self.owner_email,
                    "password_hash": temp_password_hash
                })
                
                logger.info(f"✅ Owner 계정 자동 생성 완료: {self.owner_email}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Owner 계정 생성 실패: {str(e)}")
            return False
    
    async def promote_to_owner(self, user_id: int) -> bool:
        """사용자를 Owner로 승급"""
        try:
            async with get_mysql_session() as session:
                await session.execute(text("""
                    UPDATE users 
                    SET role = 'owner', updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """), {"user_id": user_id})
                
                logger.info(f"✅ Owner 승급 완료: user_id={user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Owner 승급 실패: {str(e)}")
            return False
    
    async def can_promote_users(self, user_id: int) -> bool:
        """사용자가 다른 사용자를 승급시킬 권한이 있는지 확인"""
        try:
            role = await self.get_user_role(user_id)
            # Owner와 Prime만 사용자 승급 권한 보유
            return role in ["owner", "prime"]
            
        except Exception as e:
            logger.error(f"승급 권한 확인 실패: {str(e)}")
            return False
    
    async def promote_user(self, promoter_id: int, target_email: str, new_role: str) -> Dict[str, Any]:
        """사용자 승급 처리"""
        try:
            # 승급 권한 확인
            if not await self.can_promote_users(promoter_id):
                return {"success": False, "message": "승급 권한이 없습니다"}
            
            # 대상 사용자 조회
            target_user = await self.get_user_by_email(target_email)
            if not target_user:
                return {"success": False, "message": "대상 사용자를 찾을 수 없습니다"}
            
            # Owner는 승급 불가 (하드코딩된 유일한 Owner)
            if target_user["role"] == "owner":
                return {"success": False, "message": "Owner는 역할 변경이 불가능합니다"}
            
            # 역할 계층 검증
            role_hierarchy = ["user", "member", "manager", "prime", "owner"]
            if new_role not in role_hierarchy[:-1]:  # owner 제외
                return {"success": False, "message": "유효하지 않은 역할입니다"}
            
            # 승급 실행
            async with get_mysql_session() as session:
                await session.execute(text("""
                    UPDATE users 
                    SET role = :new_role, 
                        promoted_by = :promoter_id,
                        promoted_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :target_id
                """), {
                    "new_role": new_role,
                    "promoter_id": promoter_id,
                    "target_id": target_user["id"]
                })
                
                logger.info(f"✅ 사용자 승급 완료: {target_email} → {new_role}")
                return {"success": True, "message": f"사용자를 {new_role}로 승급했습니다"}
                
        except Exception as e:
            logger.error(f"❌ 사용자 승급 실패: {str(e)}")
            return {"success": False, "message": "승급 처리 중 오류가 발생했습니다"}
    
    async def has_vip_access(self, user_id: int) -> bool:
        """VIP 서비스(암호화폐 거래) 접근 권한 확인"""
        try:
            role = await self.get_user_role(user_id)
            # Owner와 Prime만 VIP 서비스 접근 가능
            return role in ["owner", "prime"]
            
        except Exception as e:
            logger.error(f"VIP 접근 권한 확인 실패: {str(e)}")
            return False
    
    def get_role_permissions(self, role: str) -> Dict[str, bool]:
        """역할별 권한 매트릭스"""
        permissions = {
            "owner": {
                "crypto_trading": True,      # 암호화폐 거래
                "user_promotion": True,      # 사용자 승급
                "system_admin": True,        # 시스템 관리
                "task_management": True,     # 업무 관리
                "expense_approval": True,    # 지출 승인
                "income_management": True,   # 수익 관리
                "dashboard_access": True     # 대시보드 접근
            },
            "prime": {
                "crypto_trading": True,      # 암호화폐 거래 (VIP)
                "user_promotion": True,      # 사용자 승급
                "system_admin": False,       # 시스템 관리 불가
                "task_management": True,     # 업무 관리
                "expense_approval": True,    # 지출 승인
                "income_management": True,   # 수익 관리
                "dashboard_access": True     # 대시보드 접근
            },
            "manager": {
                "crypto_trading": False,     # 암호화폐 거래 불가
                "user_promotion": False,     # 사용자 승급 불가
                "system_admin": False,       # 시스템 관리 불가
                "task_management": True,     # 업무 관리
                "expense_approval": True,    # 지출 승인
                "income_management": True,   # 수익 관리
                "dashboard_access": True     # 대시보드 접근
            },
            "member": {
                "crypto_trading": False,     # 암호화폐 거래 불가
                "user_promotion": False,     # 사용자 승급 불가
                "system_admin": False,       # 시스템 관리 불가
                "task_management": True,     # 업무 관리
                "expense_approval": False,   # 지출 승인 불가
                "income_management": False,  # 수익 관리 불가
                "dashboard_access": True     # 대시보드 접근
            },
            "user": {
                "crypto_trading": False,     # 암호화폐 거래 불가
                "user_promotion": False,     # 사용자 승급 불가
                "system_admin": False,       # 시스템 관리 불가
                "task_management": False,    # 업무 관리 불가
                "expense_approval": False,   # 지출 승인 불가
                "income_management": False,  # 수익 관리 불가
                "dashboard_access": True     # 대시보드 접근
            }
        }
        
        return permissions.get(role, permissions["user"])
    
    async def has_task_management_permission(self, user_id: int) -> bool:
        """업무 관리 권한 확인"""
        try:
            role = await self.get_user_role(user_id)
            permissions = self.get_role_permissions(role)
            return permissions.get("task_management", False)
        except Exception as e:
            logger.error(f"업무 관리 권한 확인 실패: {str(e)}")
            return False
    
    async def has_expense_permission(self, user_id: int) -> bool:
        """지출 관리 권한 확인"""
        try:
            role = await self.get_user_role(user_id)
            permissions = self.get_role_permissions(role)
            return permissions.get("expense_approval", False)
        except Exception as e:
            logger.error(f"지출 관리 권한 확인 실패: {str(e)}")
            return False
    
    async def has_income_permission(self, user_id: int) -> bool:
        """수익 관리 권한 확인"""
        try:
            role = await self.get_user_role(user_id)
            permissions = self.get_role_permissions(role)
            return permissions.get("income_management", False)
        except Exception as e:
            logger.error(f"수익 관리 권한 확인 실패: {str(e)}")
            return False

# 전역 Owner 인식 시스템 인스턴스
owner_system = OwnerRecognitionSystem()