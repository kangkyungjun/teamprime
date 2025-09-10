"""
리포트 관리 뷰
- 리포트 생성 및 다운로드 인터페이스
- 자동 리포트 설정
- 리포트 히스토리 관리
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from core.auth import get_current_user
from typing import Dict

reports_views_router = APIRouter()

@reports_views_router.get("/reports", response_class=HTMLResponse)
async def reports_dashboard(request: Request, user: Dict = Depends(get_current_user)):
    """리포트 관리 대시보드"""
    
    # 권한 체크
    if user.get("role") not in ["Owner", "Prime", "VIP", "Standard"]:
        raise HTTPException(status_code=403, detail="리포트 접근 권한이 없습니다")
    
    user_role = user.get("role", "")
    user_email = user.get("email", "")
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>리포트 관리 - 업무 관리 시스템</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --light-bg: #ecf0f1;
        }}
        
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        .main-container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            margin: 2rem auto;
            padding: 2rem;
            max-width: 1400px;
        }}
        
        .header-section {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header-section::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: float 6s ease-in-out infinite;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-20px) rotate(180deg); }}
        }}
        
        .report-card {{
            background: white;
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            border: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }}
        
        .report-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        }}
        
        .report-type-icon {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: white;
            margin-bottom: 1rem;
        }}
        
        .business-icon {{ background: linear-gradient(135deg, #27ae60, #2ecc71); }}
        .task-icon {{ background: linear-gradient(135deg, #3498db, #5dade2); }}
        .comprehensive-icon {{ background: linear-gradient(135deg, #8e44ad, #a569bd); }}
        .financial-icon {{ background: linear-gradient(135deg, #f39c12, #f4d03f); }}
        
        .download-btn {{
            margin: 0.25rem;
            border-radius: 25px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            border: none;
            position: relative;
            overflow: hidden;
        }}
        
        .download-btn::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transition: all 0.6s;
            transform: translate(-50%, -50%);
        }}
        
        .download-btn:hover::before {{
            width: 200px;
            height: 200px;
        }}
        
        .btn-excel {{
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white;
        }}
        
        .btn-pdf {{
            background: linear-gradient(135deg, #e74c3c, #ec7063);
            color: white;
        }}
        
        .btn-preview {{
            background: linear-gradient(135deg, #3498db, #5dade2);
            color: white;
        }}
        
        .settings-card {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-radius: 15px;
            padding: 2rem;
            margin-top: 2rem;
        }}
        
        .role-badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }}
        
        .role-owner {{ background: linear-gradient(135deg, #f39c12, #f4d03f); color: #2c3e50; }}
        .role-prime {{ background: linear-gradient(135deg, #8e44ad, #a569bd); color: white; }}
        .role-vip {{ background: linear-gradient(135deg, #e74c3c, #ec7063); color: white; }}
        .role-standard {{ background: linear-gradient(135deg, #95a5a6, #bdc3c7); color: white; }}
        
        .period-selector {{
            background: white;
            border-radius: 25px;
            padding: 0.25rem;
            margin-bottom: 1rem;
        }}
        
        .period-btn {{
            border: none;
            background: transparent;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            margin: 0.1rem;
            transition: all 0.3s ease;
        }}
        
        .period-btn.active {{
            background: var(--secondary-color);
            color: white;
        }}
        
        .loading-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 9999;
            justify-content: center;
            align-items: center;
        }}
        
        .loading-content {{
            background: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }}
        
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid var(--secondary-color);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .auto-report-section {{
            background: linear-gradient(135deg, #2c3e50, #3498db);
            color: white;
            border-radius: 15px;
            padding: 2rem;
            margin-top: 2rem;
        }}
        
        .feature-disabled {{
            opacity: 0.5;
            pointer-events: none;
        }}
        
        .tooltip-icon {{
            cursor: help;
            margin-left: 0.5rem;
            color: #6c757d;
        }}
        
        .navbar-brand {{
            color: white !important;
            text-decoration: none;
            font-weight: bold;
        }}
        
        .navbar-nav .nav-link {{
            color: rgba(255, 255, 255, 0.8) !important;
            margin: 0 0.5rem;
            transition: color 0.3s ease;
        }}
        
        .navbar-nav .nav-link:hover {{
            color: white !important;
        }}
        
        .btn-logout {{
            background: linear-gradient(135deg, #e74c3c, #ec7063);
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1rem;
            color: white;
        }}
    </style>
</head>
<body>
    <!-- 네비게이션 -->
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: rgba(44, 62, 80, 0.9);">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-chart-bar me-2"></i>업무 관리 시스템
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">
                    <i class="fas fa-tachometer-alt me-1"></i>대시보드
                </a>
                <a class="nav-link" href="/tasks">
                    <i class="fas fa-tasks me-1"></i>업무 관리
                </a>
                <a class="nav-link" href="/analytics">
                    <i class="fas fa-chart-line me-1"></i>분석
                </a>
                <a class="nav-link active" href="/reports">
                    <i class="fas fa-file-alt me-1"></i>리포트
                </a>
                <button class="btn btn-logout btn-sm ms-2" onclick="logout()">
                    <i class="fas fa-sign-out-alt me-1"></i>로그아웃
                </button>
            </div>
        </div>
    </nav>

    <div class="main-container">
        <!-- 헤더 섹션 -->
        <div class="header-section">
            <h1><i class="fas fa-file-chart me-3"></i>리포트 관리</h1>
            <p class="mb-0">비즈니스 인사이트를 위한 종합 리포트 시스템</p>
            <div class="role-badge role-{user_role.lower()}" style="position: absolute; top: 1rem; right: 1rem;">
                <i class="fas fa-crown me-1"></i>{user_role}
            </div>
        </div>

        <!-- 기간 선택기 -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="report-card">
                    <h5><i class="fas fa-calendar-alt me-2"></i>분석 기간 선택</h5>
                    <div class="period-selector">
                        <button class="period-btn active" onclick="selectPeriod('3months', this)">3개월</button>
                        <button class="period-btn" onclick="selectPeriod('6months', this)">6개월</button>
                        <button class="period-btn" onclick="selectPeriod('12months', this)">12개월</button>
                        {"<button class='period-btn' onclick='selectPeriod(\"2years\", this)'>2년</button>" if user_role in ["Owner", "Prime"] else ""}
                    </div>
                    <small class="text-muted">선택된 기간: <span id="selected-period">최근 3개월</span></small>
                </div>
            </div>
        </div>

        <!-- 리포트 카드들 -->
        <div class="row">
            <!-- 비즈니스 성과 리포트 -->
            <div class="col-lg-6 col-md-12">
                <div class="report-card">
                    <div class="d-flex align-items-start">
                        <div class="report-type-icon business-icon">
                            <i class="fas fa-chart-line"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h5>비즈니스 성과 리포트</h5>
                            <p class="text-muted mb-3">수익, 지출, 순이익 등 핵심 비즈니스 지표 분석</p>
                            <div class="d-flex flex-wrap">
                                <button class="btn btn-excel download-btn" onclick="downloadReport('business', 'excel')">
                                    <i class="fas fa-file-excel me-1"></i>Excel 다운로드
                                </button>
                                <button class="btn btn-pdf download-btn" onclick="downloadReport('business', 'pdf')">
                                    <i class="fas fa-file-pdf me-1"></i>PDF 다운로드
                                </button>
                                <button class="btn btn-preview download-btn" onclick="previewReport('business')">
                                    <i class="fas fa-eye me-1"></i>미리보기
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 업무 효율성 리포트 -->
            <div class="col-lg-6 col-md-12">
                <div class="report-card">
                    <div class="d-flex align-items-start">
                        <div class="report-type-icon task-icon">
                            <i class="fas fa-tasks"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h5>업무 효율성 리포트</h5>
                            <p class="text-muted mb-3">업무 완료율, 생산성 지표, 팀 퍼포먼스 분석</p>
                            <div class="d-flex flex-wrap">
                                <button class="btn btn-excel download-btn" onclick="downloadReport('task_efficiency', 'excel')">
                                    <i class="fas fa-file-excel me-1"></i>Excel 다운로드
                                </button>
                                <button class="btn btn-pdf download-btn" onclick="downloadReport('task_efficiency', 'pdf')">
                                    <i class="fas fa-file-pdf me-1"></i>PDF 다운로드
                                </button>
                                <button class="btn btn-preview download-btn" onclick="previewReport('task_efficiency')">
                                    <i class="fas fa-eye me-1"></i>미리보기
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 종합 분석 리포트 (Owner/Prime 전용) -->
            {"" if user_role not in ["Owner", "Prime"] else f"""
            <div class="col-lg-6 col-md-12">
                <div class="report-card">
                    <div class="d-flex align-items-start">
                        <div class="report-type-icon comprehensive-icon">
                            <i class="fas fa-chart-pie"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h5>종합 분석 리포트 <i class="fas fa-crown text-warning ms-1"></i></h5>
                            <p class="text-muted mb-3">모든 지표를 통합한 고급 분석 및 예측 리포트</p>
                            <div class="d-flex flex-wrap">
                                <button class="btn btn-excel download-btn" onclick="downloadReport('comprehensive', 'excel')">
                                    <i class="fas fa-file-excel me-1"></i>Excel 다운로드
                                </button>
                                <button class="btn btn-pdf download-btn" onclick="downloadReport('comprehensive', 'pdf')">
                                    <i class="fas fa-file-pdf me-1"></i>PDF 다운로드
                                </button>
                                <button class="btn btn-preview download-btn" onclick="previewReport('comprehensive')">
                                    <i class="fas fa-eye me-1"></i>미리보기
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """}

            <!-- 재무 분석 리포트 (Owner/Prime 전용) -->
            {"" if user_role not in ["Owner", "Prime"] else f"""
            <div class="col-lg-6 col-md-12">
                <div class="report-card">
                    <div class="d-flex align-items-start">
                        <div class="report-type-icon financial-icon">
                            <i class="fas fa-dollar-sign"></i>
                        </div>
                        <div class="flex-grow-1 ms-3">
                            <h5>재무 예측 리포트 <i class="fas fa-crown text-warning ms-1"></i></h5>
                            <p class="text-muted mb-3">AI 기반 수익 예측 및 트렌드 분석</p>
                            <div class="d-flex flex-wrap">
                                <button class="btn btn-excel download-btn" onclick="downloadReport('financial', 'excel')">
                                    <i class="fas fa-file-excel me-1"></i>Excel 다운로드
                                </button>
                                <button class="btn btn-pdf download-btn" onclick="downloadReport('financial', 'pdf')">
                                    <i class="fas fa-file-pdf me-1"></i>PDF 다운로드
                                </button>
                                <button class="btn btn-preview download-btn" onclick="previewReport('financial')">
                                    <i class="fas fa-eye me-1"></i>미리보기
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """}
        </div>

        <!-- 자동 리포트 설정 (Owner 전용) -->
        {"" if user_role != "Owner" else f"""
        <div class="auto-report-section">
            <h4><i class="fas fa-robot me-2"></i>자동 리포트 생성 설정</h4>
            <p class="mb-4">정기적인 리포트 자동 생성 및 이메일 발송을 설정할 수 있습니다.</p>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">리포트 유형</label>
                        <select class="form-select" id="auto-report-type">
                            <option value="business">비즈니스 성과</option>
                            <option value="comprehensive">종합 분석</option>
                            <option value="task_efficiency">업무 효율성</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">생성 주기</label>
                        <select class="form-select" id="auto-frequency">
                            <option value="weekly">매주</option>
                            <option value="monthly">매월</option>
                            <option value="quarterly">분기별</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">파일 형식</label>
                        <select class="form-select" id="auto-format">
                            <option value="pdf">PDF</option>
                            <option value="excel">Excel</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">수신자 이메일 (콤마로 구분)</label>
                        <input type="email" class="form-control" id="auto-recipients" 
                               placeholder="{user_email}, user2@example.com"
                               value="{user_email}">
                    </div>
                </div>
            </div>
            
            <button class="btn btn-light" onclick="setupAutoReport()">
                <i class="fas fa-cog me-1"></i>자동 리포트 설정
            </button>
        </div>
        """}

        <!-- 리포트 히스토리 -->
        <div class="report-card mt-4">
            <h5><i class="fas fa-history me-2"></i>최근 생성된 리포트</h5>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>리포트명</th>
                            <th>유형</th>
                            <th>생성일시</th>
                            <th>크기</th>
                            <th>다운로드</th>
                        </tr>
                    </thead>
                    <tbody id="report-history">
                        <tr>
                            <td colspan="5" class="text-center text-muted">
                                <i class="fas fa-spinner fa-spin me-2"></i>리포트 히스토리를 불러오는 중...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- 로딩 오버레이 -->
    <div class="loading-overlay" id="loading-overlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <h5>리포트 생성 중...</h5>
            <p class="text-muted">잠시만 기다려주세요</p>
        </div>
    </div>

    <!-- 미리보기 모달 -->
    <div class="modal fade" id="previewModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">리포트 미리보기</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body" id="preview-content">
                    <div class="text-center">
                        <div class="spinner mb-3"></div>
                        <p>미리보기를 준비하고 있습니다...</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let selectedPeriod = '3months';
        let previewModal;
        
        document.addEventListener('DOMContentLoaded', function() {{
            previewModal = new bootstrap.Modal(document.getElementById('previewModal'));
            loadReportHistory();
        }});
        
        function selectPeriod(period, btn) {{
            selectedPeriod = period;
            
            // 버튼 상태 업데이트
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 기간 텍스트 업데이트
            const periodTexts = {{
                '3months': '최근 3개월',
                '6months': '최근 6개월',
                '12months': '최근 12개월',
                '2years': '최근 2년'
            }};
            
            document.getElementById('selected-period').textContent = periodTexts[period];
        }}
        
        async function downloadReport(reportType, format) {{
            const loadingOverlay = document.getElementById('loading-overlay');
            
            try {{
                loadingOverlay.style.display = 'flex';
                
                let endpoint;
                if (reportType === 'business') {{
                    endpoint = format === 'excel' ? '/api/reports/business-excel' : '/api/reports/business-pdf';
                }} else if (reportType === 'comprehensive') {{
                    endpoint = format === 'excel' ? '/api/reports/comprehensive-excel' : '/api/reports/comprehensive-pdf';
                }} else if (reportType === 'task_efficiency') {{
                    endpoint = format === 'excel' ? '/api/reports/task-efficiency-excel' : '/api/reports/task-efficiency-pdf';
                }}
                
                const response = await fetch(`${{endpoint}}?period=${{selectedPeriod}}`, {{
                    method: 'GET',
                    headers: {{
                        'Accept': format === 'excel' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'application/pdf'
                    }}
                }});
                
                if (!response.ok) {{
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '리포트 생성에 실패했습니다');
                }}
                
                // 파일 다운로드
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `report_${{reportType}}_${{selectedPeriod}}.${{format === 'excel' ? 'xlsx' : 'pdf'}}`;
                
                if (contentDisposition) {{
                    const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
                    if (filenameMatch) {{
                        filename = filenameMatch[1].replace(/['"]/g, '');
                    }}
                }}
                
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                // 성공 메시지
                showAlert('success', '리포트 다운로드가 완료되었습니다!');
                
                // 히스토리 새로고침
                setTimeout(loadReportHistory, 1000);
                
            }} catch (error) {{
                console.error('리포트 다운로드 실패:', error);
                showAlert('danger', error.message || '리포트 다운로드 중 오류가 발생했습니다');
            }} finally {{
                loadingOverlay.style.display = 'none';
            }}
        }}
        
        async function previewReport(reportType) {{
            const previewContent = document.getElementById('preview-content');
            
            try {{
                previewContent.innerHTML = `
                    <div class="text-center">
                        <div class="spinner mb-3"></div>
                        <p>미리보기를 준비하고 있습니다...</p>
                    </div>
                `;
                
                previewModal.show();
                
                const response = await fetch(`/api/reports/preview?report_type=${{reportType}}&period=${{selectedPeriod}}`);
                const data = await response.json();
                
                if (!data.success) {{
                    throw new Error(data.detail || '미리보기 생성 실패');
                }}
                
                // 미리보기 내용 생성
                const preview = data.preview;
                const summary = preview.summary;
                
                previewContent.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6><i class="fas fa-chart-bar me-2"></i>핵심 지표</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row text-center">
                                        <div class="col-6">
                                            <h4 class="text-primary">${{summary.total_tasks || 0}}</h4>
                                            <small class="text-muted">전체 업무</small>
                                        </div>
                                        <div class="col-6">
                                            <h4 class="text-success">${{summary.completed_tasks || 0}}</h4>
                                            <small class="text-muted">완료 업무</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6><i class="fas fa-percentage me-2"></i>완료율</h6>
                                </div>
                                <div class="card-body text-center">
                                    <h3 class="text-info">${{(summary.completion_rate || 0).toFixed(1)}}%</h3>
                                    <div class="progress">
                                        <div class="progress-bar bg-info" style="width: ${{summary.completion_rate || 0}}%"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>분석 기간:</strong> ${{summary.period}} | 
                            <strong>리포트 유형:</strong> ${{summary.report_type}}
                        </div>
                        <p class="text-muted">
                            <i class="fas fa-download me-1"></i>
                            전체 리포트를 다운로드하시면 더 상세한 분석 결과를 확인할 수 있습니다.
                        </p>
                    </div>
                `;
                
            }} catch (error) {{
                console.error('미리보기 실패:', error);
                previewContent.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        미리보기를 불러올 수 없습니다: ${{error.message}}
                    </div>
                `;
            }}
        }}
        
        async function setupAutoReport() {{
            const reportType = document.getElementById('auto-report-type').value;
            const frequency = document.getElementById('auto-frequency').value;
            const format = document.getElementById('auto-format').value;
            const recipients = document.getElementById('auto-recipients').value;
            
            try {{
                const response = await fetch('/api/reports/schedule-auto-report', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        report_type: reportType,
                        frequency: frequency,
                        format_type: format,
                        email_recipients: recipients
                    }})
                }});
                
                const data = await response.json();
                
                if (data.success) {{
                    showAlert('success', '자동 리포트 설정이 완료되었습니다!');
                }} else {{
                    throw new Error(data.detail || '설정 실패');
                }}
                
            }} catch (error) {{
                console.error('자동 리포트 설정 실패:', error);
                showAlert('danger', error.message || '자동 리포트 설정 중 오류가 발생했습니다');
            }}
        }}
        
        async function loadReportHistory() {{
            const historyElement = document.getElementById('report-history');
            
            try {{
                // 실제로는 리포트 히스토리 API를 호출해야 합니다
                // 현재는 샘플 데이터로 대체
                setTimeout(() => {{
                    historyElement.innerHTML = `
                        <tr>
                            <td colspan="5" class="text-center text-muted">
                                <i class="fas fa-inbox me-2"></i>아직 생성된 리포트가 없습니다
                            </td>
                        </tr>
                    `;
                }}, 1000);
                
            }} catch (error) {{
                console.error('히스토리 로딩 실패:', error);
                historyElement.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>히스토리를 불러올 수 없습니다
                        </td>
                    </tr>
                `;
            }}
        }}
        
        function showAlert(type, message) {{
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${{type}} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 10000; min-width: 300px;';
            alertDiv.innerHTML = `
                ${{message}}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(alertDiv);
            
            setTimeout(() => {{
                if (alertDiv.parentNode) {{
                    alertDiv.parentNode.removeChild(alertDiv);
                }}
            }}, 5000);
        }}
        
        function logout() {{
            if (confirm('정말 로그아웃하시겠습니까?')) {{
                window.location.href = '/logout';
            }}
        }}
    </script>
</body>
</html>
"""
    
    return HTMLResponse(content=html_content)