"""
메인 뷰 라우터
- 루트 페이지
- API 키 입력 화면
- 프로필 페이지
- 거래 플로우 페이지
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)
main_views_router = APIRouter()

@main_views_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """자동거래 메인 대시보드 - 실시간 모니터링 (인증 체크 포함)"""
    # 새로운 인증 시스템 체크
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    # 인증된 사용자가 있으면 메인 대시보드, 없으면 로그인 페이지
    if current_user:
        # 인증된 사용자는 비즈니스 메인 대시보드로 리다이렉트
        return RedirectResponse(url="/main-dashboard")
    else:
        # 로그인 페이지로 리다이렉트
        return RedirectResponse(url="/login")

@main_views_router.get("/api-login", response_class=HTMLResponse)
async def authenticated_api_key_input_dashboard(request: Request, current_user: dict = None):
    """인증된 사용자용 - API 키 입력 화면 (보안 강화)"""
    
    if not current_user:
        from core.auth.middleware import get_current_user
        current_user = await get_current_user(request)
        if not current_user:
            return RedirectResponse(url="/login")
    
    user_id = current_user.get('id')
    username = current_user.get('username', '사용자')
    
    # 🔍 기존 세션 확인 - 이미 API 키로 로그인된 경우 바로 거래 대시보드로
    from core.session.session_manager import session_manager
    existing_session = session_manager.get_session(user_id)
    
    if existing_session and existing_session.login_status.get("logged_in", False):
        logger.info(f"✅ {username} 기존 세션 발견 - 거래 대시보드로 리다이렉트")
        return RedirectResponse(url="/dashboard")
    
    logger.info(f"🔑 {username} 새로운 API 키 입력 필요 - 로그인 폼 표시")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Teamprime - API 키 설정</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .container {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
            }}
            
            .logo {{
                text-align: center;
                margin-bottom: 30px;
            }}
            
            .logo h1 {{
                color: #333;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .welcome {{
                text-align: center;
                margin-bottom: 30px;
                color: #666;
                font-size: 16px;
            }}
            
            .form-group {{
                margin-bottom: 20px;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 600;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #667eea;
            }}
            
            .submit-btn {{
                width: 100%;
                padding: 15px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
                margin-top: 20px;
            }}
            
            .submit-btn:hover {{
                transform: translateY(-2px);
            }}
            
            .submit-btn:disabled {{
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }}
            
            .loading {{
                display: none;
                text-align: center;
                margin-top: 20px;
                color: #667eea;
            }}
            
            .spinner {{
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                display: inline-block;
                margin-right: 10px;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .message {{
                padding: 10px;
                border-radius: 8px;
                margin-top: 15px;
                text-align: center;
                display: none;
            }}
            
            .message.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .message.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            .nav-links {{
                text-align: center;
                margin-top: 30px;
            }}
            
            .nav-links a {{
                color: #667eea;
                text-decoration: none;
                margin: 0 15px;
                font-weight: 500;
            }}
            
            .nav-links a:hover {{
                text-decoration: underline;
            }}
            
            /* 플로팅 서브 버튼 */
            .floating-sub-buttons {{
                position: fixed;
                bottom: 100px; /* 탭바(80px) 위쪽 20px */
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-radius: 25px;
                padding: 15px 25px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                z-index: 999;
                animation: slideUp 0.3s ease-out;
            }}
            
            .sub-button {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 15px 20px;
                border-radius: 18px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 70px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .sub-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .sub-icon {{
                font-size: 20px;
                margin-bottom: 4px;
            }}
            
            .sub-label {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid #e0e0e0;
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px;
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: #333;
                text-align: center;
            }}
            
            /* 상단 앱바 */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 20px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
            }}
            
            .app-title {{
                font-size: 20px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .user-info {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .user-name {{
                font-weight: 600;
                color: #333;
            }}
            
            .user-role {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
            
            .menu-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .menu-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            .user-menu {{
                position: relative;
                display: inline-block;
            }}
            
            .dropdown-menu {{
                display: none;
                position: absolute;
                right: 0;
                top: 100%;
                background: white;
                min-width: 160px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border-radius: 12px;
                padding: 8px 0;
                z-index: 1000;
                margin-top: 8px;
            }}
            
            .dropdown-menu.show {{
                display: block;
            }}
            
            .dropdown-item {{
                display: block;
                width: 100%;
                padding: 12px 20px;
                text-decoration: none;
                color: #333;
                border: none;
                background: none;
                text-align: left;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            
            .dropdown-item:hover {{
                background-color: #f8f9fa;
            }}
            
            .dropdown-divider {{
                height: 1px;
                background-color: #e9ecef;
                margin: 8px 0;
            }}
        </style>
    </head>
    <body>
        <!-- 상단 앱바 -->
        <div class="app-bar">
            <a href="/main-dashboard" class="app-title">🚀 Teamprime</a>
            <div class="user-info">
                <span class="user-name">👤 {username}</span>
                <div class="user-menu">
                    <button class="menu-btn" onclick="toggleMenu()">☰</button>
                    <div class="dropdown-menu" id="userDropdown">
                        <a href="/profile" class="dropdown-item">👤 프로필</a>
                        <a href="/settings" class="dropdown-item">⚙️ 설정</a>
                        <div class="dropdown-divider"></div>
                        <button class="dropdown-item" onclick="logout()">🚪 로그아웃</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="container" style="margin-top: 80px;">
            <div class="logo">
                <h1>🚀 Teamprime</h1>
                <p>업비트 자동거래 시스템</p>
            </div>
            
            <div class="welcome">
                <strong>{username}</strong>님, 안전한 거래를 위해<br>
                업비트 API 키를 입력해주세요.
            </div>
            
            <form id="apiKeyForm">
                <div class="form-group">
                    <label for="accessKey">Access Key</label>
                    <input type="password" id="accessKey" name="accessKey" required placeholder="업비트 Access Key">
                </div>
                
                <div class="form-group">
                    <label for="secretKey">Secret Key</label>
                    <input type="password" id="secretKey" name="secretKey" required placeholder="업비트 Secret Key">
                </div>
                
                <button type="submit" class="submit-btn" id="submitBtn">
                    🔐 API 키 검증 및 시작
                </button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                API 키를 검증하는 중...
            </div>
            
            <div class="message" id="message"></div>
            
            <div class="nav-links">
                <a href="/main-dashboard">🏠 대시보드</a>
                <a href="/profile">👤 프로필</a>
                <a href="/logout">🚪 로그아웃</a>
            </div>
        </div>
        
        <script>
            document.getElementById('apiKeyForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const submitBtn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');
                const message = document.getElementById('message');
                const accessKey = document.getElementById('accessKey').value;
                const secretKey = document.getElementById('secretKey').value;
                
                // UI 상태 변경
                submitBtn.disabled = true;
                loading.style.display = 'block';
                message.style.display = 'none';
                
                try {{
                    const response = await fetch('/api/auth-login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            access_key: accessKey,
                            secret_key: secretKey
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        message.className = 'message success';
                        message.textContent = '✅ API 키 검증 완료! 거래 대시보드로 이동합니다...';
                        message.style.display = 'block';
                        
                        // 2초 후 대시보드로 이동
                        setTimeout(() => {{
                            window.location.href = '/dashboard';
                        }}, 2000);
                    }} else {{
                        message.className = 'message error';
                        message.textContent = '❌ ' + result.message;
                        message.style.display = 'block';
                        
                        submitBtn.disabled = false;
                    }}
                }} catch (error) {{
                    message.className = 'message error';
                    message.textContent = '❌ 네트워크 오류가 발생했습니다.';
                    message.style.display = 'block';
                    
                    submitBtn.disabled = false;
                }} finally {{
                    loading.style.display = 'none';
                }}
            }});
            
            // === 탭바 관련 JavaScript 함수들 ===
            let currentTab = null;

            function selectTab(tabType) {{
                if (currentTab === tabType) {{
                    hideSubButtons();
                    return;
                }}
                
                currentTab = tabType;
                
                if (tabType === 'task') {{
                    showSubButtons('📋', '업무 목록', '➕', '업무 등록', 
                                  'navigateToTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showExpenseModal()');
                    updateTabState('profit');
                }}
            }}
            
            function showSubButtons(icon1, label1, icon2, label2, action1, action2) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const button1 = document.getElementById('subButton1');
                const button2 = document.getElementById('subButton2');
                const icon1El = document.getElementById('subIcon1');
                const label1El = document.getElementById('subLabel1');
                const icon2El = document.getElementById('subIcon2');
                const label2El = document.getElementById('subLabel2');
                
                icon1El.textContent = icon1;
                label1El.textContent = label1;
                icon2El.textContent = icon2;
                label2El.textContent = label2;
                
                button1.onclick = () => eval(action1);
                button2.onclick = () => eval(action2);
                
                subButtons.style.display = 'flex';
            }}
            
            function hideSubButtons() {{
                document.getElementById('floatingSubButtons').style.display = 'none';
                currentTab = null;
                updateTabState(null);
            }}
            
            function updateTabState(activeTab) {{
                document.getElementById('taskTab').classList.remove('active');
                document.getElementById('profitTab').classList.remove('active');
                
                if (activeTab === 'task') {{
                    document.getElementById('taskTab').classList.add('active');
                }} else if (activeTab === 'profit') {{
                    document.getElementById('profitTab').classList.add('active');
                }}
            }}
            
            function navigateToHome() {{
                window.location.href = '/main-dashboard';
            }}
            
            function navigateToTaskList() {{
                window.location.href = '/task-list';
            }}
            
            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}
            
            function showQuickTaskModal() {{
                alert('빠른 업무 등록 기능은 메인 대시보드에서 이용하실 수 있습니다.');
            }}
            
            function showExpenseModal() {{
                alert('손익 등록 기능은 손익 페이지에서 이용하실 수 있습니다.');
            }}
            
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                dropdown.classList.toggle('show');
            }}
            
            function logout() {{
                if (confirm('로그아웃 하시겠습니까?')) {{
                    window.location.href = '/logout';
                }}
            }}
            
            // 메뉴 외부 클릭 시 닫기
            document.addEventListener('click', function(event) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const bottomNav = document.querySelector('.bottom-nav');
                
                if (currentTab && subButtons.style.display === 'flex') {{
                    if (!subButtons.contains(event.target) && !bottomNav.contains(event.target)) {{
                        hideSubButtons();
                    }}
                }}
                
                if (!event.target.matches('.menu-btn')) {{
                    const dropdown = document.getElementById('userDropdown');
                    if (dropdown.classList.contains('show')) {{
                        dropdown.classList.remove('show');
                    }}
                }}
            }});
        </script>
        
        <!-- 플로팅 서브 버튼 (탭바 위쪽) -->
        <div class="floating-sub-buttons" id="floatingSubButtons" style="display: none;">
            <div class="sub-button" id="subButton1">
                <div class="sub-icon" id="subIcon1">📋</div>
                <div class="sub-label" id="subLabel1">목록</div>
            </div>
            <div class="sub-button" id="subButton2">
                <div class="sub-icon" id="subIcon2">➕</div>
                <div class="sub-label" id="subLabel2">등록</div>
            </div>
        </div>

        <!-- 하단 탭바 네비게이션 (3개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item" id="homeTab" onclick="navigateToHome()">
                <div class="nav-icon">🏠</div>
                <div class="nav-label">홈</div>
            </div>
            <div class="nav-item" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
        </div>
        
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@main_views_router.get("/trading-flow")
async def trading_flow(request: Request):
    """거래 플로우 페이지 (간소화)"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 간단한 리다이렉트로 대체
    return RedirectResponse(url="/dashboard")

