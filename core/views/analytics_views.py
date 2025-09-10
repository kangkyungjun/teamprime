"""
분석 및 리포팅 뷰 라우터
- 비즈니스 성과 대시보드
- 업무 효율성 분석
- 지출 패턴 분석  
- 수익 예측 및 트렌드
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)
analytics_views_router = APIRouter()

@analytics_views_router.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """종합 분석 대시보드 - 새로운 손익 관리 페이지로 리다이렉트"""
    # 인증 확인 후 새로운 페이지로 리다이렉트
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 새로운 손익 관리 페이지로 리다이렉트
    return RedirectResponse(url="/profit-loss")

@analytics_views_router.get("/analytics-legacy", response_class=HTMLResponse)
async def analytics_dashboard_legacy(request: Request):
    """기존 종합 분석 대시보드 (백업용)"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_role = current_user.get('role', 'user')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>비즈니스 분석 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
                padding: 20px 0;
            }}
            
            .main-container {{
                max-width: 1600px;
                margin: 0 auto;
                padding: 0 20px;
            }}
            
            .header-section {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .analytics-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin-bottom: 30px;
            }}
            
            .analytics-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .analytics-tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }}
            
            .analytics-tab {{
                padding: 12px 24px;
                background: rgba(255, 255, 255, 0.9);
                border: none;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 600;
            }}
            
            .analytics-tab.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .chart-container {{
                position: relative;
                height: 400px;
                margin-bottom: 20px;
            }}
            
            .stats-row {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
            }}
            
            .stat-value {{
                font-size: 28px;
                font-weight: 700;
                color: #667eea;
                margin-bottom: 5px;
            }}
            
            .stat-label {{
                font-size: 14px;
                color: #6c757d;
            }}
            
            .insight-box {{
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }}
            
            .trend-indicator {{
                display: inline-flex;
                align-items: center;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            
            .trend-up {{
                background: #d4edda;
                color: #155724;
            }}
            
            .trend-down {{
                background: #f8d7da;
                color: #721c24;
            }}
            
            .trend-stable {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .loading {{
                text-align: center;
                padding: 50px;
                color: #6c757d;
            }}
            
            .loading-spinner {{
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .period-selector {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }}
            
            .period-btn {{
                padding: 6px 12px;
                border: 1px solid #dee2e6;
                background: white;
                border-radius: 20px;
                cursor: pointer;
                font-size: 12px;
                transition: all 0.3s ease;
            }}
            
            .period-btn.active {{
                background: #667eea;
                color: white;
                border-color: #667eea;
            }}
            
            @media (max-width: 768px) {{
                .analytics-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header-section {{
                    padding: 20px;
                }}
                
                .analytics-card {{
                    padding: 20px;
                }}
                
                .chart-container {{
                    height: 300px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <!-- Header Section -->
            <div class="header-section">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h1 class="mb-2"><i class="fas fa-chart-line me-3"></i>비즈니스 분석</h1>
                        <p class="text-muted mb-0">{username}님의 종합 성과 분석 대시보드</p>
                    </div>
                    <div class="d-flex gap-3">
                        <button class="btn btn-outline-primary" onclick="exportReport()">
                            <i class="fas fa-download me-2"></i>리포트 다운로드
                        </button>
                        <a href="/main-dashboard" class="btn btn-outline-secondary">
                            <i class="fas fa-home me-2"></i>대시보드
                        </a>
                    </div>
                </div>
            </div>
            
            <!-- Analytics Tabs -->
            <div class="analytics-tabs">
                <button class="analytics-tab active" data-tab="performance" onclick="switchTab('performance')">
                    📊 비즈니스 성과
                </button>
                <button class="analytics-tab" data-tab="efficiency" onclick="switchTab('efficiency')">
                    ⚡ 업무 효율성
                </button>
                <button class="analytics-tab" data-tab="expenses" onclick="switchTab('expenses')">
                    💳 지출 패턴
                </button>
                <button class="analytics-tab" data-tab="predictions" onclick="switchTab('predictions')">
                    🔮 예측 분석
                </button>
            </div>
            
            <!-- Performance Analysis Tab -->
            <div id="performance-tab" class="tab-content">
                <div class="analytics-grid">
                    <!-- Revenue & Profit Chart -->
                    <div class="analytics-card">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4>수익 & 이익 추이</h4>
                            <div class="period-selector">
                                <button class="period-btn active" data-period="3months" onclick="changePeriod('performance', '3months')">3개월</button>
                                <button class="period-btn" data-period="6months" onclick="changePeriod('performance', '6months')">6개월</button>
                                <button class="period-btn" data-period="12months" onclick="changePeriod('performance', '12months')">12개월</button>
                            </div>
                        </div>
                        <div class="chart-container">
                            <canvas id="revenueChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Performance Stats -->
                    <div class="analytics-card">
                        <h4 class="mb-3">성과 지표</h4>
                        <div class="stats-row">
                            <div class="stat-card">
                                <div class="stat-value" id="currentProfit">로딩중...</div>
                                <div class="stat-label">이번달 순이익</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="profitGrowth">로딩중...</div>
                                <div class="stat-label">전월 대비 성장률</div>
                            </div>
                        </div>
                        <div class="stats-row">
                            <div class="stat-card">
                                <div class="stat-value" id="avgRevenue">로딩중...</div>
                                <div class="stat-label">월평균 매출</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="avgProductivity">로딩중...</div>
                                <div class="stat-label">평균 생산성</div>
                            </div>
                        </div>
                        <div id="performanceInsights"></div>
                    </div>
                </div>
                
                <!-- Category Analysis -->
                <div class="analytics-card">
                    <h4 class="mb-3">카테고리별 성과</h4>
                    <div class="chart-container" style="height: 300px;">
                        <canvas id="categoryChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Efficiency Analysis Tab -->
            <div id="efficiency-tab" class="tab-content" style="display: none;">
                <div class="analytics-grid">
                    <!-- Task Efficiency Chart -->
                    <div class="analytics-card">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4>업무 효율성 분석</h4>
                            <div class="period-selector">
                                <button class="period-btn active" data-period="7days" onclick="changePeriod('efficiency', '7days')">7일</button>
                                <button class="period-btn" data-period="30days" onclick="changePeriod('efficiency', '30days')">30일</button>
                                <button class="period-btn" data-period="90days" onclick="changePeriod('efficiency', '90days')">90일</button>
                            </div>
                        </div>
                        <div class="chart-container">
                            <canvas id="efficiencyChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Efficiency Stats -->
                    <div class="analytics-card">
                        <h4 class="mb-3">효율성 지표</h4>
                        <div class="stats-row">
                            <div class="stat-card">
                                <div class="stat-value" id="completionRate">로딩중...</div>
                                <div class="stat-label">업무 완료율</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="delayRate">로딩중...</div>
                                <div class="stat-label">지연률</div>
                            </div>
                        </div>
                        <div class="stats-row">
                            <div class="stat-card">
                                <div class="stat-value" id="avgCompletionTime">로딩중...</div>
                                <div class="stat-label">평균 완료시간</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="productivityScore">로딩중...</div>
                                <div class="stat-label">생산성 점수</div>
                            </div>
                        </div>
                        <div id="efficiencyInsights"></div>
                    </div>
                </div>
                
                <!-- User Performance -->
                <div class="analytics-card">
                    <h4 class="mb-3">팀원별 성과</h4>
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>이름</th>
                                    <th>역할</th>
                                    <th>완료 업무</th>
                                    <th>완료율</th>
                                    <th>효율성 점수</th>
                                    <th>평균 완료시간</th>
                                </tr>
                            </thead>
                            <tbody id="userPerformanceTable">
                                <tr>
                                    <td colspan="6" class="text-center">로딩중...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Expense Pattern Tab -->
            <div id="expenses-tab" class="tab-content" style="display: none;">
                <div class="analytics-grid">
                    <!-- Expense Trends -->
                    <div class="analytics-card">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h4>지출 트렌드</h4>
                            <div class="period-selector">
                                <button class="period-btn active" data-period="3months" onclick="changePeriod('expenses', '3months')">3개월</button>
                                <button class="period-btn" data-period="6months" onclick="changePeriod('expenses', '6months')">6개월</button>
                                <button class="period-btn" data-period="12months" onclick="changePeriod('expenses', '12months')">12개월</button>
                            </div>
                        </div>
                        <div class="chart-container">
                            <canvas id="expenseChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Budget Recommendations -->
                    <div class="analytics-card">
                        <h4 class="mb-3">예산 추천</h4>
                        <div id="budgetRecommendations">
                            <div class="loading">
                                <div class="loading-spinner"></div>
                                예산 분석 중...
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Daily/Weekly Patterns -->
                <div class="analytics-card">
                    <h4 class="mb-3">요일별 지출 패턴</h4>
                    <div class="chart-container" style="height: 300px;">
                        <canvas id="dailyPatternChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Predictions Tab -->
            <div id="predictions-tab" class="tab-content" style="display: none;">
                <div class="analytics-card">
                    <h4 class="mb-3">수익 예측 모델</h4>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        AI 기반 수익 예측 기능은 개발 중입니다. 충분한 데이터가 쌓이면 더 정확한 예측을 제공할 예정입니다.
                    </div>
                    <div class="chart-container">
                        <canvas id="predictionChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentTab = 'performance';
            let charts = {{}};
            
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                loadAnalyticsData();
            }});
            
            // 탭 전환
            function switchTab(tabName) {{
                // 모든 탭 컨텐츠 숨기기
                document.querySelectorAll('.tab-content').forEach(tab => {{
                    tab.style.display = 'none';
                }});
                
                // 모든 탭 버튼 비활성화
                document.querySelectorAll('.analytics-tab').forEach(tab => {{
                    tab.classList.remove('active');
                }});
                
                // 선택된 탭 활성화
                document.getElementById(tabName + '-tab').style.display = 'block';
                document.querySelector(`[data-tab="${{tabName}}"]`).classList.add('active');
                
                currentTab = tabName;
                loadTabData(tabName);
            }}
            
            // 기간 변경
            function changePeriod(tab, period) {{
                // 해당 탭의 기간 버튼 업데이트
                const tabElement = document.getElementById(tab + '-tab');
                tabElement.querySelectorAll('.period-btn').forEach(btn => {{
                    btn.classList.remove('active');
                }});
                tabElement.querySelector(`[data-period="${{period}}"]`).classList.add('active');
                
                // 데이터 다시 로드
                loadTabData(tab, period);
            }}
            
            // 분석 데이터 로드
            async function loadAnalyticsData() {{
                loadTabData('performance');
            }}
            
            // 탭별 데이터 로드
            async function loadTabData(tabName, period = null) {{
                try {{
                    switch(tabName) {{
                        case 'performance':
                            await loadPerformanceData(period || '6months');
                            break;
                        case 'efficiency':
                            await loadEfficiencyData(period || '30days');
                            break;
                        case 'expenses':
                            await loadExpenseData(period || '6months');
                            break;
                        case 'predictions':
                            await loadPredictionData();
                            break;
                    }}
                }} catch (error) {{
                    console.error(`${{tabName}} 데이터 로드 오류:`, error);
                }}
            }}
            
            // 비즈니스 성과 데이터 로드
            async function loadPerformanceData(period) {{
                try {{
                    const response = await fetch(`/api/analytics/business-performance?period=${{period}}`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 통계 업데이트
                        document.getElementById('currentProfit').textContent = 
                            data.summary.current_month_profit.toLocaleString() + '원';
                        
                        const growthRate = data.summary.profit_growth_rate;
                        const growthElement = document.getElementById('profitGrowth');
                        growthElement.textContent = growthRate + '%';
                        growthElement.className = `stat-value ${{growthRate >= 0 ? 'text-success' : 'text-danger'}}`;
                        
                        document.getElementById('avgRevenue').textContent = 
                            Math.round(data.summary.avg_monthly_revenue).toLocaleString() + '원';
                        document.getElementById('avgProductivity').textContent = 
                            data.summary.avg_productivity.toFixed(1) + '%';
                        
                        // 차트 렌더링
                        renderRevenueChart(data.trends.revenue_profit);
                        renderCategoryChart(data.top_income_categories, data.top_expense_categories);
                        
                        // 인사이트 표시
                        displayInsights('performanceInsights', generatePerformanceInsights(data));
                    }}
                }} catch (error) {{
                    console.error('성과 데이터 로드 실패:', error);
                }}
            }}
            
            // 업무 효율성 데이터 로드
            async function loadEfficiencyData(period) {{
                try {{
                    const response = await fetch(`/api/analytics/task-efficiency?period=${{period}}`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 통계 업데이트
                        document.getElementById('completionRate').textContent = data.overall_stats.completion_rate + '%';
                        document.getElementById('delayRate').textContent = data.overall_stats.delay_rate + '%';
                        document.getElementById('avgCompletionTime').textContent = data.overall_stats.avg_completion_time + '일';
                        document.getElementById('productivityScore').textContent = data.overall_stats.productivity_score + '점';
                        
                        // 효율성 차트 렌더링
                        renderEfficiencyChart(data.category_efficiency);
                        
                        // 사용자 성과 테이블
                        renderUserPerformanceTable(data.user_efficiency);
                        
                        // 인사이트 표시
                        displayInsights('efficiencyInsights', data.insights);
                    }}
                }} catch (error) {{
                    console.error('효율성 데이터 로드 실패:', error);
                }}
            }}
            
            // 지출 패턴 데이터 로드
            async function loadExpenseData(period) {{
                try {{
                    const response = await fetch(`/api/analytics/expense-patterns?period=${{period}}`);
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 지출 트렌드 차트
                        renderExpenseChart(data.expense_trends);
                        
                        // 예산 추천
                        renderBudgetRecommendations(data.budget_recommendations);
                        
                        // 요일별 패턴
                        renderDailyPatternChart(data.daily_patterns);
                        
                        // 인사이트 표시
                        displayInsights('expenseInsights', data.insights);
                    }}
                }} catch (error) {{
                    console.error('지출 데이터 로드 실패:', error);
                }}
            }}
            
            // 예측 데이터 로드 (향후 구현)
            async function loadPredictionData() {{
                // 임시 플레이스홀더
                console.log('예측 분석 기능은 개발 중입니다.');
            }}
            
            // 수익 차트 렌더링
            function renderRevenueChart(trendData) {{
                const ctx = document.getElementById('revenueChart').getContext('2d');
                
                if (charts.revenue) {{
                    charts.revenue.destroy();
                }}
                
                const months = trendData.map(item => item.month).reverse();
                const revenues = trendData.map(item => item.revenue).reverse();
                const expenses = trendData.map(item => item.expense).reverse();
                const profits = trendData.map(item => item.profit).reverse();
                
                charts.revenue = new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: months,
                        datasets: [
                            {{
                                label: '수익',
                                data: revenues,
                                borderColor: '#4caf50',
                                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                                tension: 0.4
                            }},
                            {{
                                label: '지출',
                                data: expenses,
                                borderColor: '#f44336',
                                backgroundColor: 'rgba(244, 67, 54, 0.1)',
                                tension: 0.4
                            }},
                            {{
                                label: '순이익',
                                data: profits,
                                borderColor: '#2196f3',
                                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                                tension: 0.4
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'top',
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: function(value) {{
                                        return value.toLocaleString() + '원';
                                    }}
                                }}
                            }}
                        }},
                        interaction: {{
                            intersect: false,
                            mode: 'index'
                        }}
                    }}
                }});
            }}
            
            // 카테고리 차트 렌더링
            function renderCategoryChart(incomeCategories, expenseCategories) {{
                const ctx = document.getElementById('categoryChart').getContext('2d');
                
                if (charts.category) {{
                    charts.category.destroy();
                }}
                
                const labels = incomeCategories.map(item => item.category);
                const data = incomeCategories.map(item => item.count);
                
                charts.category = new Chart(ctx, {{
                    type: 'doughnut',
                    data: {{
                        labels: labels,
                        datasets: [{{
                            data: data,
                            backgroundColor: [
                                '#FF6384',
                                '#36A2EB', 
                                '#FFCE56',
                                '#4BC0C0',
                                '#9966FF',
                                '#FF9F40'
                            ]
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom'
                            }}
                        }}
                    }}
                }});
            }}
            
            // 효율성 차트 렌더링
            function renderEfficiencyChart(categoryEfficiency) {{
                const ctx = document.getElementById('efficiencyChart').getContext('2d');
                
                if (charts.efficiency) {{
                    charts.efficiency.destroy();
                }}
                
                const categories = Object.keys(categoryEfficiency);
                const efficiencyScores = categories.map(cat => categoryEfficiency[cat].efficiency_score);
                const completionRates = categories.map(cat => categoryEfficiency[cat].completion_rate);
                
                charts.efficiency = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: categories,
                        datasets: [
                            {{
                                label: '효율성 점수',
                                data: efficiencyScores,
                                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                                borderColor: 'rgba(102, 126, 234, 1)',
                                borderWidth: 1
                            }},
                            {{
                                label: '완료율',
                                data: completionRates,
                                backgroundColor: 'rgba(76, 175, 80, 0.8)',
                                borderColor: 'rgba(76, 175, 80, 1)',
                                borderWidth: 1
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100
                            }}
                        }}
                    }}
                }});
            }}
            
            // 지출 차트 렌더링
            function renderExpenseChart(expenseTrends) {{
                const ctx = document.getElementById('expenseChart').getContext('2d');
                
                if (charts.expense) {{
                    charts.expense.destroy();
                }}
                
                const months = expenseTrends.map(item => item.month);
                const amounts = expenseTrends.map(item => item.total_expense);
                
                charts.expense = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: months,
                        datasets: [{{
                            label: '월별 지출',
                            data: amounts,
                            backgroundColor: 'rgba(244, 67, 54, 0.8)',
                            borderColor: 'rgba(244, 67, 54, 1)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    callback: function(value) {{
                                        return value.toLocaleString() + '원';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            }}
            
            // 요일별 패턴 차트 렌더링
            function renderDailyPatternChart(dailyPatterns) {{
                const ctx = document.getElementById('dailyPatternChart').getContext('2d');
                
                if (charts.daily) {{
                    charts.daily.destroy();
                }}
                
                const days = Object.keys(dailyPatterns);
                const amounts = days.map(day => dailyPatterns[day].total_amount);
                
                charts.daily = new Chart(ctx, {{
                    type: 'radar',
                    data: {{
                        labels: days,
                        datasets: [{{
                            label: '일별 지출',
                            data: amounts,
                            backgroundColor: 'rgba(102, 126, 234, 0.2)',
                            borderColor: 'rgba(102, 126, 234, 1)',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            r: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }});
            }}
            
            // 사용자 성과 테이블 렌더링
            function renderUserPerformanceTable(userEfficiency) {{
                const tbody = document.getElementById('userPerformanceTable');
                
                if (userEfficiency.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">데이터가 없습니다</td></tr>';
                    return;
                }}
                
                tbody.innerHTML = userEfficiency.map(user => `
                    <tr>
                        <td>${{user.username}}</td>
                        <td><span class="badge bg-secondary">${{user.role}}</span></td>
                        <td>${{user.completed_tasks}}</td>
                        <td>
                            <span class="badge bg-${{user.completion_rate >= 80 ? 'success' : (user.completion_rate >= 60 ? 'warning' : 'danger')}}">
                                ${{user.completion_rate}}%
                            </span>
                        </td>
                        <td>${{user.efficiency_score}}점</td>
                        <td>${{user.avg_completion_days}}일</td>
                    </tr>
                `).join('');
            }}
            
            // 예산 추천 렌더링
            function renderBudgetRecommendations(budgetData) {{
                const container = document.getElementById('budgetRecommendations');
                
                if (Object.keys(budgetData).length === 0) {{
                    container.innerHTML = '<p class="text-muted">예산 데이터가 부족합니다.</p>';
                    return;
                }}
                
                container.innerHTML = Object.entries(budgetData).map(([category, budget]) => `
                    <div class="mb-3 p-3 border rounded">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-1">${{category}}</h6>
                            <span class="badge bg-${{budget.confidence === 'high' ? 'success' : 'warning'}}">
                                ${{budget.confidence}}
                            </span>
                        </div>
                        <div class="small text-muted mb-2">
                            현재 월평균: ${{budget.current_monthly_avg.toLocaleString()}}원
                        </div>
                        <div class="fw-bold text-primary">
                            권장 예산: ${{budget.recommended_budget.toLocaleString()}}원
                        </div>
                    </div>
                `).join('');
            }}
            
            // 인사이트 표시
            function displayInsights(containerId, insights) {{
                const container = document.getElementById(containerId);
                if (insights && insights.length > 0) {{
                    container.innerHTML = insights.map(insight => `
                        <div class="insight-box">
                            <small>${{insight}}</small>
                        </div>
                    `).join('');
                }} else {{
                    container.innerHTML = '';
                }}
            }}
            
            // 성과 인사이트 생성
            function generatePerformanceInsights(data) {{
                const insights = [];
                
                if (data.summary.profit_growth_rate > 10) {{
                    insights.push('🚀 수익이 크게 증가하고 있습니다! 현재 전략을 유지하세요.');
                }} else if (data.summary.profit_growth_rate < -10) {{
                    insights.push('📉 수익 감소가 우려됩니다. 원인 분석이 필요합니다.');
                }}
                
                if (data.summary.avg_productivity > 80) {{
                    insights.push('✅ 팀 생산성이 우수한 수준입니다.');
                }} else if (data.summary.avg_productivity < 60) {{
                    insights.push('⚠️ 팀 생산성 향상이 필요합니다.');
                }}
                
                return insights;
            }}
            
            // 리포트 다운로드
            function exportReport() {{
                alert('리포트 다운로드 기능은 개발 중입니다.');
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)