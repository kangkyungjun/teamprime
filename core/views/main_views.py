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
    
    username = current_user.get('username', '사용자')
    
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
        </style>
    </head>
    <body>
        <div class="container">
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
        </script>
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
        </style>
    </head>
    <body>
        <div class="container">
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
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)