@main_views_router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """프로필 페이지"""
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    email = current_user.get('email', '')
    user_role = current_user.get('role', 'user')
    user_id = current_user.get('id')
    
    # DB의 실제 role 값 사용 (이미 owner로 업데이트됨)
    display_role = user_role.upper()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>프로필 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            
            .profile-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            
            .info-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }}
            
            .nav-buttons {{
                display: flex;
                gap: 10px;
                justify-content: center;
                margin-top: 30px;
            }}
            
            .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .btn-secondary {{
                background: #6c757d;
                color: white;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            .password-change-section {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            
            .password-change-section h3 {{
                color: #333;
                margin-bottom: 20px;
                text-align: center;
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 5px;
                color: #333;
                font-weight: 600;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #667eea;
            }}
            
            .message {{
                padding: 10px;
                border-radius: 8px;
                margin-top: 15px;
                text-align: center;
                display: none;
            }}
            
            .message.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            
            .message.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            
            /* 모달 스타일 */
            .modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }}
            
            .modal-content {{
                background-color: #fefefe;
                margin: 10% auto;
                padding: 0;
                border-radius: 15px;
                width: 90%;
                max-width: 500px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
                animation: modalShow 0.3s ease-out;
            }}
            
            @keyframes modalShow {{
                from {{opacity: 0; transform: translateY(-50px);}}
                to {{opacity: 1; transform: translateY(0);}}
            }}
            
            .modal-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 30px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border-radius: 15px 15px 0 0;
            }}
            
            .modal-header h3 {{
                margin: 0;
                font-size: 20px;
            }}
            
            .close {{
                color: white;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                line-height: 1;
            }}
            
            .close:hover {{
                opacity: 0.7;
            }}
            
            .modal-body {{
                padding: 30px;
            }}
            
            .form-actions {{
                display: flex;
                gap: 10px;
                justify-content: flex-end;
                margin-top: 20px;
            }}
            
            .form-actions .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
            }}
            
            .form-actions .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .form-actions .btn-secondary {{
                background: #6c757d;
                color: white;
            }}
            
            .form-actions .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            /* 플로팅 서브 버튼 */
            .floating-sub-buttons {{
                position: fixed;
                bottom: 100px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 25px;
                padding: 15px 25px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                z-index: 999;
                animation: slideUp 0.3s ease-out;
            }}
            
            .sub-button {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 15px 20px;
                border-radius: 18px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 70px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .sub-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .sub-icon {{
                font-size: 20px;
                margin-bottom: 4px;
            }}
            
            .sub-label {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-top: 1px solid #e0e0e0;
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px;
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: #333;
                text-align: center;
            }}
            
            /* 상단 앱바 */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 20px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 1000;
            }}
            
            .app-title {{
                font-size: 20px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .user-info {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .user-name {{
                font-weight: 600;
                color: #333;
            }}
            
            .user-role {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
            
            .menu-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .menu-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            .user-menu {{
                position: relative;
                display: inline-block;
            }}
            
            .dropdown-menu {{
                display: none;
                position: absolute;
                right: 0;
                top: 100%;
                background: white;
                min-width: 160px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border-radius: 12px;
                padding: 8px 0;
                z-index: 1000;
                margin-top: 8px;
            }}
            
            .dropdown-menu.show {{
                display: block;
            }}
            
            .dropdown-item {{
                display: block;
                width: 100%;
                padding: 12px 20px;
                text-decoration: none;
                color: #333;
                border: none;
                background: none;
                text-align: left;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            
            .dropdown-item:hover {{
                background-color: #f8f9fa;
            }}
            
            .dropdown-divider {{
                height: 1px;
                background-color: #e9ecef;
                margin: 8px 0;
            }}
        </style>
    </head>
    <body>
        <!-- 상단 앱바 -->
        <div class="app-bar">
            <a href="/main-dashboard" class="app-title">🚀 Teamprime</a>
            <div class="user-info">
                <span class="user-name">👤 {username}</span>
                <span class="user-role">{display_role}</span>
                <div class="user-menu">
                    <button class="menu-btn" onclick="toggleMenu()">☰</button>
                    <div class="dropdown-menu" id="userDropdown">
                        <a href="/profile" class="dropdown-item">👤 프로필</a>
                        <a href="/settings" class="dropdown-item">⚙️ 설정</a>
                        <div class="dropdown-divider"></div>
                        <button class="dropdown-item" onclick="logout()">🚪 로그아웃</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="container" style="margin-top: 80px; margin-bottom: 100px;">
            <div class="header">
                <h1>👤 사용자 프로필</h1>
            </div>
            
            <div class="profile-info">
                <div class="info-row">
                    <strong>사용자명:</strong>
                    <span>{username}</span>
                </div>
                <div class="info-row">
                    <strong>이메일:</strong>
                    <span>{email}</span>
                </div>
                <div class="info-row">
                    <strong>권한 등급:</strong>
                    <span style="text-transform: uppercase; font-weight: bold; color: #667eea;">{display_role}</span>
                </div>
            </div>
            
            <div class="password-change-section">
                <h3>계정 보안</h3>
                <button class="btn btn-primary" onclick="openPasswordModal()">🔒 비밀번호 변경</button>
            </div>
            
            <div class="nav-buttons">
                <a href="/main-dashboard" class="btn btn-primary">🏠 대시보드</a>
                <a href="/logout" class="btn btn-secondary">🚪 로그아웃</a>
            </div>
        </div>
        
        <!-- 비밀번호 변경 모달 -->
        <div class="modal" id="passwordModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>🔒 비밀번호 변경</h3>
                    <span class="close" onclick="closePasswordModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <form id="passwordChangeForm">
                        <div class="form-group">
                            <label for="currentPassword">현재 비밀번호:</label>
                            <input type="password" id="currentPassword" name="currentPassword" required>
                        </div>
                        <div class="form-group">
                            <label for="newPassword">새 비밀번호:</label>
                            <input type="password" id="newPassword" name="newPassword" required>
                        </div>
                        <div class="form-group">
                            <label for="confirmPassword">새 비밀번호 확인:</label>
                            <input type="password" id="confirmPassword" name="confirmPassword" required>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn btn-primary">변경하기</button>
                            <button type="button" class="btn btn-secondary" onclick="closePasswordModal()">취소</button>
                        </div>
                    </form>
                    <div class="message" id="passwordMessage"></div>
                </div>
            </div>
        </div>
        
        <script>
            // 모달 관리 함수들
            function openPasswordModal() {{
                document.getElementById('passwordModal').style.display = 'block';
                // 폼 초기화
                document.getElementById('passwordChangeForm').reset();
                // 메시지 숨기기
                const message = document.getElementById('passwordMessage');
                message.style.display = 'none';
            }}
            
            function closePasswordModal() {{
                document.getElementById('passwordModal').style.display = 'none';
            }}
            
            // 모달 외부 클릭시 닫기
            window.onclick = function(event) {{
                const modal = document.getElementById('passwordModal');
                if (event.target == modal) {{
                    closePasswordModal();
                }}
            }}
            
            document.getElementById('passwordChangeForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const currentPassword = document.getElementById('currentPassword').value;
                const newPassword = document.getElementById('newPassword').value;
                const confirmPassword = document.getElementById('confirmPassword').value;
                const message = document.getElementById('passwordMessage');
                
                // 비밀번호 확인 검증
                if (newPassword !== confirmPassword) {{
                    message.className = 'message error';
                    message.textContent = '새 비밀번호가 일치하지 않습니다.';
                    message.style.display = 'block';
                    return;
                }}
                
                // 비밀번호 길이 검증
                if (newPassword.length < 6) {{
                    message.className = 'message error';
                    message.textContent = '새 비밀번호는 최소 6자 이상이어야 합니다.';
                    message.style.display = 'block';
                    return;
                }}
                
                try {{
                    const response = await fetch('/api/change-password', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            current_password: currentPassword,
                            new_password: newPassword
                        }})
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        message.className = 'message success';
                        message.textContent = '✅ 비밀번호가 성공적으로 변경되었습니다.';
                        message.style.display = 'block';
                        
                        // 2초 후 모달 닫기
                        setTimeout(() => {{
                            closePasswordModal();
                        }}, 2000);
                    }} else {{
                        message.className = 'message error';
                        message.textContent = '❌ ' + result.message;
                        message.style.display = 'block';
                    }}
                }} catch (error) {{
                    message.className = 'message error';
                    message.textContent = '❌ 네트워크 오류가 발생했습니다.';
                    message.style.display = 'block';
                }}
            }});
            
            // === 탭바 관련 JavaScript 함수들 ===
            let currentTab = null;

            function selectTab(tabType) {{
                if (currentTab === tabType) {{
                    hideSubButtons();
                    return;
                }}
                
                currentTab = tabType;
                
                if (tabType === 'task') {{
                    showSubButtons('📋', '업무 목록', '➕', '업무 등록', 
                                  'navigateToTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showExpenseModal()');
                    updateTabState('profit');
                }}
            }}
            
            function showSubButtons(icon1, label1, icon2, label2, action1, action2) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const button1 = document.getElementById('subButton1');
                const button2 = document.getElementById('subButton2');
                const icon1El = document.getElementById('subIcon1');
                const label1El = document.getElementById('subLabel1');
                const icon2El = document.getElementById('subIcon2');
                const label2El = document.getElementById('subLabel2');
                
                icon1El.textContent = icon1;
                label1El.textContent = label1;
                icon2El.textContent = icon2;
                label2El.textContent = label2;
                
                button1.onclick = () => eval(action1);
                button2.onclick = () => eval(action2);
                
                subButtons.style.display = 'flex';
            }}
            
            function hideSubButtons() {{
                document.getElementById('floatingSubButtons').style.display = 'none';
                currentTab = null;
                updateTabState(null);
            }}
            
            function updateTabState(activeTab) {{
                document.getElementById('taskTab').classList.remove('active');
                document.getElementById('profitTab').classList.remove('active');
                
                if (activeTab === 'task') {{
                    document.getElementById('taskTab').classList.add('active');
                }} else if (activeTab === 'profit') {{
                    document.getElementById('profitTab').classList.add('active');
                }}
            }}
            
            function navigateToHome() {{
                window.location.href = '/main-dashboard';
            }}
            
            function navigateToTaskList() {{
                window.location.href = '/task-list';
            }}
            
            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}
            
            function showQuickTaskModal() {{
                alert('빠른 업무 등록 기능은 메인 대시보드에서 이용하실 수 있습니다.');
            }}
            
            function showExpenseModal() {{
                alert('손익 등록 기능은 손익 페이지에서 이용하실 수 있습니다.');
            }}
            
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                dropdown.classList.toggle('show');
            }}
            
            function logout() {{
                if (confirm('로그아웃 하시겠습니까?')) {{
                    window.location.href = '/logout';
                }}
            }}
            
            // 메뉴 외부 클릭 시 닫기
            document.addEventListener('click', function(event) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const bottomNav = document.querySelector('.bottom-nav');
                
                if (currentTab && subButtons.style.display === 'flex') {{
                    if (!subButtons.contains(event.target) && !bottomNav.contains(event.target)) {{
                        hideSubButtons();
                    }}
                }}
                
                if (!event.target.matches('.menu-btn')) {{
                    const dropdown = document.getElementById('userDropdown');
                    if (dropdown.classList.contains('show')) {{
                        dropdown.classList.remove('show');
                    }}
                }}
            }});
        </script>
        
        <!-- 플로팅 서브 버튼 (탭바 위쪽) -->
        <div class="floating-sub-buttons" id="floatingSubButtons" style="display: none;">
            <div class="sub-button" id="subButton1">
                <div class="sub-icon" id="subIcon1">📋</div>
                <div class="sub-label" id="subLabel1">목록</div>
            </div>
            <div class="sub-button" id="subButton2">
                <div class="sub-icon" id="subIcon2">➕</div>
                <div class="sub-label" id="subLabel2">등록</div>
            </div>
        </div>

        <!-- 하단 탭바 네비게이션 (3개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item" id="homeTab" onclick="navigateToHome()">
                <div class="nav-icon">🏠</div>
                <div class="nav-label">홈</div>
            </div>
            <div class="nav-item" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
        </div>
        
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)