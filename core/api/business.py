"""
비즈니스 관리 API 엔드포인트
- 업무 관리 (CRUD)
- 지출 관리 (승인 워크플로)
- 수익 관리
- 권한 기반 접근 제어
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text, desc
from ..database.mysql_connection import get_mysql_session
from ..auth.middleware import (
    require_auth, require_task_management, require_expense_approval, 
    require_income_management, auth_middleware
)

logger = logging.getLogger(__name__)
router = APIRouter()

# === 데이터 모델들 ===

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(기획|개발|디자인|운영|영업|고객지원|회계|법무|교육|유지보수|기타)$")
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, pattern="^(기획|개발|디자인|운영|영업|고객지원|회계|법무|교육|유지보수|기타)$")
    status: Optional[str] = Field(None, pattern="^(대기|진행중|완료|보류|취소)$")
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ExpenseCreate(BaseModel):
    task_id: Optional[int] = None
    category: str = Field(..., pattern="^(자산|소모품|식비|교통|출장|통신|소프트웨어|급여|인센티브|교육/세미나|관리비|인건비|용역|세금|기타|일반)$")
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1)
    receipt_file: Optional[str] = None
    participants_internal: Optional[str] = None  # JSON 문자열
    participants_external: int = Field(default=0, ge=0)
    external_note: Optional[str] = None
    expense_date: date

class ExpenseApproval(BaseModel):
    status: str = Field(..., pattern="^(승인|반려)$")
    note: Optional[str] = None

class IncomeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., pattern="^(틱톡|유튜브|애드몹|광고협찬|프로젝트|기타)$")
    amount: float = Field(..., gt=0)
    source: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    attachment_file: Optional[str] = None
    income_date: date

# === 업무 관리 API ===

@router.get("/api/business/tasks")
async def get_tasks(
    request: Request,
    status: Optional[str] = None,
    category: Optional[str] = None,
    assignee_id: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    user: Dict = Depends(require_task_management)
):
    """업무 목록 조회"""
    try:
        offset = (page - 1) * limit
        
        # 기본 쿼리
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        # 필터 조건 추가
        if status:
            where_conditions.append("status = :status")
            params["status"] = status
        if category:
            where_conditions.append("category = :category")
            params["category"] = category
        if assignee_id:
            where_conditions.append("assignee_id = :assignee_id")
            params["assignee_id"] = assignee_id
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        async with get_mysql_session() as session:
            # 업무 목록 조회
            query = f"""
                SELECT t.*, 
                       assignee.username as assignee_name,
                       creator.username as creator_name
                FROM tasks t
                LEFT JOIN users assignee ON t.assignee_id = assignee.id
                LEFT JOIN users creator ON t.created_by = creator.id
                {where_clause}
                ORDER BY t.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = await session.execute(text(query), params)
            tasks = []
            
            for row in result.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "status": row[3],
                    "assignee_id": row[4],
                    "assignee_name": row[11],  # assignee.username (12번째 컬럼)
                    "created_by": row[5],
                    "creator_name": row[12],   # creator.username (13번째 컬럼)
                    "start_date": row[6].isoformat() if row[6] else None,
                    "end_date": row[7].isoformat() if row[7] else None,
                    "description": row[8],
                    "created_at": row[9].isoformat(),
                    "updated_at": row[10].isoformat()
                })
            
            # 총 개수 조회
            count_query = f"""
                SELECT COUNT(*) FROM tasks t {where_clause.replace('t.*,', '').replace('LEFT JOIN users assignee ON t.assignee_id = assignee.id', '').replace('LEFT JOIN users creator ON t.created_by = creator.id', '').replace('ORDER BY t.created_at DESC', '').replace('LIMIT :limit OFFSET :offset', '')}
            """
            count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
            count_result = await session.execute(text(count_query), count_params)
            total = count_result.scalar()
            
            return {
                "success": True,
                "tasks": tasks,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            }
            
    except Exception as e:
        logger.error(f"업무 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 목록 조회에 실패했습니다")

