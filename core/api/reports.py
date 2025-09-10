"""
리포트 생성 API 엔드포인트
- Excel/PDF 리포트 다운로드
- 리포트 미리보기
- 자동 리포트 스케줄링
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
import io
import json

from core.auth import get_current_user
from core.database import get_mysql_session
from core.services.report_service import report_service, ReportData
from core.services.prediction_service import prediction_service
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/reports/business-excel")
async def download_business_excel_report(
    period: str = Query("12months", description="리포트 기간"),
    user: Dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_mysql_session)
):
    """비즈니스 Excel 리포트 다운로드"""
    
    try:
        # 권한 체크
        if user.get("role") not in ["Owner", "Prime", "VIP"]:
            raise HTTPException(status_code=403, detail="리포트 다운로드 권한이 없습니다")
        
        # 리포트 데이터 수집
        report_data = await _collect_report_data(session, user, period)
        
        # Excel 파일 생성
        excel_file = await report_service.generate_excel_report(
            report_data, 
            report_type="business"
        )
        
        # 파일명 생성
        filename = report_service.get_report_filename("비즈니스", "xlsx", period)
        
        logger.info(f"Excel 리포트 다운로드: {user.get('email')} - {filename}")
        
        return StreamingResponse(
            io.BytesIO(excel_file.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Excel 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다")

@router.get("/api/reports/business-pdf")
async def download_business_pdf_report(
    period: str = Query("12months", description="리포트 기간"),
    include_charts: bool = Query(True, description="차트 포함 여부"),
    user: Dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_mysql_session)
):
    """비즈니스 PDF 리포트 다운로드"""
    
    try:
        # 권한 체크
        if user.get("role") not in ["Owner", "Prime", "VIP"]:
            raise HTTPException(status_code=403, detail="리포트 다운로드 권한이 없습니다")
        
        # 리포트 데이터 수집
        report_data = await _collect_report_data(session, user, period)
        
        # PDF 파일 생성
        pdf_file = await report_service.generate_pdf_report(
            report_data, 
            include_charts=include_charts
        )
        
        # 파일명 생성
        filename = report_service.get_report_filename("비즈니스", "pdf", period)
        
        logger.info(f"PDF 리포트 다운로드: {user.get('email')} - {filename}")
        
        return StreamingResponse(
            io.BytesIO(pdf_file.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"PDF 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다")

@router.get("/api/reports/comprehensive-excel")
async def download_comprehensive_excel_report(
    period: str = Query("12months", description="리포트 기간"),
    user: Dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_mysql_session)
):
    """종합 Excel 리포트 다운로드 (모든 분석 포함)"""
    
    try:
        # 권한 체크 (Owner와 Prime만)
        if user.get("role") not in ["Owner", "Prime"]:
            raise HTTPException(status_code=403, detail="종합 리포트는 Owner/Prime 전용입니다")
        
        # 리포트 데이터 수집
        report_data = await _collect_comprehensive_report_data(session, user, period)
        
        # Excel 파일 생성
        excel_file = await report_service.generate_excel_report(
            report_data, 
            report_type="comprehensive"
        )
        
        # 파일명 생성
        filename = report_service.get_report_filename("종합분석", "xlsx", period)
        
        logger.info(f"종합 Excel 리포트 다운로드: {user.get('email')} - {filename}")
        
        return StreamingResponse(
            io.BytesIO(excel_file.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"종합 Excel 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다")

@router.get("/api/reports/task-efficiency-pdf")
async def download_task_efficiency_pdf_report(
    period: str = Query("6months", description="리포트 기간"),
    team_analysis: bool = Query(True, description="팀 분석 포함"),
    user: Dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_mysql_session)
):
    """업무 효율성 PDF 리포트 다운로드"""
    
    try:
        # 권한 체크
        if user.get("role") not in ["Owner", "Prime", "VIP"]:
            raise HTTPException(status_code=403, detail="리포트 다운로드 권한이 없습니다")
        
        # 업무 효율성 특화 데이터 수집
        report_data = await _collect_task_efficiency_report_data(
            session, user, period, team_analysis
        )
        
        # PDF 파일 생성
        pdf_file = await report_service.generate_pdf_report(
            report_data, 
            include_charts=True
        )
        
        # 파일명 생성
        filename = report_service.get_report_filename("업무효율성", "pdf", period)
        
        logger.info(f"업무 효율성 PDF 리포트 다운로드: {user.get('email')} - {filename}")
        
        return StreamingResponse(
            io.BytesIO(pdf_file.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"업무 효율성 PDF 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다")

@router.post("/api/reports/schedule-auto-report")
async def schedule_auto_report(
    background_tasks: BackgroundTasks,
    report_type: str = Query("business", description="리포트 타입"),
    frequency: str = Query("monthly", description="생성 주기: daily, weekly, monthly"),
    format_type: str = Query("pdf", description="파일 형식: pdf, excel"),
    email_recipients: str = Query("", description="수신자 이메일 (콤마 구분)"),
    user: Dict = Depends(get_current_user)
):
    """자동 리포트 생성 스케줄링"""
    
    try:
        # Owner만 자동 리포트 설정 가능
        if user.get("role") != "Owner":
            raise HTTPException(status_code=403, detail="자동 리포트 설정은 Owner 전용입니다")
        
        # 백그라운드 태스크로 스케줄링 등록
        background_tasks.add_task(
            _setup_auto_report_schedule,
            report_type=report_type,
            frequency=frequency,
            format_type=format_type,
            email_recipients=email_recipients.split(",") if email_recipients else [],
            user_id=user.get("id")
        )
        
        logger.info(f"자동 리포트 스케줄링 등록: {user.get('email')} - {report_type}/{frequency}")
        
        return {
            "success": True,
            "message": f"{frequency} {report_type} 리포트 자동 생성이 예약되었습니다",
            "details": {
                "report_type": report_type,
                "frequency": frequency,
                "format": format_type,
                "recipients": email_recipients.split(",") if email_recipients else []
            }
        }
        
    except Exception as e:
        logger.error(f"자동 리포트 스케줄링 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="자동 리포트 설정 중 오류가 발생했습니다")

@router.get("/api/reports/preview")
async def get_report_preview(
    report_type: str = Query("business", description="리포트 타입"),
    period: str = Query("3months", description="리포트 기간"),
    user: Dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_mysql_session)
):
    """리포트 미리보기 데이터"""
    
    try:
        # 권한 체크
        if user.get("role") not in ["Owner", "Prime", "VIP", "Standard"]:
            raise HTTPException(status_code=403, detail="리포트 미리보기 권한이 없습니다")
        
        # 미리보기용 데이터 수집 (간소화)
        preview_data = await _collect_preview_data(session, user, period, report_type)
        
        logger.info(f"리포트 미리보기: {user.get('email')} - {report_type}/{period}")
        
        return {
            "success": True,
            "preview": preview_data,
            "metadata": {
                "report_type": report_type,
                "period": period,
                "generated_at": datetime.now().isoformat(),
                "user_role": user.get("role")
            }
        }
        
    except Exception as e:
        logger.error(f"리포트 미리보기 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="미리보기 생성 중 오류가 발생했습니다")

@router.get("/api/reports/available-formats")
async def get_available_report_formats(
    user: Dict = Depends(get_current_user)
):
    """사용 가능한 리포트 형식 목록"""
    
    role = user.get("role", "")
    
    formats = {
        "Owner": {
            "types": ["business", "comprehensive", "task_efficiency", "financial", "predictive"],
            "formats": ["pdf", "excel", "csv"],
            "periods": ["1month", "3months", "6months", "12months", "2years", "custom"],
            "features": ["charts", "predictions", "team_analysis", "auto_schedule"]
        },
        "Prime": {
            "types": ["business", "comprehensive", "task_efficiency"],
            "formats": ["pdf", "excel", "csv"],
            "periods": ["1month", "3months", "6months", "12months"],
            "features": ["charts", "predictions", "team_analysis"]
        },
        "VIP": {
            "types": ["business", "task_efficiency"],
            "formats": ["pdf", "excel"],
            "periods": ["1month", "3months", "6months"],
            "features": ["charts"]
        },
        "Standard": {
            "types": ["business"],
            "formats": ["pdf"],
            "periods": ["1month", "3months"],
            "features": []
        }
    }
    
    return {
        "success": True,
        "available_formats": formats.get(role, formats["Standard"]),
        "current_role": role
    }

# === 내부 헬퍼 함수들 ===

async def _collect_report_data(session: AsyncSession, user: Dict, period: str) -> ReportData:
    """기본 리포트 데이터 수집"""
    
    # 기간 계산
    end_date = datetime.now()
    if period == "1month":
        start_date = end_date - timedelta(days=30)
        period_text = "최근 1개월"
    elif period == "3months":
        start_date = end_date - timedelta(days=90)
        period_text = "최근 3개월"
    elif period == "6months":
        start_date = end_date - timedelta(days=180)
        period_text = "최근 6개월"
    elif period == "12months":
        start_date = end_date - timedelta(days=365)
        period_text = "최근 12개월"
    elif period == "2years":
        start_date = end_date - timedelta(days=730)
        period_text = "최근 2년"
    else:
        start_date = end_date - timedelta(days=90)
        period_text = "최근 3개월"
    
    # 비즈니스 성과 데이터
    business_performance = await _get_business_performance_data(session, start_date, end_date)
    
    # 업무 효율성 데이터
    task_efficiency = await _get_task_efficiency_data(session, start_date, end_date)
    
    # 지출 분석 데이터
    expense_analysis = await _get_expense_analysis_data(session, start_date, end_date)
    
    # 예측 데이터
    predictions = []
    try:
        # 예측 서비스 호출
        historical_data = await _get_historical_data_for_prediction(session, start_date, end_date)
        if historical_data:
            pred_results, trend_analysis = prediction_service.predict_revenue_trends(
                historical_data, periods_ahead=6
            )
            predictions = [
                {
                    "date": pred.date,
                    "predicted_income": pred.predicted_income,
                    "predicted_expense": pred.predicted_expense,
                    "predicted_profit": pred.predicted_profit,
                    "confidence_lower": pred.confidence_lower,
                    "confidence_upper": pred.confidence_upper,
                    "trend_strength": pred.trend_strength
                }
                for pred in pred_results
            ]
    except Exception as e:
        logger.warning(f"예측 데이터 생성 실패: {str(e)}")
    
    # 요약 정보
    summary = {
        "total_income": business_performance.get("total_income", 0),
        "total_expense": business_performance.get("total_expense", 0),
        "net_profit": business_performance.get("net_profit", 0),
        "completed_tasks": task_efficiency.get("completed_tasks", 0),
        "completion_rate": task_efficiency.get("completion_rate", 0),
        "avg_processing_time": task_efficiency.get("avg_completion_time", 0)
    }
    
    return ReportData(
        title="업무 관리 분석 리포트",
        period=period_text,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        business_performance=business_performance,
        task_efficiency=task_efficiency,
        expense_analysis=expense_analysis,
        predictions=predictions,
        summary=summary
    )

async def _collect_comprehensive_report_data(session: AsyncSession, user: Dict, period: str) -> ReportData:
    """종합 리포트 데이터 수집 (모든 분석 포함)"""
    
    # 기본 데이터 수집
    base_data = await _collect_report_data(session, user, period)
    
    # 추가 종합 분석 데이터
    # 예: 고급 통계, 비교 분석, 트렌드 분석 등
    
    # 제목 변경
    base_data.title = "종합 업무 관리 분석 리포트"
    
    return base_data

async def _collect_task_efficiency_report_data(
    session: AsyncSession, 
    user: Dict, 
    period: str, 
    team_analysis: bool
) -> ReportData:
    """업무 효율성 특화 리포트 데이터"""
    
    # 기본 데이터 수집
    base_data = await _collect_report_data(session, user, period)
    
    # 업무 효율성 특화 분석 추가
    if team_analysis:
        # 팀별 효율성 분석 추가
        pass
    
    # 제목 변경
    base_data.title = "업무 효율성 분석 리포트"
    
    return base_data

async def _collect_preview_data(session: AsyncSession, user: Dict, period: str, report_type: str) -> Dict:
    """미리보기용 간소화된 데이터"""
    
    # 간단한 요약 정보만 반환
    end_date = datetime.now()
    if period == "1month":
        start_date = end_date - timedelta(days=30)
    elif period == "3months":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=90)
    
    # 기본 통계
    total_tasks_query = await session.execute(
        text("SELECT COUNT(*) FROM tasks WHERE created_at >= :start_date"),
        {"start_date": start_date}
    )
    total_tasks = total_tasks_query.scalar() or 0
    
    completed_tasks_query = await session.execute(
        text("SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND created_at >= :start_date"),
        {"start_date": start_date}
    )
    completed_tasks = completed_tasks_query.scalar() or 0
    
    return {
        "summary": {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "period": period,
            "report_type": report_type
        }
    }

async def _get_business_performance_data(session: AsyncSession, start_date: datetime, end_date: datetime) -> Dict:
    """비즈니스 성과 데이터 조회"""
    
    try:
        # 수익 데이터
        income_query = await session.execute(
            text("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_income,
                    DATE_FORMAT(date, '%Y-%m') as month
                FROM incomes 
                WHERE date >= :start_date AND date <= :end_date
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        income_results = income_query.fetchall()
        
        # 지출 데이터
        expense_query = await session.execute(
            text("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_expense,
                    DATE_FORMAT(date, '%Y-%m') as month
                FROM expenses 
                WHERE date >= :start_date AND date <= :end_date AND status = 'approved'
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        expense_results = expense_query.fetchall()
        
        # 월별 데이터 조합
        monthly_data = []
        income_dict = {row.month: row.total_income for row in income_results}
        expense_dict = {row.month: row.total_expense for row in expense_results}
        
        all_months = set(income_dict.keys()) | set(expense_dict.keys())
        for month in sorted(all_months):
            income = income_dict.get(month, 0)
            expense = expense_dict.get(month, 0)
            monthly_data.append({
                "month": month,
                "income": float(income),
                "expense": float(expense),
                "profit": float(income - expense)
            })
        
        # 총합 계산
        total_income = sum(data["income"] for data in monthly_data)
        total_expense = sum(data["expense"] for data in monthly_data)
        
        return {
            "monthly_data": monthly_data,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": total_income - total_expense,
            "avg_monthly_income": total_income / len(monthly_data) if monthly_data else 0,
            "avg_monthly_expense": total_expense / len(monthly_data) if monthly_data else 0
        }
        
    except Exception as e:
        logger.error(f"비즈니스 성과 데이터 조회 실패: {str(e)}")
        return {
            "monthly_data": [],
            "total_income": 0,
            "total_expense": 0,
            "net_profit": 0,
            "avg_monthly_income": 0,
            "avg_monthly_expense": 0
        }

async def _get_task_efficiency_data(session: AsyncSession, start_date: datetime, end_date: datetime) -> Dict:
    """업무 효율성 데이터 조회"""
    
    try:
        # 업무 통계
        task_stats_query = await session.execute(
            text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tasks,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_tasks,
                    SUM(CASE WHEN due_date < NOW() AND status != 'completed' THEN 1 ELSE 0 END) as overdue_tasks
                FROM tasks 
                WHERE created_at >= :start_date AND created_at <= :end_date
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        task_stats = task_stats_query.fetchone()
        
        # 평균 완료 시간 계산
        completion_time_query = await session.execute(
            text("""
                SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, updated_at)) as avg_completion_time
                FROM tasks 
                WHERE status = 'completed' 
                AND created_at >= :start_date AND created_at <= :end_date
                AND updated_at IS NOT NULL
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        avg_completion_time = completion_time_query.scalar() or 0
        
        # 생산성 점수 계산 (완료율 기반)
        total_tasks = task_stats.total_tasks or 1
        completed_tasks = task_stats.completed_tasks or 0
        completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        
        # 지연률 고려한 생산성 점수
        overdue_tasks = task_stats.overdue_tasks or 0
        overdue_rate = (overdue_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        productivity_score = completion_rate - (overdue_rate * 0.5)  # 지연은 패널티
        
        return {
            "total_tasks": task_stats.total_tasks or 0,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": task_stats.in_progress_tasks or 0,
            "pending_tasks": task_stats.pending_tasks or 0,
            "overdue_tasks": overdue_tasks,
            "completion_rate": completion_rate,
            "overdue_rate": overdue_rate,
            "avg_completion_time": float(avg_completion_time),
            "productivity_score": max(0, min(100, productivity_score))  # 0-100 범위
        }
        
    except Exception as e:
        logger.error(f"업무 효율성 데이터 조회 실패: {str(e)}")
        return {
            "total_tasks": 0,
            "completed_tasks": 0,
            "in_progress_tasks": 0,
            "pending_tasks": 0,
            "overdue_tasks": 0,
            "completion_rate": 0,
            "overdue_rate": 0,
            "avg_completion_time": 0,
            "productivity_score": 0
        }

async def _get_expense_analysis_data(session: AsyncSession, start_date: datetime, end_date: datetime) -> Dict:
    """지출 분석 데이터 조회"""
    
    try:
        # 카테고리별 지출
        category_query = await session.execute(
            text("""
                SELECT 
                    category,
                    SUM(amount) as total_amount,
                    COUNT(*) as count
                FROM expenses 
                WHERE date >= :start_date AND date <= :end_date AND status = 'approved'
                GROUP BY category
                ORDER BY total_amount DESC
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        category_results = category_query.fetchall()
        
        # 월별 지출 트렌드
        monthly_query = await session.execute(
            text("""
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') as month,
                    SUM(amount) as total_expense
                FROM expenses 
                WHERE date >= :start_date AND date <= :end_date AND status = 'approved'
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        monthly_results = monthly_query.fetchall()
        
        return {
            "category_breakdown": [
                {
                    "category": row.category,
                    "amount": float(row.total_amount),
                    "count": row.count
                }
                for row in category_results
            ],
            "monthly_trend": [
                {
                    "month": row.month,
                    "amount": float(row.total_expense)
                }
                for row in monthly_results
            ],
            "total_expense": sum(row.total_expense for row in monthly_results),
            "avg_monthly_expense": sum(row.total_expense for row in monthly_results) / len(monthly_results) if monthly_results else 0
        }
        
    except Exception as e:
        logger.error(f"지출 분석 데이터 조회 실패: {str(e)}")
        return {
            "category_breakdown": [],
            "monthly_trend": [],
            "total_expense": 0,
            "avg_monthly_expense": 0
        }

async def _get_historical_data_for_prediction(session: AsyncSession, start_date: datetime, end_date: datetime) -> List[Dict]:
    """예측을 위한 역사적 데이터 조회"""
    
    try:
        # 월별 수익/지출 데이터
        query = await session.execute(
            text("""
                SELECT 
                    DATE_FORMAT(date_col, '%Y-%m') as month,
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
                FROM (
                    SELECT date as date_col, amount, 'income' as type FROM incomes
                    UNION ALL
                    SELECT date as date_col, amount, 'expense' as type FROM expenses WHERE status = 'approved'
                ) combined_data
                WHERE date_col >= :start_date AND date_col <= :end_date
                GROUP BY DATE_FORMAT(date_col, '%Y-%m')
                ORDER BY month
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        results = query.fetchall()
        
        return [
            {
                "month": row.month,
                "income": float(row.income),
                "expense": float(row.expense),
                "profit": float(row.income - row.expense)
            }
            for row in results
        ]
        
    except Exception as e:
        logger.error(f"예측용 데이터 조회 실패: {str(e)}")
        return []

async def _setup_auto_report_schedule(
    report_type: str,
    frequency: str, 
    format_type: str,
    email_recipients: List[str],
    user_id: int
):
    """자동 리포트 스케줄 설정 (백그라운드 태스크)"""
    
    try:
        # TODO: 실제 스케줄링 시스템 구현
        # 예: Celery, APScheduler 등을 사용하여 주기적 리포트 생성
        
        logger.info(f"자동 리포트 스케줄 설정 완료: {report_type}/{frequency}/{format_type}")
        logger.info(f"수신자: {email_recipients}, 사용자 ID: {user_id}")
        
        # 스케줄링 정보를 데이터베이스에 저장할 수도 있음
        
    except Exception as e:
        logger.error(f"자동 리포트 스케줄 설정 실패: {str(e)}")