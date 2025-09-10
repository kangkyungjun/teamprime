"""
분석 및 리포팅 API 엔드포인트
- 비즈니스 성과 분석
- 업무 효율성 분석  
- 지출 패턴 분석
- 수익 예측 및 트렌드
- 리포트 생성
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy import text, func
import calendar
import json
from collections import defaultdict

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_current_user_from_request(request: Request):
    """요청에서 현재 사용자 정보 추출"""
    from core.auth.middleware import get_current_user
    return await get_current_user(request)

@router.get("/api/analytics/business-performance")
async def get_business_performance(
    request: Request,
    period: str = Query("12months", description="분석 기간: 3months, 6months, 12months, 2years"),
    user: Dict = Depends(get_current_user_from_request)
):
    """비즈니스 성과 분석 - 월별/분기별 수익 분석"""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from core.database.mysql_connection import get_mysql_connection
        
        # 기간 설정
        period_months = {
            "3months": 3,
            "6months": 6, 
            "12months": 12,
            "2years": 24
        }
        
        months = period_months.get(period, 12)
        start_date = datetime.now() - timedelta(days=months * 30)
        
        async with get_mysql_connection() as connection:
            
            # 월별 수익 분석
            income_query = text("""
                SELECT 
                    DATE_FORMAT(income_date, '%Y-%m') as month,
                    category,
                    COUNT(*) as count,
                    SUM(amount) as total_amount,
                    SUM(tax) as total_tax,
                    SUM(amount - tax) as net_amount
                FROM incomes 
                WHERE income_date >= :start_date
                GROUP BY DATE_FORMAT(income_date, '%Y-%m'), category
                ORDER BY month DESC, category
            """)
            
            income_result = await connection.execute(income_query, {"start_date": start_date})
            income_data = income_result.fetchall()
            
            # 월별 지출 분석
            expense_query = text("""
                SELECT 
                    DATE_FORMAT(expense_date, '%Y-%m') as month,
                    category,
                    status,
                    COUNT(*) as count,
                    SUM(amount) as total_amount
                FROM expenses 
                WHERE expense_date >= :start_date
                GROUP BY DATE_FORMAT(expense_date, '%Y-%m'), category, status
                ORDER BY month DESC, category
            """)
            
            expense_result = await connection.execute(expense_query, {"start_date": start_date})
            expense_data = expense_result.fetchall()
            
            # 업무 완료 분석 (생산성 지표)
            task_query = text("""
                SELECT 
                    DATE_FORMAT(updated_at, '%Y-%m') as month,
                    category,
                    status,
                    priority,
                    COUNT(*) as count,
                    AVG(estimated_hours) as avg_hours
                FROM tasks 
                WHERE updated_at >= :start_date
                GROUP BY DATE_FORMAT(updated_at, '%Y-%m'), category, status, priority
                ORDER BY month DESC
            """)
            
            task_result = await connection.execute(task_query, {"start_date": start_date})
            task_data = task_result.fetchall()
            
        # 데이터 가공
        monthly_summary = defaultdict(lambda: {
            'income': {'total': 0, 'tax': 0, 'net': 0, 'categories': {}},
            'expense': {'total': 0, 'approved': 0, 'categories': {}},
            'tasks': {'total': 0, 'completed': 0, 'productivity': 0}
        })
        
        # 수익 데이터 가공
        for row in income_data:
            month = row.month
            category = row.category
            monthly_summary[month]['income']['total'] += float(row.total_amount)
            monthly_summary[month]['income']['tax'] += float(row.total_tax or 0)
            monthly_summary[month]['income']['net'] += float(row.net_amount or 0)
            
            if category not in monthly_summary[month]['income']['categories']:
                monthly_summary[month]['income']['categories'][category] = 0
            monthly_summary[month]['income']['categories'][category] += float(row.total_amount)
        
        # 지출 데이터 가공
        for row in expense_data:
            month = row.month
            category = row.category
            status = row.status
            amount = float(row.total_amount)
            
            monthly_summary[month]['expense']['total'] += amount
            if status == 'approved':
                monthly_summary[month]['expense']['approved'] += amount
                
            if category not in monthly_summary[month]['expense']['categories']:
                monthly_summary[month]['expense']['categories'][category] = 0
            monthly_summary[month]['expense']['categories'][category] += amount
        
        # 업무 데이터 가공
        for row in task_data:
            month = row.month
            status = row.status
            count = row.count
            
            monthly_summary[month]['tasks']['total'] += count
            if status == 'completed':
                monthly_summary[month]['tasks']['completed'] += count
        
        # 생산성 계산
        for month in monthly_summary:
            total_tasks = monthly_summary[month]['tasks']['total']
            completed_tasks = monthly_summary[month]['tasks']['completed']
            if total_tasks > 0:
                monthly_summary[month]['tasks']['productivity'] = round((completed_tasks / total_tasks) * 100, 2)
        
        # 월별 정렬 및 최종 데이터 구성
        sorted_months = sorted(monthly_summary.keys(), reverse=True)
        
        # 트렌드 계산
        revenue_trend = []
        profit_trend = []
        productivity_trend = []
        
        for month in sorted_months:
            data = monthly_summary[month]
            revenue_trend.append({
                'month': month,
                'revenue': data['income']['total'],
                'expense': data['expense']['approved'],
                'profit': data['income']['net'] - data['expense']['approved']
            })
            
            productivity_trend.append({
                'month': month,
                'productivity': data['tasks']['productivity']
            })
        
        # 성과 지표 계산
        current_month = datetime.now().strftime('%Y-%m')
        previous_month = (datetime.now() - timedelta(days=32)).strftime('%Y-%m')
        
        current_profit = 0
        previous_profit = 0
        
        if current_month in monthly_summary:
            current_data = monthly_summary[current_month]
            current_profit = current_data['income']['net'] - current_data['expense']['approved']
            
        if previous_month in monthly_summary:
            previous_data = monthly_summary[previous_month]
            previous_profit = previous_data['income']['net'] - previous_data['expense']['approved']
        
        profit_growth = 0
        if previous_profit != 0:
            profit_growth = round(((current_profit - previous_profit) / abs(previous_profit)) * 100, 2)
        
        return {
            "success": True,
            "period": period,
            "analysis_period": f"{start_date.strftime('%Y-%m')} ~ {datetime.now().strftime('%Y-%m')}",
            "summary": {
                "total_months": len(sorted_months),
                "current_month_profit": current_profit,
                "previous_month_profit": previous_profit,
                "profit_growth_rate": profit_growth,
                "avg_monthly_revenue": sum(monthly_summary[m]['income']['total'] for m in monthly_summary) / len(monthly_summary) if monthly_summary else 0,
                "avg_monthly_expense": sum(monthly_summary[m]['expense']['approved'] for m in monthly_summary) / len(monthly_summary) if monthly_summary else 0,
                "avg_productivity": sum(monthly_summary[m]['tasks']['productivity'] for m in monthly_summary) / len(monthly_summary) if monthly_summary else 0
            },
            "monthly_data": dict(monthly_summary),
            "trends": {
                "revenue_profit": revenue_trend,
                "productivity": productivity_trend
            },
            "top_income_categories": get_top_categories([row.category for row in income_data]),
            "top_expense_categories": get_top_categories([row.category for row in expense_data])
        }
        
    except Exception as e:
        logger.error(f"비즈니스 성과 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 처리 중 오류가 발생했습니다: {str(e)}")

@router.get("/api/analytics/task-efficiency")
async def get_task_efficiency_analysis(
    request: Request,
    period: str = Query("30days", description="분석 기간: 7days, 30days, 90days"),
    user: Dict = Depends(get_current_user_from_request)
):
    """업무 효율성 분석 - 완료율, 지연률, 생산성 지표"""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from core.database.mysql_connection import get_mysql_connection
        
        # 기간 설정
        period_days = {
            "7days": 7,
            "30days": 30,
            "90days": 90
        }
        
        days = period_days.get(period, 30)
        start_date = datetime.now() - timedelta(days=days)
        
        async with get_mysql_connection() as connection:
            
            # 업무 효율성 분석 쿼리
            efficiency_query = text("""
                SELECT 
                    assignee_id,
                    category,
                    priority,
                    status,
                    estimated_hours,
                    start_date,
                    due_date,
                    created_at,
                    updated_at,
                    CASE 
                        WHEN due_date IS NOT NULL AND status = 'completed' AND updated_at > due_date 
                        THEN 1 ELSE 0 
                    END as is_delayed,
                    CASE 
                        WHEN status = 'completed' 
                        THEN DATEDIFF(updated_at, created_at) 
                        ELSE NULL 
                    END as completion_days
                FROM tasks 
                WHERE created_at >= :start_date
                ORDER BY created_at DESC
            """)
            
            result = await connection.execute(efficiency_query, {"start_date": start_date})
            task_data = result.fetchall()
            
            # 사용자별 업무 효율성 분석
            user_efficiency_query = text("""
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.role,
                    COUNT(t.id) as total_tasks,
                    SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN t.due_date IS NOT NULL AND t.status = 'completed' 
                             AND t.updated_at > t.due_date THEN 1 ELSE 0 END) as delayed_tasks,
                    AVG(CASE WHEN t.status = 'completed' 
                             THEN DATEDIFF(t.updated_at, t.created_at) ELSE NULL END) as avg_completion_days,
                    SUM(t.estimated_hours) as total_estimated_hours
                FROM users u
                LEFT JOIN tasks t ON u.id = t.assignee_id AND t.created_at >= :start_date
                GROUP BY u.id, u.username, u.role
                HAVING COUNT(t.id) > 0
                ORDER BY completed_tasks DESC
            """)
            
            user_result = await connection.execute(user_efficiency_query, {"start_date": start_date})
            user_data = user_result.fetchall()
        
        # 전체 통계 계산
        total_tasks = len(task_data)
        completed_tasks = sum(1 for task in task_data if task.status == 'completed')
        delayed_tasks = sum(task.is_delayed for task in task_data)
        
        completion_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
        delay_rate = round((delayed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
        
        # 평균 완료 시간
        completion_times = [task.completion_days for task in task_data if task.completion_days is not None]
        avg_completion_time = round(sum(completion_times) / len(completion_times), 1) if completion_times else 0
        
        # 카테고리별 분석
        category_stats = defaultdict(lambda: {'total': 0, 'completed': 0, 'delayed': 0})
        for task in task_data:
            category = task.category
            category_stats[category]['total'] += 1
            if task.status == 'completed':
                category_stats[category]['completed'] += 1
            if task.is_delayed:
                category_stats[category]['delayed'] += 1
        
        # 카테고리별 효율성 점수 계산
        category_efficiency = {}
        for category, stats in category_stats.items():
            if stats['total'] > 0:
                completion_rate = (stats['completed'] / stats['total']) * 100
                delay_rate = (stats['delayed'] / stats['total']) * 100
                efficiency_score = max(0, completion_rate - delay_rate)  # 완료율 - 지연률
                category_efficiency[category] = {
                    'total_tasks': stats['total'],
                    'completion_rate': round(completion_rate, 2),
                    'delay_rate': round(delay_rate, 2),
                    'efficiency_score': round(efficiency_score, 2)
                }
        
        # 우선순위별 분석
        priority_stats = defaultdict(lambda: {'total': 0, 'completed': 0, 'delayed': 0})
        for task in task_data:
            priority = task.priority
            priority_stats[priority]['total'] += 1
            if task.status == 'completed':
                priority_stats[priority]['completed'] += 1
            if task.is_delayed:
                priority_stats[priority]['delayed'] += 1
        
        # 사용자별 효율성 데이터 가공
        user_efficiency = []
        for user in user_data:
            total = user.total_tasks
            completed = user.completed_tasks
            delayed = user.delayed_tasks
            
            completion_rate = round((completed / total) * 100, 2) if total > 0 else 0
            delay_rate = round((delayed / total) * 100, 2) if total > 0 else 0
            efficiency_score = max(0, completion_rate - delay_rate)
            
            user_efficiency.append({
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role,
                'total_tasks': total,
                'completed_tasks': completed,
                'delayed_tasks': delayed,
                'completion_rate': completion_rate,
                'delay_rate': delay_rate,
                'efficiency_score': round(efficiency_score, 2),
                'avg_completion_days': round(float(user.avg_completion_days), 1) if user.avg_completion_days else 0,
                'total_estimated_hours': float(user.total_estimated_hours) if user.total_estimated_hours else 0
            })
        
        # 효율성 점수별 정렬
        user_efficiency.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
        return {
            "success": True,
            "period": period,
            "analysis_period": f"{start_date.strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
            "overall_stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "delayed_tasks": delayed_tasks,
                "completion_rate": completion_rate,
                "delay_rate": delay_rate,
                "avg_completion_time": avg_completion_time,
                "productivity_score": round(max(0, completion_rate - delay_rate), 2)
            },
            "category_efficiency": category_efficiency,
            "priority_analysis": {
                priority: {
                    'total': stats['total'],
                    'completion_rate': round((stats['completed'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0,
                    'delay_rate': round((stats['delayed'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0
                }
                for priority, stats in priority_stats.items()
            },
            "user_efficiency": user_efficiency,
            "insights": generate_efficiency_insights(category_efficiency, user_efficiency, completion_rate, delay_rate)
        }
        
    except Exception as e:
        logger.error(f"업무 효율성 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 처리 중 오류가 발생했습니다: {str(e)}")

@router.get("/api/analytics/expense-patterns")
async def get_expense_pattern_analysis(
    request: Request,
    period: str = Query("6months", description="분석 기간: 3months, 6months, 12months"),
    user: Dict = Depends(get_current_user_from_request)
):
    """지출 패턴 분석 및 예산 관리"""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from core.database.mysql_connection import get_mysql_connection
        
        # 기간 설정
        period_months = {"3months": 3, "6months": 6, "12months": 12}
        months = period_months.get(period, 6)
        start_date = datetime.now() - timedelta(days=months * 30)
        
        async with get_mysql_connection() as connection:
            
            # 지출 패턴 분석
            expense_pattern_query = text("""
                SELECT 
                    DATE_FORMAT(expense_date, '%Y-%m') as month,
                    category,
                    status,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MIN(amount) as min_amount,
                    MAX(amount) as max_amount,
                    DAYOFWEEK(expense_date) as day_of_week
                FROM expenses 
                WHERE expense_date >= :start_date
                GROUP BY DATE_FORMAT(expense_date, '%Y-%m'), category, status
                ORDER BY month DESC, total_amount DESC
            """)
            
            result = await connection.execute(expense_pattern_query, {"start_date": start_date})
            expense_data = result.fetchall()
            
            # 승인률 분석
            approval_query = text("""
                SELECT 
                    category,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
                    AVG(amount) as avg_amount,
                    SUM(CASE WHEN status = 'approved' THEN amount ELSE 0 END) as approved_amount
                FROM expenses 
                WHERE expense_date >= :start_date
                GROUP BY category
                ORDER BY total_requests DESC
            """)
            
            approval_result = await connection.execute(approval_query, {"start_date": start_date})
            approval_data = approval_result.fetchall()
            
            # 일별 지출 패턴
            daily_pattern_query = text("""
                SELECT 
                    DAYOFWEEK(expense_date) as day_of_week,
                    COUNT(*) as transaction_count,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount
                FROM expenses 
                WHERE expense_date >= :start_date AND status = 'approved'
                GROUP BY DAYOFWEEK(expense_date)
                ORDER BY day_of_week
            """)
            
            daily_result = await connection.execute(daily_pattern_query, {"start_date": start_date})
            daily_data = daily_result.fetchall()
        
        # 월별 지출 패턴 분석
        monthly_patterns = defaultdict(lambda: {'total': 0, 'categories': {}, 'approved': 0})
        
        for row in expense_data:
            month = row.month
            category = row.category
            status = row.status
            amount = float(row.total_amount)
            
            monthly_patterns[month]['total'] += amount
            if status == 'approved':
                monthly_patterns[month]['approved'] += amount
                
            if category not in monthly_patterns[month]['categories']:
                monthly_patterns[month]['categories'][category] = 0
            monthly_patterns[month]['categories'][category] += amount
        
        # 카테고리별 승인률 및 패턴
        category_analysis = {}
        for row in approval_data:
            category = row.category
            total_requests = row.total_requests
            approved_count = row.approved_count
            rejected_count = row.rejected_count
            
            approval_rate = round((approved_count / total_requests) * 100, 2) if total_requests > 0 else 0
            rejection_rate = round((rejected_count / total_requests) * 100, 2) if total_requests > 0 else 0
            
            category_analysis[category] = {
                'total_requests': total_requests,
                'approval_rate': approval_rate,
                'rejection_rate': rejection_rate,
                'avg_amount': round(float(row.avg_amount), 2),
                'approved_amount': float(row.approved_amount),
                'risk_level': 'high' if approval_rate < 70 else ('medium' if approval_rate < 85 else 'low')
            }
        
        # 요일별 지출 패턴
        days_of_week = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
        daily_patterns = {}
        
        for row in daily_data:
            day_index = row.day_of_week - 1  # MySQL DAYOFWEEK는 1부터 시작
            day_name = days_of_week[day_index]
            daily_patterns[day_name] = {
                'transaction_count': row.transaction_count,
                'total_amount': float(row.total_amount),
                'avg_amount': round(float(row.avg_amount), 2)
            }
        
        # 예산 추천 계산
        total_months = len(monthly_patterns)
        avg_monthly_expense = sum(monthly_patterns[m]['approved'] for m in monthly_patterns) / total_months if total_months > 0 else 0
        
        # 카테고리별 예산 추천
        category_budgets = {}
        for category, analysis in category_analysis.items():
            monthly_avg = analysis['approved_amount'] / total_months if total_months > 0 else 0
            # 승인률을 고려한 버퍼 추가
            buffer_rate = 1.2 if analysis['approval_rate'] > 90 else 1.5
            recommended_budget = monthly_avg * buffer_rate
            
            category_budgets[category] = {
                'current_monthly_avg': round(monthly_avg, 2),
                'recommended_budget': round(recommended_budget, 2),
                'buffer_rate': buffer_rate,
                'confidence': 'high' if analysis['total_requests'] >= 10 else 'medium'
            }
        
        # 지출 트렌드 예측
        sorted_months = sorted(monthly_patterns.keys())
        monthly_trend = []
        for month in sorted_months:
            monthly_trend.append({
                'month': month,
                'total_expense': monthly_patterns[month]['approved'],
                'categories': monthly_patterns[month]['categories']
            })
        
        # 이상 지출 감지 (평균의 150% 이상인 경우)
        anomalies = []
        if len(monthly_trend) >= 3:
            recent_avg = sum(t['total_expense'] for t in monthly_trend[-3:]) / 3
            for trend in monthly_trend:
                if trend['total_expense'] > recent_avg * 1.5:
                    anomalies.append({
                        'month': trend['month'],
                        'amount': trend['total_expense'],
                        'deviation': round(((trend['total_expense'] - recent_avg) / recent_avg) * 100, 2)
                    })
        
        return {
            "success": True,
            "period": period,
            "analysis_period": f"{start_date.strftime('%Y-%m')} ~ {datetime.now().strftime('%Y-%m')}",
            "summary": {
                "total_months_analyzed": total_months,
                "avg_monthly_expense": round(avg_monthly_expense, 2),
                "total_approved_expense": sum(monthly_patterns[m]['approved'] for m in monthly_patterns),
                "most_expensive_category": max(category_analysis.items(), key=lambda x: x[1]['approved_amount'])[0] if category_analysis else None,
                "highest_risk_category": min(category_analysis.items(), key=lambda x: x[1]['approval_rate'])[0] if category_analysis else None
            },
            "monthly_patterns": dict(monthly_patterns),
            "category_analysis": category_analysis,
            "daily_patterns": daily_patterns,
            "budget_recommendations": category_budgets,
            "expense_trends": monthly_trend,
            "anomalies": anomalies,
            "insights": generate_expense_insights(category_analysis, monthly_patterns, daily_patterns)
        }
        
    except Exception as e:
        logger.error(f"지출 패턴 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 처리 중 오류가 발생했습니다: {str(e)}")

def get_top_categories(category_list, limit=5):
    """상위 카테고리 추출"""
    from collections import Counter
    category_counts = Counter(category_list)
    return [{"category": cat, "count": count} for cat, count in category_counts.most_common(limit)]

def generate_efficiency_insights(category_efficiency, user_efficiency, completion_rate, delay_rate):
    """업무 효율성 인사이트 생성"""
    insights = []
    
    # 전체 효율성 평가
    if completion_rate >= 80:
        insights.append("✅ 전체 업무 완료율이 우수합니다 (80% 이상)")
    elif completion_rate >= 60:
        insights.append("⚠️ 업무 완료율이 보통 수준입니다. 개선이 필요합니다")
    else:
        insights.append("🚨 업무 완료율이 낮습니다. 즉시 개선이 필요합니다")
    
    # 지연률 평가
    if delay_rate <= 10:
        insights.append("✅ 업무 지연률이 낮아 일정 관리가 잘 되고 있습니다")
    elif delay_rate <= 20:
        insights.append("⚠️ 업무 지연률이 다소 높습니다. 일정 관리 개선을 권장합니다")
    else:
        insights.append("🚨 업무 지연률이 높습니다. 일정 관리 시스템을 점검해주세요")
    
    # 카테고리별 인사이트
    if category_efficiency:
        best_category = max(category_efficiency.items(), key=lambda x: x[1]['efficiency_score'])
        worst_category = min(category_efficiency.items(), key=lambda x: x[1]['efficiency_score'])
        
        insights.append(f"🏆 가장 효율적인 업무 분야: {best_category[0]} ({best_category[1]['efficiency_score']}점)")
        insights.append(f"📉 개선이 필요한 업무 분야: {worst_category[0]} ({worst_category[1]['efficiency_score']}점)")
    
    # 사용자별 인사이트
    if user_efficiency and len(user_efficiency) > 1:
        top_performer = user_efficiency[0]
        insights.append(f"🌟 최고 성과자: {top_performer['username']} (효율성 점수: {top_performer['efficiency_score']}점)")
    
    return insights

@router.get("/api/analytics/revenue-prediction")
async def get_revenue_prediction(
    request: Request,
    periods: int = Query(6, description="예측할 기간 (개월)", ge=1, le=12),
    user: Dict = Depends(get_current_user_from_request)
):
    """수익 예측 및 트렌드 분석"""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        from core.database.mysql_connection import get_mysql_connection
        from core.services.prediction_service import prediction_service
        
        # 과거 24개월 데이터 수집 (예측을 위한 충분한 데이터)
        start_date = datetime.now() - timedelta(days=24 * 30)
        
        async with get_mysql_connection() as connection:
            
            # 월별 수익/지출/이익 데이터
            revenue_query = text("""
                SELECT 
                    DATE_FORMAT(income_date, '%Y-%m') as month,
                    SUM(amount - IFNULL(tax, 0)) as income,
                    0 as expense,
                    SUM(amount - IFNULL(tax, 0)) as profit
                FROM incomes 
                WHERE income_date >= :start_date
                GROUP BY DATE_FORMAT(income_date, '%Y-%m')
                
                UNION ALL
                
                SELECT 
                    DATE_FORMAT(expense_date, '%Y-%m') as month,
                    0 as income,
                    SUM(amount) as expense,
                    -SUM(amount) as profit
                FROM expenses 
                WHERE expense_date >= :start_date AND status = 'approved'
                GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
                
                ORDER BY month
            """)
            
            result = await connection.execute(revenue_query, {"start_date": start_date})
            raw_data = result.fetchall()
        
        # 데이터 집계 (월별로 수익과 지출 합계)
        monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0, 'profit': 0})
        
        for row in raw_data:
            month = row.month
            monthly_data[month]['income'] += float(row.income)
            monthly_data[month]['expense'] += float(row.expense)
            monthly_data[month]['profit'] += float(row.profit)
        
        # 최종 월별 순이익 계산
        historical_data = []
        for month in sorted(monthly_data.keys()):
            data = monthly_data[month]
            net_profit = data['income'] - data['expense']
            historical_data.append({
                'month': month,
                'income': data['income'],
                'expense': data['expense'], 
                'profit': net_profit
            })
        
        if len(historical_data) < 3:
            return {
                "success": False,
                "message": "예측을 위한 충분한 데이터가 없습니다. 최소 3개월의 데이터가 필요합니다.",
                "data_points": len(historical_data)
            }
        
        # 예측 수행
        predictions, trend_analysis = prediction_service.predict_revenue_trends(
            historical_data, periods
        )
        
        # 현재 데이터 요약
        current_summary = {
            'total_months': len(historical_data),
            'avg_monthly_income': sum(d['income'] for d in historical_data) / len(historical_data),
            'avg_monthly_expense': sum(d['expense'] for d in historical_data) / len(historical_data),
            'avg_monthly_profit': sum(d['profit'] for d in historical_data) / len(historical_data),
            'last_month_profit': historical_data[-1]['profit'] if historical_data else 0
        }
        
        # 비즈니스 인사이트 생성
        insights = prediction_service.generate_business_insights(
            predictions, trend_analysis, {
                'profits': [d['profit'] for d in historical_data]
            }
        )
        
        # 예측 정확도 평가 (과거 데이터로 검증)
        accuracy_score = calculate_prediction_accuracy(historical_data) if len(historical_data) >= 6 else 0
        
        # 리스크 분석
        risk_analysis = analyze_prediction_risks(predictions, trend_analysis)
        
        return {
            "success": True,
            "prediction_period": f"{periods}개월",
            "model_info": {
                "type": "Linear Regression with Seasonality",
                "data_points_used": len(historical_data),
                "accuracy_score": round(accuracy_score, 2),
                "confidence_level": "95%"
            },
            "historical_summary": current_summary,
            "trend_analysis": {
                "direction": trend_analysis.trend_direction,
                "strength": round(trend_analysis.trend_strength, 2),
                "growth_rate": round(trend_analysis.growth_rate, 2),
                "volatility": round(trend_analysis.volatility, 2),
                "seasonality_detected": trend_analysis.seasonality_detected,
                "seasonal_pattern": trend_analysis.seasonal_pattern
            },
            "predictions": [
                {
                    "date": pred.date,
                    "predicted_income": round(pred.predicted_income, 2),
                    "predicted_expense": round(pred.predicted_expense, 2),
                    "predicted_profit": round(pred.predicted_profit, 2),
                    "confidence_lower": round(pred.confidence_lower, 2),
                    "confidence_upper": round(pred.confidence_upper, 2),
                    "trend_strength": round(pred.trend_strength, 2)
                }
                for pred in predictions
            ],
            "risk_analysis": risk_analysis,
            "business_insights": insights,
            "recommendations": generate_strategic_recommendations(
                trend_analysis, predictions, current_summary
            )
        }
        
    except Exception as e:
        logger.error(f"수익 예측 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"예측 분석 중 오류가 발생했습니다: {str(e)}")

def calculate_prediction_accuracy(historical_data: List[Dict]) -> float:
    """예측 모델의 정확도 계산 (과거 데이터로 검증)"""
    
    if len(historical_data) < 6:
        return 0
    
    # 과거 데이터의 후반부를 테스트 세트로 사용
    train_size = len(historical_data) // 2
    train_data = historical_data[:train_size]
    test_data = historical_data[train_size:]
    
    try:
        from core.services.prediction_service import prediction_service
        
        # 훈련 데이터로 예측
        predictions, _ = prediction_service.predict_revenue_trends(train_data, len(test_data))
        
        # 실제값과 예측값 비교
        actual_profits = [d['profit'] for d in test_data]
        predicted_profits = [p.predicted_profit for p in predictions[:len(actual_profits)]]
        
        # MAPE (Mean Absolute Percentage Error) 계산
        mape_errors = []
        for actual, predicted in zip(actual_profits, predicted_profits):
            if actual != 0:
                mape_errors.append(abs((actual - predicted) / actual))
        
        if mape_errors:
            mape = sum(mape_errors) / len(mape_errors)
            accuracy = max(0, (1 - mape) * 100)  # MAPE를 정확도로 변환
        else:
            accuracy = 0
        
        return min(100, accuracy)  # 최대 100%
        
    except Exception as e:
        logger.error(f"정확도 계산 오류: {str(e)}")
        return 0

def analyze_prediction_risks(predictions: List, trend_analysis) -> Dict:
    """예측 리스크 분석"""
    
    if not predictions:
        return {"overall_risk": "low", "risk_factors": []}
    
    risk_factors = []
    risk_score = 0
    
    # 변동성 리스크
    if trend_analysis.volatility > 50:
        risk_factors.append("높은 수익 변동성으로 인한 예측 불확실성")
        risk_score += 30
    elif trend_analysis.volatility > 30:
        risk_factors.append("중간 수준의 수익 변동성")
        risk_score += 15
    
    # 트렌드 리스크
    if trend_analysis.trend_direction == "decreasing" and trend_analysis.trend_strength > 60:
        risk_factors.append("강한 하락 트렌드로 인한 수익 감소 위험")
        risk_score += 40
    elif trend_analysis.trend_direction == "decreasing":
        risk_factors.append("수익 하락 추세 지속 가능성")
        risk_score += 20
    
    # 신뢰구간 리스크
    avg_confidence_range = sum(p.confidence_upper - p.confidence_lower for p in predictions) / len(predictions)
    avg_prediction = sum(p.predicted_profit for p in predictions) / len(predictions)
    
    if avg_prediction != 0:
        relative_uncertainty = abs(avg_confidence_range / avg_prediction) * 100
        if relative_uncertainty > 50:
            risk_factors.append("예측 신뢰구간이 넓어 불확실성 높음")
            risk_score += 25
        elif relative_uncertainty > 30:
            risk_factors.append("중간 수준의 예측 불확실성")
            risk_score += 10
    
    # 계절성 리스크
    if trend_analysis.seasonality_detected:
        risk_factors.append("계절성 패턴으로 인한 주기적 변동 위험")
        risk_score += 10
    
    # 데이터 부족 리스크
    # 이 정보는 상위에서 전달되어야 하지만, 여기서는 예측 개수로 추정
    if len(predictions) > 6:  # 6개월 이상 예측 시
        risk_factors.append("장기 예측으로 인한 정확도 저하 위험")
        risk_score += 15
    
    # 전체 리스크 등급 결정
    if risk_score >= 60:
        overall_risk = "high"
    elif risk_score >= 30:
        overall_risk = "medium"
    else:
        overall_risk = "low"
    
    return {
        "overall_risk": overall_risk,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "confidence_level": max(40, 100 - risk_score),  # 리스크 점수에 반비례
        "recommendation": get_risk_recommendation(overall_risk)
    }

def get_risk_recommendation(risk_level: str) -> str:
    """리스크 수준별 권장사항"""
    
    recommendations = {
        "low": "예측 신뢰도가 높습니다. 계획된 전략을 실행하세요.",
        "medium": "적당한 리스크가 있습니다. 대안 시나리오를 준비하고 모니터링을 강화하세요.",
        "high": "높은 불확실성이 있습니다. 보수적 접근과 리스크 관리가 필요합니다."
    }
    
    return recommendations.get(risk_level, "리스크 평가가 필요합니다.")

def generate_strategic_recommendations(trend_analysis, predictions, current_summary) -> List[str]:
    """전략적 권장사항 생성"""
    
    recommendations = []
    
    # 트렌드 기반 권장사항
    if trend_analysis.trend_direction == "increasing":
        if trend_analysis.growth_rate > 20:
            recommendations.append("💡 강력한 성장세입니다. 마케팅 투자를 확대하고 시장 점유율을 높이세요.")
            recommendations.append("💡 성장 모멘텀을 활용해 신제품이나 서비스 출시를 고려하세요.")
        else:
            recommendations.append("💡 안정적인 성장입니다. 지속 가능한 성장 전략을 수립하세요.")
    elif trend_analysis.trend_direction == "decreasing":
        recommendations.append("💡 수익 개선을 위한 비용 최적화와 효율성 향상이 필요합니다.")
        recommendations.append("💡 새로운 수익원 발굴이나 사업 모델 혁신을 검토하세요.")
    else:
        recommendations.append("💡 안정적인 상황입니다. 새로운 성장 기회를 탐색하세요.")
    
    # 변동성 기반 권장사항  
    if trend_analysis.volatility > 40:
        recommendations.append("💡 수익 안정성 확보를 위한 다각화 전략을 수립하세요.")
        recommendations.append("💡 위험 관리 시스템을 강화하고 비상 계획을 준비하세요.")
    
    # 예측 기반 권장사항
    if predictions:
        future_avg = sum(p.predicted_profit for p in predictions) / len(predictions)
        current_avg = current_summary['avg_monthly_profit']
        
        if future_avg > current_avg * 1.2:
            recommendations.append("💡 수익 증가가 예상됩니다. 성장 투자를 늘리고 인력을 확충하세요.")
        elif future_avg < current_avg * 0.8:
            recommendations.append("💡 수익 감소가 우려됩니다. 비용 구조를 점검하고 효율성을 개선하세요.")
    
    # 계절성 기반 권장사항
    if trend_analysis.seasonality_detected:
        recommendations.append("💡 계절성 패턴을 활용한 마케팅 타이밍과 재고 관리를 최적화하세요.")
    
    # 기본 권장사항이 없으면 일반적인 조언 추가
    if not recommendations:
        recommendations.append("💡 정기적인 성과 모니터링과 데이터 기반 의사결정을 강화하세요.")
    
    return recommendations

def generate_expense_insights(category_analysis, monthly_patterns, daily_patterns):
    """지출 패턴 인사이트 생성"""
    insights = []
    
    if category_analysis:
        # 승인률이 낮은 카테고리
        low_approval = [cat for cat, analysis in category_analysis.items() if analysis['approval_rate'] < 70]
        if low_approval:
            insights.append(f"🚨 승인률이 낮은 지출 분야: {', '.join(low_approval)}")
        
        # 가장 많이 사용하는 카테고리
        highest_spending = max(category_analysis.items(), key=lambda x: x[1]['approved_amount'])
        insights.append(f"💰 주요 지출 분야: {highest_spending[0]} (총 {highest_spending[1]['approved_amount']:,.0f}원)")
    
    if daily_patterns:
        # 요일별 지출 패턴
        max_day = max(daily_patterns.items(), key=lambda x: x[1]['total_amount'])
        min_day = min(daily_patterns.items(), key=lambda x: x[1]['total_amount'])
        insights.append(f"📊 지출이 가장 많은 요일: {max_day[0]} ({max_day[1]['total_amount']:,.0f}원)")
        insights.append(f"📊 지출이 가장 적은 요일: {min_day[0]} ({min_day[1]['total_amount']:,.0f}원)")
    
    if len(monthly_patterns) >= 3:
        # 최근 3개월 트렌드
        recent_months = sorted(monthly_patterns.keys())[-3:]
        recent_expenses = [monthly_patterns[month]['approved'] for month in recent_months]
        
        if recent_expenses[-1] > recent_expenses[0] * 1.2:
            insights.append("📈 최근 지출이 증가 추세입니다. 예산 관리에 주의하세요")
        elif recent_expenses[-1] < recent_expenses[0] * 0.8:
            insights.append("📉 최근 지출이 감소 추세입니다. 비용 절감이 잘 되고 있습니다")
        else:
            insights.append("📊 지출이 안정적인 수준을 유지하고 있습니다")
    
    return insights