@router.post("/api/business/tasks")
async def create_task(
    request: Request,
    task_data: TaskCreate,
    user: Dict = Depends(require_task_management)
):
    """새 업무 생성"""
    try:
        async with get_mysql_session() as session:
            # 담당자 존재 확인 (지정된 경우)
            if task_data.assignee_id:
                assignee_check = await session.execute(
                    text("SELECT id FROM users WHERE id = :assignee_id AND is_active = 1"),
                    {"assignee_id": task_data.assignee_id}
                )
                if not assignee_check.fetchone():
                    raise HTTPException(status_code=400, detail="유효하지 않은 담당자입니다")
            
            # 업무 생성
            query = """
                INSERT INTO tasks (title, category, description, assignee_id, created_by, start_date, end_date)
                VALUES (:title, :category, :description, :assignee_id, :created_by, :start_date, :end_date)
            """
            
            params = {
                "title": task_data.title,
                "category": task_data.category,
                "description": task_data.description,
                "assignee_id": task_data.assignee_id,
                "created_by": user["id"],
                "start_date": task_data.start_date,
                "end_date": task_data.end_date
            }
            
            result = await session.execute(text(query), params)
            task_id = result.lastrowid
            
            logger.info(f"✅ 새 업무 생성: {task_data.title} (ID: {task_id})")
            
            return {
                "success": True,
                "message": "업무가 성공적으로 생성되었습니다",
                "task_id": task_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업무 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 생성에 실패했습니다")

@router.get("/api/business/tasks/{task_id}")
async def get_task(
    request: Request,
    task_id: int,
    user: Dict = Depends(require_task_management)
):
    """업무 상세 조회"""
    try:
        async with get_mysql_session() as session:
            query = """
                SELECT t.*,
                       assignee.username as assignee_name,
                       assignee.email as assignee_email,
                       creator.username as creator_name,
                       creator.email as creator_email
                FROM tasks t
                LEFT JOIN users assignee ON t.assignee_id = assignee.id
                LEFT JOIN users creator ON t.created_by = creator.id
                WHERE t.id = :task_id
            """
            
            result = await session.execute(text(query), {"task_id": task_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="업무를 찾을 수 없습니다")
            
            return {
                "success": True,
                "task": {
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "status": row[3],
                    "assignee_id": row[4],
                    "assignee_name": row[11],
                    "assignee_email": row[12],
                    "created_by": row[5],
                    "creator_name": row[13],
                    "creator_email": row[14],
                    "start_date": row[6].isoformat() if row[6] else None,
                    "end_date": row[7].isoformat() if row[7] else None,
                    "description": row[8],
                    "created_at": row[9].isoformat(),
                    "updated_at": row[10].isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업무 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 조회에 실패했습니다")

@router.put("/api/business/tasks/{task_id}")
async def update_task(
    request: Request,
    task_id: int,
    task_data: TaskUpdate,
    user: Dict = Depends(require_task_management)
):
    """업무 수정"""
    try:
        async with get_mysql_session() as session:
            # 업무 존재 확인
            check_result = await session.execute(
                text("SELECT id FROM tasks WHERE id = :task_id"),
                {"task_id": task_id}
            )
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="업무를 찾을 수 없습니다")
            
            # 담당자 존재 확인 (지정된 경우)
            if task_data.assignee_id:
                assignee_check = await session.execute(
                    text("SELECT id FROM users WHERE id = :assignee_id AND is_active = 1"),
                    {"assignee_id": task_data.assignee_id}
                )
                if not assignee_check.fetchone():
                    raise HTTPException(status_code=400, detail="유효하지 않은 담당자입니다")
            
            # 수정할 필드들 동적 구성
            update_fields = []
            params = {"task_id": task_id}
            
            if task_data.title is not None:
                update_fields.append("title = :title")
                params["title"] = task_data.title
            if task_data.category is not None:
                update_fields.append("category = :category")
                params["category"] = task_data.category
            if task_data.status is not None:
                update_fields.append("status = :status")
                params["status"] = task_data.status
            if task_data.description is not None:
                update_fields.append("description = :description")
                params["description"] = task_data.description
            if task_data.assignee_id is not None:
                update_fields.append("assignee_id = :assignee_id")
                params["assignee_id"] = task_data.assignee_id
            if task_data.start_date is not None:
                update_fields.append("start_date = :start_date")
                params["start_date"] = task_data.start_date
            if task_data.end_date is not None:
                update_fields.append("end_date = :end_date")
                params["end_date"] = task_data.end_date
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")
            
            # 업무 수정
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = :task_id"
            
            await session.execute(text(query), params)
            
            logger.info(f"✅ 업무 수정 완료: ID {task_id}")
            
            return {
                "success": True,
                "message": "업무가 성공적으로 수정되었습니다"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업무 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 수정에 실패했습니다")

@router.delete("/api/business/tasks/{task_id}")
async def delete_task(
    request: Request,
    task_id: int,
    user: Dict = Depends(require_task_management)
):
    """업무 삭제"""
    try:
        async with get_mysql_session() as session:
            # 업무 존재 확인
            check_result = await session.execute(
                text("SELECT id FROM tasks WHERE id = :task_id"),
                {"task_id": task_id}
            )
            if not check_result.fetchone():
                raise HTTPException(status_code=404, detail="업무를 찾을 수 없습니다")
            
            # 업무 삭제 (CASCADE로 관련 데이터도 삭제됨)
            await session.execute(text("DELETE FROM tasks WHERE id = :task_id"), {"task_id": task_id})
            
            logger.info(f"✅ 업무 삭제 완료: ID {task_id}")
            
            return {
                "success": True,
                "message": "업무가 성공적으로 삭제되었습니다"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업무 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 삭제에 실패했습니다")

# === 추가 업무 관리 API (지출 연동용) ===

@router.get("/api/business/tasks/active")
async def get_active_tasks(
    request: Request,
    user: Dict = Depends(require_task_management)
):
    """활성 업무 목록 조회 (지출 연동용 - 대기, 진행중 상태만)"""
    try:
        async with get_mysql_session() as session:
            query = """
                SELECT t.id, t.title, t.category, t.status,
                       assignee.username as assignee_name
                FROM tasks t
                LEFT JOIN users assignee ON t.assignee_id = assignee.id
                WHERE t.status IN ('대기', '진행중')
                ORDER BY t.created_at DESC
                LIMIT 50
            """
            
            result = await session.execute(text(query))
            tasks = []
            
            for row in result.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "status": row[3],
                    "assignee_name": row[4]
                })
            
            return {
                "success": True,
                "tasks": tasks
            }
            
    except Exception as e:
        logger.error(f"활성 업무 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="활성 업무 조회에 실패했습니다")

@router.get("/api/business/tasks/search")
async def search_tasks(
    request: Request,
    query: str,
    limit: int = 20,
    user: Dict = Depends(require_task_management)
):
    """업무명 검색 (완료된 업무 포함)"""
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="검색어를 입력해주세요")
        
        async with get_mysql_session() as session:
            search_query = """
                SELECT t.id, t.title, t.category, t.status,
                       assignee.username as assignee_name,
                       t.created_at
                FROM tasks t
                LEFT JOIN users assignee ON t.assignee_id = assignee.id
                WHERE t.title LIKE :search_term
                ORDER BY t.created_at DESC
                LIMIT :limit
            """
            
            search_term = f"%{query.strip()}%"
            result = await session.execute(text(search_query), {
                "search_term": search_term,
                "limit": limit
            })
            
            tasks = []
            for row in result.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "status": row[3],
                    "assignee_name": row[4],
                    "created_at": row[5].isoformat()
                })
            
            return {
                "success": True,
                "tasks": tasks,
                "query": query,
                "total_found": len(tasks)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업무 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="업무 검색에 실패했습니다")

# === 지출 관리 API ===

@router.get("/api/business/expenses")
async def get_expenses(
    request: Request,
    status: Optional[str] = None,
    category: Optional[str] = None,
    month: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: Dict = Depends(require_auth)
):
    """지출 목록 조회"""
    try:
        offset = (page - 1) * limit
        
        # 기본 쿼리
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        # 필터 조건 추가
        if status:
            where_conditions.append("e.status = :status")
            params["status"] = status
        if category:
            where_conditions.append("e.category = :category")
            params["category"] = category
        if month:  # YYYY-MM 형식
            where_conditions.append("DATE_FORMAT(e.expense_date, '%Y-%m') = :month")
            params["month"] = month
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        async with get_mysql_session() as session:
            query = f"""
                SELECT e.*, 
                       creator.username as creator_name,
                       approver.username as approver_name,
                       task.title as task_title
                FROM expenses e
                LEFT JOIN users creator ON e.created_by = creator.id
                LEFT JOIN users approver ON e.approved_by = approver.id
                LEFT JOIN tasks task ON e.task_id = task.id
                {where_clause}
                ORDER BY e.expense_date DESC, e.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = await session.execute(text(query), params)
            expenses = []
            
            for row in result.fetchall():
                expenses.append({
                    "id": row[0],
                    "task_id": row[1],
                    "task_title": row[18],
                    "category": row[2],
                    "amount": float(row[3]),
                    "description": row[4],
                    "receipt_file": row[5],
                    "participants_internal": row[6],
                    "participants_external": row[7],
                    "external_note": row[8],
                    "created_by": row[9],
                    "creator_name": row[16],
                    "status": row[10],
                    "approved_by": row[11],
                    "approver_name": row[17],
                    "expense_date": row[12].isoformat(),
                    "created_at": row[13].isoformat(),
                    "updated_at": row[14].isoformat()
                })
            
            # 총 개수 조회
            count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM expenses e {where_clause}"), 
                count_params
            )
            total = count_result.scalar()
            
            return {
                "success": True,
                "expenses": expenses,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            }
            
    except Exception as e:
        logger.error(f"지출 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="지출 목록 조회에 실패했습니다")

@router.post("/api/business/expenses")
async def create_expense(
    request: Request,
    expense_data: ExpenseCreate,
    user: Dict = Depends(require_auth)
):
    """새 지출 등록"""
    try:
        async with get_mysql_session() as session:
            # 연관 업무 존재 확인 (지정된 경우)
            if expense_data.task_id:
                task_check = await session.execute(
                    text("SELECT id FROM tasks WHERE id = :task_id"),
                    {"task_id": expense_data.task_id}
                )
                if not task_check.fetchone():
                    raise HTTPException(status_code=400, detail="유효하지 않은 업무입니다")
            
            # 지출 등록
            query = """
                INSERT INTO expenses (task_id, category, amount, description, receipt_file, 
                                    participants_internal, participants_external, external_note,
                                    created_by, expense_date)
                VALUES (:task_id, :category, :amount, :description, :receipt_file,
                        :participants_internal, :participants_external, :external_note,
                        :created_by, :expense_date)
            """
            
            params = {
                "task_id": expense_data.task_id,
                "category": expense_data.category,
                "amount": expense_data.amount,
                "description": expense_data.description,
                "receipt_file": expense_data.receipt_file,
                "participants_internal": expense_data.participants_internal,
                "participants_external": expense_data.participants_external,
                "external_note": expense_data.external_note,
                "created_by": user["id"],
                "expense_date": expense_data.expense_date
            }
            
            result = await session.execute(text(query), params)
            expense_id = result.lastrowid
            
            logger.info(f"✅ 새 지출 등록: {expense_data.description} (ID: {expense_id}, 금액: {expense_data.amount:,}원)")
            
            return {
                "success": True,
                "message": "지출이 성공적으로 등록되었습니다",
                "expense_id": expense_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지출 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="지출 등록에 실패했습니다")

@router.put("/api/business/expenses/{expense_id}/approve")
async def approve_expense(
    request: Request,
    expense_id: int,
    approval_data: ExpenseApproval,
    user: Dict = Depends(require_expense_approval)
):
    """지출 승인/반려"""
    try:
        async with get_mysql_session() as session:
            # 지출 존재 및 승인 대기 상태 확인
            check_result = await session.execute(
                text("SELECT id, status FROM expenses WHERE id = :expense_id"),
                {"expense_id": expense_id}
            )
            expense = check_result.fetchone()
            
            if not expense:
                raise HTTPException(status_code=404, detail="지출을 찾을 수 없습니다")
            
            if expense[1] != "검토":
                raise HTTPException(status_code=400, detail="검토 중인 지출만 승인/반려할 수 있습니다")
            
            # 승인/반려 처리
            new_status = "승인" if approval_data.status == "승인" else "반려"
            
            query = """
                UPDATE expenses 
                SET status = :status, approved_by = :approved_by, updated_at = CURRENT_TIMESTAMP
                WHERE id = :expense_id
            """
            
            await session.execute(text(query), {
                "status": new_status,
                "approved_by": user["id"],
                "expense_id": expense_id
            })
            
            logger.info(f"✅ 지출 {new_status}: ID {expense_id} (승인자: {user['username']})")
            
            return {
                "success": True,
                "message": f"지출이 {new_status}되었습니다"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"지출 승인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="지출 승인 처리에 실패했습니다")

# === 수익 관리 API ===

@router.get("/api/business/incomes")
async def get_incomes(
    request: Request,
    category: Optional[str] = None,
    month: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: Dict = Depends(require_income_management)
):
    """수익 목록 조회"""
    try:
        offset = (page - 1) * limit
        
        # 기본 쿼리
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        # 필터 조건 추가
        if category:
            where_conditions.append("category = :category")
            params["category"] = category
        if month:  # YYYY-MM 형식
            where_conditions.append("DATE_FORMAT(income_date, '%Y-%m') = :month")
            params["month"] = month
        
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        
        async with get_mysql_session() as session:
            query = f"""
                SELECT i.*, u.username as creator_name
                FROM incomes i
                LEFT JOIN users u ON i.created_by = u.id
                {where_clause}
                ORDER BY i.income_date DESC, i.created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = await session.execute(text(query), params)
            incomes = []
            
            for row in result.fetchall():
                incomes.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "amount": float(row[3]),
                    "source": row[4],
                    "description": row[5],
                    "attachment_file": row[6],
                    "created_by": row[7],
                    "creator_name": row[11],
                    "income_date": row[8].isoformat(),
                    "created_at": row[9].isoformat(),
                    "updated_at": row[10].isoformat()
                })
            
            # 총 개수 조회
            count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
            count_result = await session.execute(
                text(f"SELECT COUNT(*) FROM incomes i {where_clause}"), 
                count_params
            )
            total = count_result.scalar()
            
            return {
                "success": True,
                "incomes": incomes,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            }
            
    except Exception as e:
        logger.error(f"수익 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="수익 목록 조회에 실패했습니다")

@router.post("/api/business/incomes")
async def create_income(
    request: Request,
    income_data: IncomeCreate,
    user: Dict = Depends(require_income_management)
):
    """새 수익 등록"""
    try:
        async with get_mysql_session() as session:
            query = """
                INSERT INTO incomes (title, category, amount, source, description, 
                                   attachment_file, created_by, income_date)
                VALUES (:title, :category, :amount, :source, :description,
                        :attachment_file, :created_by, :income_date)
            """
            
            params = {
                "title": income_data.title,
                "category": income_data.category,
                "amount": income_data.amount,
                "source": income_data.source,
                "description": income_data.description,
                "attachment_file": income_data.attachment_file,
                "created_by": user["id"],
                "income_date": income_data.income_date
            }
            
            result = await session.execute(text(query), params)
            income_id = result.lastrowid
            
            logger.info(f"✅ 새 수익 등록: {income_data.title} (ID: {income_id}, 금액: {income_data.amount:,}원)")
            
            return {
                "success": True,
                "message": "수익이 성공적으로 등록되었습니다",
                "income_id": income_id
            }
            
    except Exception as e:
        logger.error(f"수익 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="수익 등록에 실패했습니다")

# === 대시보드 통계 API ===

@router.get("/api/business/dashboard-stats")
async def get_dashboard_stats(
    request: Request,
    month: Optional[str] = None,
    user: Dict = Depends(require_auth)
):
    """비즈니스 대시보드 통계"""
    try:
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        async with get_mysql_session() as session:
            # 업무 통계
            task_stats = await session.execute(text("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM tasks 
                WHERE DATE_FORMAT(created_at, '%Y-%m') = :month
                GROUP BY status
            """), {"month": month})
            
            tasks_by_status = {}
            total_tasks = 0
            for row in task_stats.fetchall():
                tasks_by_status[row[0]] = row[1]
                total_tasks += row[1]
            
            # 지출 통계
            expense_stats = await session.execute(text("""
                SELECT 
                    SUM(amount) as total_amount,
                    COUNT(*) as total_count,
                    category
                FROM expenses 
                WHERE DATE_FORMAT(expense_date, '%Y-%m') = :month
                  AND status IN ('승인', '정산')
                GROUP BY category
                ORDER BY total_amount DESC
            """), {"month": month})
            
            expenses_by_category = []
            total_expenses = 0
            for row in expense_stats.fetchall():
                amount = float(row[0]) if row[0] else 0
                expenses_by_category.append({
                    "category": row[2],
                    "amount": amount,
                    "count": row[1]
                })
                total_expenses += amount
            
            # 수익 통계
            income_stats = await session.execute(text("""
                SELECT 
                    SUM(amount) as total_amount,
                    COUNT(*) as total_count,
                    category
                FROM incomes 
                WHERE DATE_FORMAT(income_date, '%Y-%m') = :month
                GROUP BY category
                ORDER BY total_amount DESC
            """), {"month": month})
            
            incomes_by_category = []
            total_incomes = 0
            for row in income_stats.fetchall():
                amount = float(row[0]) if row[0] else 0
                incomes_by_category.append({
                    "category": row[2],
                    "amount": amount,
                    "count": row[1]
                })
                total_incomes += amount
            
            # 순이익 계산
            net_profit = total_incomes - total_expenses
            
            return {
                "success": True,
                "month": month,
                "summary": {
                    "total_tasks": total_tasks,
                    "total_expenses": total_expenses,
                    "total_incomes": total_incomes,
                    "net_profit": net_profit,
                    "profit_margin": (net_profit / total_incomes * 100) if total_incomes > 0 else 0
                },
                "tasks_by_status": tasks_by_status,
                "expenses_by_category": expenses_by_category,
                "incomes_by_category": incomes_by_category
            }
            
    except Exception as e:
        logger.error(f"대시보드 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="대시보드 통계 조회에 실패했습니다")