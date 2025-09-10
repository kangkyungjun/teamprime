"""
업무 관리 관련 뷰 라우터
- 업무 대시보드
- 업무 생성/수정 페이지
- 업무 상세 페이지
- 마일스톤 시각화
"""

import logging
from typing import Optional, Dict
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)
task_views_router = APIRouter()

@task_views_router.get("/tasks", response_class=HTMLResponse)
async def task_dashboard(request: Request):
    """업무 관리 대시보드 - 새로운 업무 목록 페이지로 리다이렉트"""
    # 인증 확인 후 새로운 페이지로 리다이렉트
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 새로운 업무 목록 페이지로 리다이렉트
    return RedirectResponse(url="/task-list")

@task_views_router.get("/tasks-legacy", response_class=HTMLResponse)
async def task_dashboard_legacy(request: Request):
    """기존 업무 관리 대시보드 (백업용)"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_id = current_user.get('id')
    role = current_user.get('role', 'user')
    
    # 권한 확인
    from core.auth.owner_system import owner_system
    can_create_tasks = await owner_system.has_task_management_permission(user_id)
    can_approve = await owner_system.has_approval_permission(user_id)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>업무 관리 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
                padding: 20px 0;
            }}
            
            .main-container {{
                max-width: 1400px;
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
            
            .task-grid {{
                display: grid;
                grid-template-columns: 1fr 350px;
                gap: 30px;
            }}
            
            .task-list {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .task-sidebar {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            
            .sidebar-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .task-item {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
                border-left: 4px solid #007bff;
                transition: all 0.3s ease;
            }}
            
            .task-item:hover {{
                transform: translateX(5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .task-item.high-priority {{
                border-left-color: #dc3545;
            }}
            
            .task-item.medium-priority {{
                border-left-color: #ffc107;
            }}
            
            .task-item.low-priority {{
                border-left-color: #28a745;
            }}
            
            .task-status {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-pending {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .status-in-progress {{
                background: #cce5ff;
                color: #0066cc;
            }}
            
            .status-completed {{
                background: #d4edda;
                color: #155724;
            }}
            
            .status-cancelled {{
                background: #f8d7da;
                color: #721c24;
            }}
            
            .btn-create {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                color: white;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            
            .btn-create:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                color: white;
            }}
            
            .filter-tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 25px;
                flex-wrap: wrap;
            }}
            
            .filter-tab {{
                padding: 8px 16px;
                border: 2px solid #dee2e6;
                border-radius: 20px;
                background: white;
                color: #6c757d;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 500;
            }}
            
            .filter-tab.active {{
                background: #007bff;
                color: white;
                border-color: #007bff;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            
            .stat-item {{
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: 700;
                color: #007bff;
                display: block;
            }}
            
            .stat-label {{
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }}
            
            .loading {{
                text-align: center;
                padding: 50px;
                color: #6c757d;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 50px;
                color: #6c757d;
            }}
            
            .milestone-view {{
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            @media (max-width: 768px) {{
                .task-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header-section {{
                    padding: 20px;
                }}
                
                .task-list, .sidebar-card {{
                    padding: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <!-- Header Section -->
            <div class="header-section">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h1 class="mb-2"><i class="fas fa-tasks me-3"></i>업무 관리</h1>
                        <p class="text-muted mb-0">{username}님의 업무 대시보드</p>
                    </div>
                    <div class="d-flex gap-3">
                        {'<button class="btn btn-create" onclick="showCreateTaskModal()"><i class="fas fa-plus me-2"></i>새 업무</button>' if can_create_tasks else ''}
                        <a href="/main-dashboard" class="btn btn-outline-primary">
                            <i class="fas fa-home me-2"></i>대시보드
                        </a>
                    </div>
                </div>
                
                <!-- 통계 카드 -->
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number" id="totalTasks">-</span>
                        <div class="stat-label">전체 업무</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="inProgressTasks">-</span>
                        <div class="stat-label">진행중</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="completedTasks">-</span>
                        <div class="stat-label">완료</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="myTasks">-</span>
                        <div class="stat-label">내 업무</div>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="task-grid">
                <!-- Task List -->
                <div class="task-list">
                    <!-- Filter Tabs -->
                    <div class="filter-tabs">
                        <div class="filter-tab active" data-status="all">전체</div>
                        <div class="filter-tab" data-status="pending">대기중</div>
                        <div class="filter-tab" data-status="in_progress">진행중</div>
                        <div class="filter-tab" data-status="completed">완료</div>
                        <div class="filter-tab" data-category="all">모든 분야</div>
                    </div>
                    
                    <!-- Task Items Container -->
                    <div id="taskContainer">
                        <div class="loading">
                            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                            <p>업무 목록을 불러오는 중...</p>
                        </div>
                    </div>
                    
                    <!-- Pagination -->
                    <nav aria-label="업무 페이지네이션" class="mt-4">
                        <ul class="pagination justify-content-center" id="pagination">
                            <!-- 동적으로 생성됨 -->
                        </ul>
                    </nav>
                </div>
                
                <!-- Sidebar -->
                <div class="task-sidebar">
                    <!-- 빠른 액션 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-bolt me-2"></i>빠른 액션</h5>
                        <div class="d-grid gap-2">
                            {'<button class="btn btn-sm btn-outline-primary" onclick="showCreateTaskModal()">업무 생성</button>' if can_create_tasks else ''}
                            <button class="btn btn-sm btn-outline-success" onclick="filterMyTasks()">내 업무만</button>
                            <button class="btn btn-sm btn-outline-info" onclick="showMilestoneView()">마일스톤 보기</button>
                            {'<button class="btn btn-sm btn-outline-warning" onclick="showApprovalQueue()">승인 대기</button>' if can_approve else ''}
                        </div>
                    </div>
                    
                    <!-- 분야별 필터 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-filter me-2"></i>분야별 필터</h5>
                        <div class="d-grid gap-1">
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="all">전체</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="기획">기획</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="개발">개발</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="디자인">디자인</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="운영">운영</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="영업">영업</button>
                            <button class="btn btn-sm btn-outline-secondary filter-category" data-category="기타">기타</button>
                        </div>
                    </div>
                    
                    <!-- 최근 활동 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-history me-2"></i>최근 활동</h5>
                        <div id="recentActivity">
                            <div class="text-center text-muted">
                                <i class="fas fa-spinner fa-spin"></i>
                                <small class="d-block mt-2">불러오는 중...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 마일스톤 뷰 -->
            <div id="milestoneView" class="milestone-view" style="display: none;">
                <h4><i class="fas fa-map-signs me-2"></i>프로젝트 마일스톤</h4>
                <div id="milestoneChart">
                    <!-- 마일스톤 차트가 여기에 렌더링됨 -->
                </div>
            </div>
        </div>
        
        <!-- 업무 생성/수정 모달 -->
        <div class="modal fade" id="taskModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="taskModalTitle">새 업무 생성</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="taskForm">
                            <input type="hidden" id="taskId">
                            <div class="row">
                                <div class="col-md-8">
                                    <div class="mb-3">
                                        <label class="form-label">업무 제목 *</label>
                                        <input type="text" class="form-control" id="taskTitle" required>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="mb-3">
                                        <label class="form-label">우선순위</label>
                                        <select class="form-select" id="taskPriority">
                                            <option value="low">낮음</option>
                                            <option value="medium" selected>보통</option>
                                            <option value="high">높음</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">분야</label>
                                        <select class="form-select" id="taskCategory">
                                            <option value="기획">기획</option>
                                            <option value="개발">개발</option>
                                            <option value="디자인">디자인</option>
                                            <option value="운영">운영</option>
                                            <option value="영업">영업</option>
                                            <option value="고객지원">고객지원</option>
                                            <option value="회계">회계</option>
                                            <option value="법무">법무</option>
                                            <option value="교육">교육</option>
                                            <option value="유지보수">유지보수</option>
                                            <option value="기타">기타</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">담당자</label>
                                        <select class="form-select" id="taskAssignee">
                                            <option value="">선택 안함</option>
                                            <!-- 사용자 목록이 동적으로 로드됨 -->
                                        </select>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">시작일</label>
                                        <input type="date" class="form-control" id="taskStartDate">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">마감일</label>
                                        <input type="date" class="form-control" id="taskDueDate">
                                    </div>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">설명</label>
                                <textarea class="form-control" id="taskDescription" rows="4"></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">예상 시간 (시간)</label>
                                        <input type="number" class="form-control" id="taskEstimatedHours" min="0" step="0.5">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">상위 업무</label>
                                        <select class="form-select" id="taskParent">
                                            <option value="">선택 안함</option>
                                            <!-- 상위 업무 목록이 동적으로 로드됨 -->
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                        <button type="button" class="btn btn-primary" onclick="saveTask()">저장</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 업무 상세 모달 -->
        <div class="modal fade" id="taskDetailModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">업무 상세</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="taskDetailContent">
                        <!-- 업무 상세 내용이 동적으로 로드됨 -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                        <div class="btn-group" id="taskDetailActions">
                            <!-- 동적으로 액션 버튼들이 추가됨 -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentPage = 1;
            let currentFilters = {{ status: 'all', category: 'all', assignee: null }};
            let tasks = [];
            let users = [];
            
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                loadUsers();
                loadTasks();
                loadStats();
                setupEventListeners();
            }});
            
            // 이벤트 리스너 설정
            function setupEventListeners() {{
                // 필터 탭 클릭
                document.querySelectorAll('.filter-tab').forEach(tab => {{
                    tab.addEventListener('click', function() {{
                        // 활성 탭 업데이트
                        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                        this.classList.add('active');
                        
                        // 필터 적용
                        const status = this.getAttribute('data-status');
                        const category = this.getAttribute('data-category');
                        
                        if (status) {{
                            currentFilters.status = status;
                        }}
                        if (category) {{
                            currentFilters.category = category;
                        }}
                        
                        currentPage = 1;
                        loadTasks();
                    }});
                }});
                
                // 분야별 필터 버튼
                document.querySelectorAll('.filter-category').forEach(btn => {{
                    btn.addEventListener('click', function() {{
                        document.querySelectorAll('.filter-category').forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        
                        currentFilters.category = this.getAttribute('data-category');
                        currentPage = 1;
                        loadTasks();
                    }});
                }});
            }}
            
            // 사용자 목록 로드
            async function loadUsers() {{
                try {{
                    const response = await fetch('/api/users/list');
                    if (response.ok) {{
                        users = await response.json();
                        populateUserDropdowns();
                    }}
                }} catch (error) {{
                    console.error('사용자 목록 로드 오류:', error);
                }}
            }}
            
            // 사용자 드롭다운 채우기
            function populateUserDropdowns() {{
                const assigneeSelect = document.getElementById('taskAssignee');
                assigneeSelect.innerHTML = '<option value="">선택 안함</option>';
                
                users.forEach(user => {{
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = `${{user.username}} (${{user.role}})`;
                    assigneeSelect.appendChild(option);
                }});
            }}
            
            // 통계 데이터 로드
            async function loadStats() {{
                try {{
                    const response = await fetch('/api/business/dashboard-stats');
                    if (response.ok) {{
                        const stats = await response.json();
                        
                        document.getElementById('totalTasks').textContent = stats.total_tasks || 0;
                        document.getElementById('inProgressTasks').textContent = stats.in_progress_tasks || 0;
                        document.getElementById('completedTasks').textContent = stats.completed_tasks || 0;
                        document.getElementById('myTasks').textContent = stats.my_tasks || 0;
                    }}
                }} catch (error) {{
                    console.error('통계 로드 오류:', error);
                }}
            }}
            
            // 업무 목록 로드
            async function loadTasks() {{
                try {{
                    const params = new URLSearchParams({{
                        page: currentPage,
                        limit: 10
                    }});
                    
                    if (currentFilters.status !== 'all') {{
                        params.append('status', currentFilters.status);
                    }}
                    if (currentFilters.category !== 'all') {{
                        params.append('category', currentFilters.category);
                    }}
                    if (currentFilters.assignee) {{
                        params.append('assignee_id', currentFilters.assignee);
                    }}
                    
                    const response = await fetch(`/api/business/tasks?${{params}}`);
                    if (response.ok) {{
                        const data = await response.json();
                        tasks = data.tasks || [];
                        renderTasks(tasks);
                        renderPagination(data.total || 0, data.page || 1, data.limit || 10);
                    }} else {{
                        throw new Error('업무 목록을 불러올 수 없습니다');
                    }}
                }} catch (error) {{
                    console.error('업무 로드 오류:', error);
                    document.getElementById('taskContainer').innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3 text-warning"></i>
                            <p>업무 목록을 불러올 수 없습니다.</p>
                            <button class="btn btn-primary" onclick="loadTasks()">다시 시도</button>
                        </div>
                    `;
                }}
            }}
            
            // 업무 목록 렌더링
            function renderTasks(taskList) {{
                const container = document.getElementById('taskContainer');
                
                if (taskList.length === 0) {{
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-tasks fa-2x mb-3 text-muted"></i>
                            <p>조건에 맞는 업무가 없습니다.</p>
                        </div>
                    `;
                    return;
                }}
                
                container.innerHTML = taskList.map(task => `
                    <div class="task-item ${{task.priority}}-priority" onclick="showTaskDetail(${{task.id}})">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${{task.title}}</h6>
                                <small class="text-muted">${{task.category}} | 담당자: ${{task.assignee_name || '미지정'}}</small>
                            </div>
                            <span class="task-status status-${{task.status.replace('_', '-')}}">${{getStatusText(task.status)}}</span>
                        </div>
                        <p class="mb-2 text-muted small">${{task.description ? task.description.substring(0, 100) + '...' : '설명 없음'}}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="small text-muted">
                                <i class="fas fa-calendar me-1"></i>
                                ${{task.due_date ? formatDate(task.due_date) : '마감일 없음'}}
                            </div>
                            <div class="small text-muted">
                                <i class="fas fa-flag me-1"></i>
                                ${{getPriorityText(task.priority)}}
                            </div>
                        </div>
                    </div>
                `).join('');
            }}
            
            // 페이지네이션 렌더링
            function renderPagination(total, page, limit) {{
                const totalPages = Math.ceil(total / limit);
                const pagination = document.getElementById('pagination');
                
                if (totalPages <= 1) {{
                    pagination.innerHTML = '';
                    return;
                }}
                
                let html = '';
                
                // 이전 페이지
                if (page > 1) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page - 1}})">이전</a></li>`;
                }}
                
                // 페이지 번호들
                for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {{
                    html += `<li class="page-item ${{i === page ? 'active' : ''}}">
                        <a class="page-link" href="#" onclick="changePage(${{i}})">${{i}}</a>
                    </li>`;
                }}
                
                // 다음 페이지
                if (page < totalPages) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page + 1}})">다음</a></li>`;
                }}
                
                pagination.innerHTML = html;
            }}
            
            // 페이지 변경
            function changePage(page) {{
                currentPage = page;
                loadTasks();
            }}
            
            // 업무 생성 모달 표시
            function showCreateTaskModal() {{
                document.getElementById('taskModalTitle').textContent = '새 업무 생성';
                document.getElementById('taskForm').reset();
                document.getElementById('taskId').value = '';
                new bootstrap.Modal(document.getElementById('taskModal')).show();
            }}
            
            // 업무 저장
            async function saveTask() {{
                const taskId = document.getElementById('taskId').value;
                const isEdit = !!taskId;
                
                // 폼 검증
                const title = document.getElementById('taskTitle').value.trim();
                if (!title) {{
                    alert('업무 제목을 입력해주세요.');
                    document.getElementById('taskTitle').focus();
                    return;
                }}
                
                if (title.length > 200) {{
                    alert('업무 제목은 200자를 초과할 수 없습니다.');
                    document.getElementById('taskTitle').focus();
                    return;
                }}
                
                const startDate = document.getElementById('taskStartDate').value;
                const endDate = document.getElementById('taskDueDate').value;
                
                if (startDate && endDate && new Date(startDate) > new Date(endDate)) {{
                    alert('시작일은 마감일보다 늦을 수 없습니다.');
                    document.getElementById('taskStartDate').focus();
                    return;
                }}
                
                const taskData = {{
                    title: title,
                    description: document.getElementById('taskDescription').value.trim(),
                    category: document.getElementById('taskCategory').value,
                    assignee_id: document.getElementById('taskAssignee').value || null,
                    start_date: startDate || null,
                    end_date: endDate || null
                }};
                
                // 저장 버튼 비활성화
                const saveBtn = document.querySelector('#taskModal .btn-primary');
                const originalText = saveBtn.textContent;
                saveBtn.disabled = true;
                saveBtn.textContent = '저장 중...';
                
                try {{
                    const url = isEdit ? `/api/business/tasks/${{taskId}}` : '/api/business/tasks';
                    const method = isEdit ? 'PUT' : 'POST';
                    
                    const response = await fetch(url, {{
                        method: method,
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(taskData)
                    }});
                    
                    if (response.ok) {{
                        bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
                        loadTasks();
                        loadStats();
                        showToast(isEdit ? '업무가 수정되었습니다.' : '업무가 생성되었습니다.', 'success');
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '알 수 없는 오류'));
                    }}
                }} catch (error) {{
                    console.error('업무 저장 오류:', error);
                    alert('업무 저장 중 오류가 발생했습니다.');
                }} finally {{
                    // 저장 버튼 복원
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }}
            }}
            
            // 토스트 알림 표시
            function showToast(message, type = 'info') {{
                // Bootstrap 토스트가 없으므로 간단한 알림으로 대체
                const toastDiv = document.createElement('div');
                toastDiv.className = `alert alert-${{type === 'success' ? 'success' : 'info'}} toast-notification`;
                toastDiv.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    min-width: 300px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                `;
                toastDiv.textContent = message;
                
                document.body.appendChild(toastDiv);
                
                // 3초 후 자동 제거
                setTimeout(() => {{
                    toastDiv.remove();
                }}, 3000);
            }}
            
            // 업무 상세 보기
            async function showTaskDetail(taskId) {{
                try {{
                    const response = await fetch(`/api/business/tasks/${{taskId}}`);
                    if (response.ok) {{
                        const task = await response.json();
                        renderTaskDetail(task);
                        new bootstrap.Modal(document.getElementById('taskDetailModal')).show();
                    }}
                }} catch (error) {{
                    console.error('업무 상세 로드 오류:', error);
                    alert('업무 상세 정보를 불러올 수 없습니다.');
                }}
            }}
            
            // 업무 상세 렌더링
            function renderTaskDetail(task) {{
                const content = document.getElementById('taskDetailContent');
                content.innerHTML = `
                    <div class="row">
                        <div class="col-md-8">
                            <h4>${{task.title}}</h4>
                            <p class="text-muted">${{task.description || '설명 없음'}}</p>
                        </div>
                        <div class="col-md-4">
                            <span class="task-status status-${{task.status.replace('_', '-')}}">${{getStatusText(task.status)}}</span>
                        </div>
                    </div>
                    <hr>
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>분야:</strong> ${{task.category}}</p>
                            <p><strong>우선순위:</strong> ${{getPriorityText(task.priority)}}</p>
                            <p><strong>담당자:</strong> ${{task.assignee_name || '미지정'}}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>시작일:</strong> ${{task.start_date ? formatDate(task.start_date) : '미설정'}}</p>
                            <p><strong>마감일:</strong> ${{task.due_date ? formatDate(task.due_date) : '미설정'}}</p>
                            <p><strong>예상 시간:</strong> ${{task.estimated_hours ? task.estimated_hours + '시간' : '미설정'}}</p>
                        </div>
                    </div>
                    ${{task.parent_task ? `<p><strong>상위 업무:</strong> ${{task.parent_task.title}}</p>` : ''}}
                    <div class="mt-3">
                        <small class="text-muted">생성일: ${{formatDate(task.created_at)}}</small>
                        ${{task.updated_at !== task.created_at ? `<br><small class="text-muted">수정일: ${{formatDate(task.updated_at)}}</small>` : ''}}
                    </div>
                `;
                
                // 액션 버튼들
                const actions = document.getElementById('taskDetailActions');
                actions.innerHTML = `
                    <button class="btn btn-primary" onclick="editTask(${{task.id}})">수정</button>
                    <button class="btn btn-danger" onclick="deleteTask(${{task.id}})">삭제</button>
                `;
            }}
            
            // 내 업무만 필터링
            function filterMyTasks() {{
                currentFilters.assignee = {user_id};
                currentPage = 1;
                loadTasks();
            }}
            
            // 마일스톤 뷰 토글
            function showMilestoneView() {{
                const milestoneView = document.getElementById('milestoneView');
                if (milestoneView.style.display === 'none') {{
                    milestoneView.style.display = 'block';
                    loadMilestones();
                }} else {{
                    milestoneView.style.display = 'none';
                }}
            }}
            
            // 마일스톤 로드
            async function loadMilestones() {{
                try {{
                    const response = await fetch('/api/business/task-relationships');
                    if (response.ok) {{
                        const relationships = await response.json();
                        renderMilestones(relationships);
                    }}
                }} catch (error) {{
                    console.error('마일스톤 로드 오류:', error);
                }}
            }}
            
            // 마일스톤 렌더링
            function renderMilestones(relationships) {{
                const chart = document.getElementById('milestoneChart');
                // 간단한 마일스톤 차트 렌더링 (실제로는 더 복잡한 차트 라이브러리 사용)
                chart.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        마일스톤 시각화 기능은 개발 중입니다.
                        현재 ${{relationships.length}}개의 업무 관계가 있습니다.
                    </div>
                `;
            }}
            
            // 유틸리티 함수들
            function getStatusText(status) {{
                const statusMap = {{
                    'pending': '대기중',
                    'in_progress': '진행중',
                    'completed': '완료',
                    'cancelled': '취소됨'
                }};
                return statusMap[status] || status;
            }}
            
            function getPriorityText(priority) {{
                const priorityMap = {{
                    'low': '낮음',
                    'medium': '보통',
                    'high': '높음'
                }};
                return priorityMap[priority] || priority;
            }}
            
            function formatDate(dateString) {{
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR');
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@task_views_router.get("/incomes", response_class=HTMLResponse)
async def income_dashboard(request: Request):
    """수익 관리 대시보드 - 새로운 손익 페이지로 리다이렉트"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 새로운 손익 관리 통합 페이지로 리다이렉트
    return RedirectResponse(url="/profit-loss")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>수익 관리 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
                padding: 20px 0;
            }}
            
            .main-container {{
                max-width: 1400px;
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
            
            .income-grid {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 30px;
            }}
            
            .income-list {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .income-sidebar {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            
            .sidebar-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .income-item {{
                background: #f0f8f0;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
                border-left: 4px solid #4caf50;
                transition: all 0.3s ease;
            }}
            
            .income-item:hover {{
                transform: translateX(5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .amount {{
                font-size: 18px;
                font-weight: 700;
                color: #4caf50;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            
            .stat-item {{
                text-align: center;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .stat-number {{
                font-size: 24px;
                font-weight: 700;
                color: #4caf50;
                display: block;
            }}
            
            .stat-label {{
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }}
            
            .filter-tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 25px;
                flex-wrap: wrap;
            }}
            
            .filter-tab {{
                padding: 8px 16px;
                border: 2px solid #dee2e6;
                border-radius: 20px;
                background: white;
                color: #6c757d;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 500;
            }}
            
            .filter-tab.active {{
                background: #4caf50;
                color: white;
                border-color: #4caf50;
            }}
            
            .btn-create {{
                background: linear-gradient(45deg, #4caf50, #45a049);
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                color: white;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            
            .btn-create:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                color: white;
            }}
            
            @media (max-width: 768px) {{
                .income-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header-section {{
                    padding: 20px;
                }}
                
                .income-list, .sidebar-card {{
                    padding: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <!-- Header Section -->
            <div class="header-section">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h1 class="mb-2"><i class="fas fa-chart-line me-3"></i>수익 관리</h1>
                        <p class="text-muted mb-0">{username}님의 수익 추적 시스템</p>
                    </div>
                    <div class="d-flex gap-3">
                        {'<button class="btn btn-create" onclick="showIncomeModal()"><i class="fas fa-plus me-2"></i>수익 등록</button>' if can_add_income else ''}
                        <a href="/main-dashboard" class="btn btn-outline-success">
                            <i class="fas fa-home me-2"></i>대시보드
                        </a>
                    </div>
                </div>
                
                <!-- 통계 카드 -->
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number" id="totalIncomes">-</span>
                        <div class="stat-label">총 수익 건수</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="totalAmount">-</span>
                        <div class="stat-label">총 수익 금액</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="monthlyIncome">-</span>
                        <div class="stat-label">이번달 수익</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="avgIncome">-</span>
                        <div class="stat-label">평균 수익</div>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="income-grid">
                <!-- Income List -->
                <div class="income-list">
                    <!-- Filter Tabs -->
                    <div class="filter-tabs">
                        <div class="filter-tab active" data-category="all">전체</div>
                        <div class="filter-tab" data-category="매출">매출</div>
                        <div class="filter-tab" data-category="투자수익">투자수익</div>
                        <div class="filter-tab" data-category="부수입">부수입</div>
                        <div class="filter-tab" data-category="기타">기타</div>
                    </div>
                    
                    <!-- Income Items Container -->
                    <div id="incomeContainer">
                        <div class="loading text-center">
                            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                            <p>수익 목록을 불러오는 중...</p>
                        </div>
                    </div>
                    
                    <!-- Pagination -->
                    <nav aria-label="수익 페이지네이션" class="mt-4">
                        <ul class="pagination justify-content-center" id="incomePagination">
                        </ul>
                    </nav>
                </div>
                
                <!-- Sidebar -->
                <div class="income-sidebar">
                    <!-- 빠른 액션 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-bolt me-2"></i>빠른 액션</h5>
                        <div class="d-grid gap-2">
                            {'<button class="btn btn-sm btn-outline-success" onclick="showIncomeModal()">수익 등록</button>' if can_add_income else ''}
                            <button class="btn btn-sm btn-outline-primary" onclick="exportIncomes()">내보내기</button>
                            <button class="btn btn-sm btn-outline-info" onclick="showAnalytics()">분석 보기</button>
                            <button class="btn btn-sm btn-outline-warning" onclick="showTrends()">추세 분석</button>
                        </div>
                    </div>
                    
                    <!-- 월별 통계 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-chart-bar me-2"></i>월별 통계</h5>
                        <div id="monthlyStats">
                            <div class="text-center text-muted">
                                <i class="fas fa-spinner fa-spin"></i>
                                <small class="d-block mt-2">불러오는 중...</small>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 카테고리별 분석 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-pie-chart me-2"></i>카테고리별 분석</h5>
                        <div id="categoryAnalysis">
                            <div class="text-center text-muted">
                                <i class="fas fa-spinner fa-spin"></i>
                                <small class="d-block mt-2">불러오는 중...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 수익 등록 모달 -->
        <div class="modal fade" id="incomeModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="incomeModalTitle">수익 등록</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="incomeForm">
                            <input type="hidden" id="incomeId">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">제목 *</label>
                                        <input type="text" class="form-control" id="incomeTitle" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">금액 *</label>
                                        <div class="input-group">
                                            <input type="number" class="form-control" id="incomeAmount" required min="0">
                                            <span class="input-group-text">원</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">분야</label>
                                        <select class="form-select" id="incomeCategory">
                                            <option value="매출">매출</option>
                                            <option value="투자수익">투자수익</option>
                                            <option value="이자소득">이자소득</option>
                                            <option value="배당소득">배당소득</option>
                                            <option value="부수입">부수입</option>
                                            <option value="기타">기타</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">수익 발생일 *</label>
                                        <input type="date" class="form-control" id="incomeDate" required>
                                    </div>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">설명</label>
                                <textarea class="form-control" id="incomeDescription" rows="3"></textarea>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">세금 (원)</label>
                                        <input type="number" class="form-control" id="incomeTax" min="0" value="0">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">순수익</label>
                                        <input type="number" class="form-control" id="netIncome" readonly>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                        <button type="button" class="btn btn-success" onclick="saveIncome()">저장</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentPage = 1;
            let currentCategory = 'all';
            let incomes = [];
            
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                setupEventListeners();
                loadIncomes();
                loadStats();
                
                // 오늘 날짜를 기본값으로 설정
                document.getElementById('incomeDate').valueAsDate = new Date();
            }});
            
            // 이벤트 리스너 설정
            function setupEventListeners() {{
                // 카테고리 필터 탭
                document.querySelectorAll('.filter-tab').forEach(tab => {{
                    tab.addEventListener('click', function() {{
                        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                        this.classList.add('active');
                        
                        currentCategory = this.getAttribute('data-category');
                        currentPage = 1;
                        loadIncomes();
                    }});
                }});
                
                // 금액 변경 시 순수익 계산
                document.getElementById('incomeAmount').addEventListener('input', calculateNetIncome);
                document.getElementById('incomeTax').addEventListener('input', calculateNetIncome);
            }}
            
            // 순수익 계산
            function calculateNetIncome() {{
                const amount = parseFloat(document.getElementById('incomeAmount').value) || 0;
                const tax = parseFloat(document.getElementById('incomeTax').value) || 0;
                const netIncome = amount - tax;
                document.getElementById('netIncome').value = netIncome;
            }}
            
            // 통계 데이터 로드
            async function loadStats() {{
                try {{
                    const response = await fetch('/api/business/dashboard-stats');
                    if (response.ok) {{
                        const stats = await response.json();
                        
                        document.getElementById('totalIncomes').textContent = stats.total_incomes || 0;
                        document.getElementById('totalAmount').textContent = 
                            (stats.total_income_amount || 0).toLocaleString() + '원';
                        document.getElementById('monthlyIncome').textContent = 
                            (stats.monthly_income || 0).toLocaleString() + '원';
                        document.getElementById('avgIncome').textContent = 
                            (stats.avg_income || 0).toLocaleString() + '원';
                    }}
                }} catch (error) {{
                    console.error('통계 로드 오류:', error);
                }}
            }}
            
            // 수익 목록 로드
            async function loadIncomes() {{
                try {{
                    const params = new URLSearchParams({{
                        page: currentPage,
                        limit: 10
                    }});
                    
                    if (currentCategory !== 'all') {{
                        params.append('category', currentCategory);
                    }}
                    
                    const response = await fetch(`/api/business/incomes?${{params}}`);
                    if (response.ok) {{
                        const data = await response.json();
                        incomes = data.incomes || [];
                        renderIncomes(incomes);
                        renderPagination(data.total || 0, data.page || 1, data.limit || 10);
                    }} else {{
                        throw new Error('수익 목록을 불러올 수 없습니다');
                    }}
                }} catch (error) {{
                    console.error('수익 로드 오류:', error);
                    document.getElementById('incomeContainer').innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3 text-warning"></i>
                            <p>수익 목록을 불러올 수 없습니다.</p>
                            <button class="btn btn-success" onclick="loadIncomes()">다시 시도</button>
                        </div>
                    `;
                }}
            }}
            
            // 수익 목록 렌더링
            function renderIncomes(incomeList) {{
                const container = document.getElementById('incomeContainer');
                
                if (incomeList.length === 0) {{
                    container.innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-chart-line fa-2x mb-3 text-muted"></i>
                            <p>등록된 수익이 없습니다.</p>
                        </div>
                    `;
                    return;
                }}
                
                container.innerHTML = incomeList.map(income => `
                    <div class="income-item" onclick="showIncomeDetail(${{income.id}})">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${{income.title}}</h6>
                                <small class="text-muted">${{income.category}} | ${{formatDate(income.income_date)}}</small>
                            </div>
                            <div class="text-end">
                                <div class="amount">${{income.amount.toLocaleString()}}원</div>
                                ${{income.tax ? `<small class="text-muted">세금: ${{income.tax.toLocaleString()}}원</small>` : ''}}
                            </div>
                        </div>
                        <p class="mb-2 text-muted small">${{income.description || '설명 없음'}}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="small text-muted">
                                등록자: ${{income.user_name}}
                            </div>
                            ${{income.tax ? `
                                <div class="small text-success">
                                    순수익: ${{(income.amount - income.tax).toLocaleString()}}원
                                </div>
                            ` : ''}}
                        </div>
                    </div>
                `).join('');
            }}
            
            // 수익 등록 모달 표시
            function showIncomeModal() {{
                document.getElementById('incomeModalTitle').textContent = '수익 등록';
                document.getElementById('incomeForm').reset();
                document.getElementById('incomeId').value = '';
                document.getElementById('incomeDate').valueAsDate = new Date();
                document.getElementById('incomeTax').value = '0';
                document.getElementById('netIncome').value = '0';
                new bootstrap.Modal(document.getElementById('incomeModal')).show();
            }}
            
            // 수익 저장
            async function saveIncome() {{
                const incomeId = document.getElementById('incomeId').value;
                const isEdit = !!incomeId;
                
                const incomeData = {{
                    title: document.getElementById('incomeTitle').value,
                    amount: parseFloat(document.getElementById('incomeAmount').value),
                    category: document.getElementById('incomeCategory').value,
                    description: document.getElementById('incomeDescription').value,
                    income_date: document.getElementById('incomeDate').value,
                    tax: parseFloat(document.getElementById('incomeTax').value) || 0
                }};
                
                try {{
                    const url = isEdit ? `/api/business/incomes/${{incomeId}}` : '/api/business/incomes';
                    const method = isEdit ? 'PUT' : 'POST';
                    
                    const response = await fetch(url, {{
                        method: method,
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(incomeData)
                    }});
                    
                    if (response.ok) {{
                        bootstrap.Modal.getInstance(document.getElementById('incomeModal')).hide();
                        loadIncomes();
                        loadStats();
                        alert(isEdit ? '수익이 수정되었습니다.' : '수익이 등록되었습니다.');
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '알 수 없는 오류'));
                    }}
                }} catch (error) {{
                    console.error('수익 저장 오류:', error);
                    alert('수익 저장 중 오류가 발생했습니다.');
                }}
            }}
            
            // 수익 내보내기
            function exportIncomes() {{
                window.open('/api/business/incomes/export', '_blank');
            }}
            
            // 분석 보기
            function showAnalytics() {{
                alert('분석 기능은 개발 중입니다.');
            }}
            
            // 추세 분석
            function showTrends() {{
                alert('추세 분석 기능은 개발 중입니다.');
            }}
            
            // 페이지네이션 렌더링
            function renderPagination(total, page, limit) {{
                const totalPages = Math.ceil(total / limit);
                const pagination = document.getElementById('incomePagination');
                
                if (totalPages <= 1) {{
                    pagination.innerHTML = '';
                    return;
                }}
                
                let html = '';
                
                if (page > 1) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page - 1}})">이전</a></li>`;
                }}
                
                for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {{
                    html += `<li class="page-item ${{i === page ? 'active' : ''}}">
                        <a class="page-link" href="#" onclick="changePage(${{i}})">${{i}}</a>
                    </li>`;
                }}
                
                if (page < totalPages) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page + 1}})">다음</a></li>`;
                }}
                
                pagination.innerHTML = html;
            }}
            
            // 페이지 변경
            function changePage(page) {{
                currentPage = page;
                loadIncomes();
            }}
            
            // 유틸리티 함수들
            function formatDate(dateString) {{
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR');
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@task_views_router.get("/expenses", response_class=HTMLResponse)
async def expense_dashboard(request: Request):
    """지출 관리 대시보드 - 새로운 손익 페이지로 리다이렉트"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 새로운 손익 관리 통합 페이지로 리다이렉트
    return RedirectResponse(url="/profit-loss")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>지출 관리 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
                padding: 20px 0;
            }}
            
            .main-container {{
                max-width: 1400px;
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
            
            .expense-grid {{
                display: grid;
                grid-template-columns: 1fr 350px;
                gap: 30px;
            }}
            
            .expense-list {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .expense-sidebar {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            
            .sidebar-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .expense-item {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
                border-left: 4px solid #007bff;
                transition: all 0.3s ease;
            }}
            
            .expense-item:hover {{
                transform: translateX(5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .expense-item.pending {{
                border-left-color: #ffc107;
            }}
            
            .expense-item.approved {{
                border-left-color: #28a745;
            }}
            
            .expense-item.rejected {{
                border-left-color: #dc3545;
            }}
            
            .expense-status {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-pending {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .status-approved {{
                background: #d4edda;
                color: #155724;
            }}
            
            .status-rejected {{
                background: #f8d7da;
                color: #721c24;
            }}
            
            .amount {{
                font-size: 18px;
                font-weight: 700;
                color: #007bff;
            }}
            
            .receipt-preview {{
                max-width: 100px;
                max-height: 100px;
                object-fit: cover;
                border-radius: 8px;
                cursor: pointer;
            }}
            
            .drop-zone {{
                border: 2px dashed #dee2e6;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                background: #f8f9fa;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .drop-zone.dragover {{
                border-color: #007bff;
                background: #e3f2fd;
            }}
            
            .drop-zone:hover {{
                border-color: #007bff;
            }}
            
            @media (max-width: 768px) {{
                .expense-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .header-section {{
                    padding: 20px;
                }}
                
                .expense-list, .sidebar-card {{
                    padding: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="main-container">
            <!-- Header Section -->
            <div class="header-section">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h1 class="mb-2"><i class="fas fa-receipt me-3"></i>지출 관리</h1>
                        <p class="text-muted mb-0">{username}님의 지출 관리 시스템</p>
                    </div>
                    <div class="d-flex gap-3">
                        {'<button class="btn btn-primary" onclick="showExpenseModal()"><i class="fas fa-plus me-2"></i>지출 등록</button>' if can_submit else ''}
                        <a href="/main-dashboard" class="btn btn-outline-primary">
                            <i class="fas fa-home me-2"></i>대시보드
                        </a>
                    </div>
                </div>
                
                <!-- 통계 카드 -->
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-number" id="totalExpenses">-</span>
                        <div class="stat-label">전체 지출</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="pendingExpenses">-</span>
                        <div class="stat-label">승인 대기</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="approvedAmount">-</span>
                        <div class="stat-label">승인된 금액</div>
                    </div>
                    <div class="stat-item">
                        <span class="stat-number" id="myExpenses">-</span>
                        <div class="stat-label">내 지출</div>
                    </div>
                </div>
            </div>
            
            <!-- Main Content -->
            <div class="expense-grid">
                <!-- Expense List -->
                <div class="expense-list">
                    <!-- Filter Tabs -->
                    <div class="filter-tabs mb-4">
                        <div class="btn-group" role="group">
                            <input type="radio" class="btn-check" name="statusFilter" id="allStatus" value="all" checked>
                            <label class="btn btn-outline-primary" for="allStatus">전체</label>
                            
                            <input type="radio" class="btn-check" name="statusFilter" id="pendingStatus" value="pending">
                            <label class="btn btn-outline-warning" for="pendingStatus">승인 대기</label>
                            
                            <input type="radio" class="btn-check" name="statusFilter" id="approvedStatus" value="approved">
                            <label class="btn btn-outline-success" for="approvedStatus">승인됨</label>
                            
                            <input type="radio" class="btn-check" name="statusFilter" id="rejectedStatus" value="rejected">
                            <label class="btn btn-outline-danger" for="rejectedStatus">반려됨</label>
                        </div>
                    </div>
                    
                    <!-- Expense Items Container -->
                    <div id="expenseContainer">
                        <div class="loading text-center">
                            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                            <p>지출 목록을 불러오는 중...</p>
                        </div>
                    </div>
                    
                    <!-- Pagination -->
                    <nav aria-label="지출 페이지네이션" class="mt-4">
                        <ul class="pagination justify-content-center" id="expensePagination">
                        </ul>
                    </nav>
                </div>
                
                <!-- Sidebar -->
                <div class="expense-sidebar">
                    <!-- 빠른 액션 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-bolt me-2"></i>빠른 액션</h5>
                        <div class="d-grid gap-2">
                            {'<button class="btn btn-sm btn-outline-primary" onclick="showExpenseModal()">지출 등록</button>' if can_submit else ''}
                            <button class="btn btn-sm btn-outline-success" onclick="filterMyExpenses()">내 지출만</button>
                            {'<button class="btn btn-sm btn-outline-warning" onclick="filterPendingApprovals()">승인 대기</button>' if can_approve else ''}
                            <button class="btn btn-sm btn-outline-info" onclick="exportExpenses()">내보내기</button>
                        </div>
                    </div>
                    
                    <!-- 분야별 필터 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-filter me-2"></i>분야별 필터</h5>
                        <div class="d-grid gap-1">
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="all">전체</button>
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="사무용품">사무용품</button>
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="교통비">교통비</button>
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="식비">식비</button>
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="회의비">회의비</button>
                            <button class="btn btn-sm btn-outline-secondary category-filter" data-category="기타">기타</button>
                        </div>
                    </div>
                    
                    <!-- 월별 통계 -->
                    <div class="sidebar-card">
                        <h5><i class="fas fa-chart-bar me-2"></i>월별 통계</h5>
                        <div id="monthlyStats">
                            <div class="text-center text-muted">
                                <i class="fas fa-spinner fa-spin"></i>
                                <small class="d-block mt-2">불러오는 중...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 지출 등록/수정 모달 -->
        <div class="modal fade" id="expenseModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="expenseModalTitle">지출 등록</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="expenseForm" enctype="multipart/form-data">
                            <input type="hidden" id="expenseId">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">제목 *</label>
                                        <input type="text" class="form-control" id="expenseTitle" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">금액 *</label>
                                        <div class="input-group">
                                            <input type="number" class="form-control" id="expenseAmount" required min="0">
                                            <span class="input-group-text">원</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">분야</label>
                                        <select class="form-select" id="expenseCategory">
                                            <option value="사무용품">사무용품</option>
                                            <option value="교통비">교통비</option>
                                            <option value="식비">식비</option>
                                            <option value="회의비">회의비</option>
                                            <option value="마케팅">마케팅</option>
                                            <option value="교육">교육</option>
                                            <option value="기타">기타</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">지출일 *</label>
                                        <input type="date" class="form-control" id="expenseDate" required>
                                    </div>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">설명</label>
                                <textarea class="form-control" id="expenseDescription" rows="3"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">영수증 첨부</label>
                                <div class="drop-zone" id="dropZone">
                                    <i class="fas fa-cloud-upload-alt fa-2x mb-3 text-muted"></i>
                                    <p class="mb-2">영수증을 드래그하거나 클릭하여 업로드</p>
                                    <p class="small text-muted">JPG, PNG, PDF 파일만 업로드 가능</p>
                                    <input type="file" id="receiptFile" accept="image/*,.pdf" style="display: none;">
                                </div>
                                <div id="filePreview" class="mt-3" style="display: none;">
                                    <div class="d-flex align-items-center justify-content-between p-3 bg-light rounded">
                                        <div class="d-flex align-items-center">
                                            <i class="fas fa-file-alt me-2"></i>
                                            <span id="fileName"></span>
                                        </div>
                                        <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile()">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                        <button type="button" class="btn btn-primary" onclick="saveExpense()">저장</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 지출 상세 모달 -->
        <div class="modal fade" id="expenseDetailModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">지출 상세</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="expenseDetailContent">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                        <div class="btn-group" id="expenseDetailActions">
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 영수증 확대 모달 -->
        <div class="modal fade" id="receiptModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">영수증</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img id="receiptImage" class="img-fluid" src="" alt="영수증">
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            let currentPage = 1;
            let currentFilters = {{ status: 'all', category: 'all' }};
            let expenses = [];
            
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                setupEventListeners();
                loadExpenses();
                loadStats();
                
                // 오늘 날짜를 기본값으로 설정
                document.getElementById('expenseDate').valueAsDate = new Date();
            }});
            
            // 이벤트 리스너 설정
            function setupEventListeners() {{
                // 상태 필터 라디오 버튼
                document.querySelectorAll('input[name="statusFilter"]').forEach(radio => {{
                    radio.addEventListener('change', function() {{
                        currentFilters.status = this.value;
                        currentPage = 1;
                        loadExpenses();
                    }});
                }});
                
                // 분야 필터 버튼
                document.querySelectorAll('.category-filter').forEach(btn => {{
                    btn.addEventListener('click', function() {{
                        document.querySelectorAll('.category-filter').forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        
                        currentFilters.category = this.getAttribute('data-category');
                        currentPage = 1;
                        loadExpenses();
                    }});
                }});
                
                // 드래그 앤 드롭
                const dropZone = document.getElementById('dropZone');
                const fileInput = document.getElementById('receiptFile');
                
                dropZone.addEventListener('click', () => fileInput.click());
                
                dropZone.addEventListener('dragover', (e) => {{
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                }});
                
                dropZone.addEventListener('dragleave', (e) => {{
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                }});
                
                dropZone.addEventListener('drop', (e) => {{
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {{
                        handleFileSelect(files[0]);
                    }}
                }});
                
                fileInput.addEventListener('change', (e) => {{
                    if (e.target.files.length > 0) {{
                        handleFileSelect(e.target.files[0]);
                    }}
                }});
            }}
            
            // 파일 선택 처리
            function handleFileSelect(file) {{
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
                
                if (!allowedTypes.includes(file.type)) {{
                    alert('JPG, PNG, PDF 파일만 업로드 가능합니다.');
                    return;
                }}
                
                if (file.size > 10 * 1024 * 1024) {{ // 10MB
                    alert('파일 크기는 10MB 이하여야 합니다.');
                    return;
                }}
                
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('filePreview').style.display = 'block';
            }}
            
            // 파일 제거
            function removeFile() {{
                document.getElementById('receiptFile').value = '';
                document.getElementById('filePreview').style.display = 'none';
            }}
            
            // 통계 데이터 로드
            async function loadStats() {{
                try {{
                    const response = await fetch('/api/business/dashboard-stats');
                    if (response.ok) {{
                        const stats = await response.json();
                        
                        document.getElementById('totalExpenses').textContent = stats.total_expenses || 0;
                        document.getElementById('pendingExpenses').textContent = stats.pending_expenses || 0;
                        document.getElementById('approvedAmount').textContent = 
                            (stats.approved_amount || 0).toLocaleString() + '원';
                        document.getElementById('myExpenses').textContent = stats.my_expenses || 0;
                    }}
                }} catch (error) {{
                    console.error('통계 로드 오류:', error);
                }}
            }}
            
            // 지출 목록 로드
            async function loadExpenses() {{
                try {{
                    const params = new URLSearchParams({{
                        page: currentPage,
                        limit: 10
                    }});
                    
                    if (currentFilters.status !== 'all') {{
                        params.append('status', currentFilters.status);
                    }}
                    if (currentFilters.category !== 'all') {{
                        params.append('category', currentFilters.category);
                    }}
                    
                    const response = await fetch(`/api/business/expenses?${{params}}`);
                    if (response.ok) {{
                        const data = await response.json();
                        expenses = data.expenses || [];
                        renderExpenses(expenses);
                        renderPagination(data.total || 0, data.page || 1, data.limit || 10);
                    }} else {{
                        throw new Error('지출 목록을 불러올 수 없습니다');
                    }}
                }} catch (error) {{
                    console.error('지출 로드 오류:', error);
                    document.getElementById('expenseContainer').innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3 text-warning"></i>
                            <p>지출 목록을 불러올 수 없습니다.</p>
                            <button class="btn btn-primary" onclick="loadExpenses()">다시 시도</button>
                        </div>
                    `;
                }}
            }}
            
            // 지출 목록 렌더링
            function renderExpenses(expenseList) {{
                const container = document.getElementById('expenseContainer');
                
                if (expenseList.length === 0) {{
                    container.innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-receipt fa-2x mb-3 text-muted"></i>
                            <p>조건에 맞는 지출이 없습니다.</p>
                        </div>
                    `;
                    return;
                }}
                
                container.innerHTML = expenseList.map(expense => `
                    <div class="expense-item ${{expense.status}}" onclick="showExpenseDetail(${{expense.id}})">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${{expense.title}}</h6>
                                <small class="text-muted">${{expense.category}} | ${{formatDate(expense.expense_date)}}</small>
                            </div>
                            <div class="text-end">
                                <div class="amount">${{expense.amount.toLocaleString()}}원</div>
                                <span class="expense-status status-${{expense.status}}">${{getStatusText(expense.status)}}</span>
                            </div>
                        </div>
                        <p class="mb-2 text-muted small">${{expense.description || '설명 없음'}}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="small text-muted">
                                신청자: ${{expense.user_name}}
                            </div>
                            <div class="small text-muted">
                                ${{expense.receipt_url ? '<i class="fas fa-paperclip me-1"></i>영수증 첨부' : '영수증 없음'}}
                            </div>
                        </div>
                        ${{expense.approved_by_name ? `
                            <div class="mt-2 small text-muted">
                                승인자: ${{expense.approved_by_name}} (${{formatDate(expense.updated_at)}})
                            </div>
                        ` : ''}}
                    </div>
                `).join('');
            }}
            
            // 지출 등록 모달 표시
            function showExpenseModal() {{
                document.getElementById('expenseModalTitle').textContent = '지출 등록';
                document.getElementById('expenseForm').reset();
                document.getElementById('expenseId').value = '';
                document.getElementById('expenseDate').valueAsDate = new Date();
                document.getElementById('filePreview').style.display = 'none';
                new bootstrap.Modal(document.getElementById('expenseModal')).show();
            }}
            
            // 지출 저장
            async function saveExpense() {{
                const expenseId = document.getElementById('expenseId').value;
                const isEdit = !!expenseId;
                
                const formData = new FormData();
                formData.append('title', document.getElementById('expenseTitle').value);
                formData.append('amount', document.getElementById('expenseAmount').value);
                formData.append('category', document.getElementById('expenseCategory').value);
                formData.append('description', document.getElementById('expenseDescription').value);
                formData.append('expense_date', document.getElementById('expenseDate').value);
                
                const receiptFile = document.getElementById('receiptFile').files[0];
                if (receiptFile) {{
                    formData.append('receipt', receiptFile);
                }}
                
                try {{
                    const url = isEdit ? `/api/business/expenses/${{expenseId}}` : '/api/business/expenses';
                    const method = isEdit ? 'PUT' : 'POST';
                    
                    const response = await fetch(url, {{
                        method: method,
                        body: formData
                    }});
                    
                    if (response.ok) {{
                        bootstrap.Modal.getInstance(document.getElementById('expenseModal')).hide();
                        loadExpenses();
                        loadStats();
                        alert(isEdit ? '지출이 수정되었습니다.' : '지출이 등록되었습니다.');
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '알 수 없는 오류'));
                    }}
                }} catch (error) {{
                    console.error('지출 저장 오류:', error);
                    alert('지출 저장 중 오류가 발생했습니다.');
                }}
            }}
            
            // 지출 상세 보기
            async function showExpenseDetail(expenseId) {{
                try {{
                    const response = await fetch(`/api/business/expenses/${{expenseId}}`);
                    if (response.ok) {{
                        const expense = await response.json();
                        renderExpenseDetail(expense);
                        new bootstrap.Modal(document.getElementById('expenseDetailModal')).show();
                    }}
                }} catch (error) {{
                    console.error('지출 상세 로드 오류:', error);
                    alert('지출 상세 정보를 불러올 수 없습니다.');
                }}
            }}
            
            // 지출 상세 렌더링
            function renderExpenseDetail(expense) {{
                const content = document.getElementById('expenseDetailContent');
                content.innerHTML = `
                    <div class="row">
                        <div class="col-md-8">
                            <h4>${{expense.title}}</h4>
                            <p class="text-muted">${{expense.description || '설명 없음'}}</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="amount mb-2">${{expense.amount.toLocaleString()}}원</div>
                            <span class="expense-status status-${{expense.status}}">${{getStatusText(expense.status)}}</span>
                        </div>
                    </div>
                    <hr>
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>분야:</strong> ${{expense.category}}</p>
                            <p><strong>지출일:</strong> ${{formatDate(expense.expense_date)}}</p>
                            <p><strong>신청자:</strong> ${{expense.user_name}}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>등록일:</strong> ${{formatDate(expense.created_at)}}</p>
                            ${{expense.approved_by_name ? `<p><strong>승인자:</strong> ${{expense.approved_by_name}}</p>` : ''}}
                            ${{expense.approval_comment ? `<p><strong>승인 의견:</strong> ${{expense.approval_comment}}</p>` : ''}}
                        </div>
                    </div>
                    ${{expense.receipt_url ? `
                        <div class="mt-3">
                            <p><strong>첨부 파일:</strong></p>
                            <img src="${{expense.receipt_url}}" class="receipt-preview" onclick="showReceipt('${{expense.receipt_url}}')" alt="영수증">
                        </div>
                    ` : ''}}
                `;
                
                // 액션 버튼들
                const actions = document.getElementById('expenseDetailActions');
                let actionButtons = '';
                
                if (expense.status === 'pending' && {str(can_approve).lower()}) {{
                    actionButtons += `
                        <button class="btn btn-success" onclick="approveExpense(${{expense.id}})">승인</button>
                        <button class="btn btn-danger" onclick="rejectExpense(${{expense.id}})">반려</button>
                    `;
                }}
                
                if (expense.user_id === {user_id} && expense.status === 'pending') {{
                    actionButtons += `
                        <button class="btn btn-primary" onclick="editExpense(${{expense.id}})">수정</button>
                        <button class="btn btn-outline-danger" onclick="deleteExpense(${{expense.id}})">삭제</button>
                    `;
                }}
                
                actions.innerHTML = actionButtons;
            }}
            
            // 영수증 확대 보기
            function showReceipt(url) {{
                document.getElementById('receiptImage').src = url;
                new bootstrap.Modal(document.getElementById('receiptModal')).show();
            }}
            
            // 지출 승인
            async function approveExpense(expenseId) {{
                const comment = prompt('승인 의견을 입력해주세요 (선택사항):');
                
                try {{
                    const response = await fetch(`/api/business/expenses/${{expenseId}}/approve`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ comment: comment || null }})
                    }});
                    
                    if (response.ok) {{
                        bootstrap.Modal.getInstance(document.getElementById('expenseDetailModal')).hide();
                        loadExpenses();
                        loadStats();
                        alert('지출이 승인되었습니다.');
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '승인 실패'));
                    }}
                }} catch (error) {{
                    console.error('승인 오류:', error);
                    alert('승인 처리 중 오류가 발생했습니다.');
                }}
            }}
            
            // 지출 반려
            async function rejectExpense(expenseId) {{
                const comment = prompt('반려 사유를 입력해주세요:');
                if (!comment) {{
                    alert('반려 사유는 필수입니다.');
                    return;
                }}
                
                try {{
                    const response = await fetch(`/api/business/expenses/${{expenseId}}/reject`, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ comment: comment }})
                    }});
                    
                    if (response.ok) {{
                        bootstrap.Modal.getInstance(document.getElementById('expenseDetailModal')).hide();
                        loadExpenses();
                        loadStats();
                        alert('지출이 반려되었습니다.');
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '반려 실패'));
                    }}
                }} catch (error) {{
                    console.error('반려 오류:', error);
                    alert('반려 처리 중 오류가 발생했습니다.');
                }}
            }}
            
            // 내 지출만 필터링
            function filterMyExpenses() {{
                // 구현 필요
                alert('내 지출 필터링 기능은 개발 중입니다.');
            }}
            
            // 승인 대기 필터링
            function filterPendingApprovals() {{
                document.getElementById('pendingStatus').checked = true;
                currentFilters.status = 'pending';
                currentPage = 1;
                loadExpenses();
            }}
            
            // 지출 내보내기
            function exportExpenses() {{
                window.open('/api/business/expenses/export', '_blank');
            }}
            
            // 페이지네이션 렌더링
            function renderPagination(total, page, limit) {{
                const totalPages = Math.ceil(total / limit);
                const pagination = document.getElementById('expensePagination');
                
                if (totalPages <= 1) {{
                    pagination.innerHTML = '';
                    return;
                }}
                
                let html = '';
                
                if (page > 1) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page - 1}})">이전</a></li>`;
                }}
                
                for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {{
                    html += `<li class="page-item ${{i === page ? 'active' : ''}}">
                        <a class="page-link" href="#" onclick="changePage(${{i}})">${{i}}</a>
                    </li>`;
                }}
                
                if (page < totalPages) {{
                    html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${{page + 1}})">다음</a></li>`;
                }}
                
                pagination.innerHTML = html;
            }}
            
            // 페이지 변경
            function changePage(page) {{
                currentPage = page;
                loadExpenses();
            }}
            
            // 유틸리티 함수들
            function getStatusText(status) {{
                const statusMap = {{
                    'pending': '승인 대기',
                    'approved': '승인됨',
                    'rejected': '반려됨'
                }};
                return statusMap[status] || status;
            }}
            
            function formatDate(dateString) {{
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR');
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)