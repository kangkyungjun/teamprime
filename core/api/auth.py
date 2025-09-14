"""인증 관련 API 라우터"""

import logging
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from typing import Dict, Any
from pydantic import BaseModel, EmailStr

from ..auth.auth_service import AuthService
from ..auth.middleware import get_current_user, require_auth
from ..session.session_manager import session_manager
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# 요청 모델 정의 - 간소화 (API 키 저장 제거)
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    remember_me: bool = False

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

# API 키 업데이트 모델 제거됨 - API 키 저장하지 않음

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/main-dashboard"):
    """로그인 페이지"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>로그인 - 업비트 자동거래 시스템</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .login-container {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }}
            .login-header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .login-header h1 {{
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            .login-header p {{
                color: #666;
                margin: 0;
                font-size: 16px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            .form-group label {{
                display: block;
                margin-bottom: 5px;
                color: #333;
                font-weight: 600;
            }}
            .form-control {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }}
            .form-control:focus {{
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }}
            .checkbox-group {{
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }}
            .checkbox-group input {{
                margin-right: 8px;
            }}
            .btn-primary {{
                width: 100%;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }}
            .btn-primary:hover {{
                transform: translateY(-2px);
            }}
            .btn-primary:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}
            .register-link {{
                text-align: center;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e9ecef;
            }}
            .register-link a {{
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }}
            .register-link a:hover {{
                text-decoration: underline;
            }}
            .alert {{
                padding: 12px 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }}
            .alert-error {{
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
            .alert-success {{
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <h1>로그인</h1>
            </div>
            
            <div id="alert" class="alert alert-error"></div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">사용자명 또는 이메일</label>
                    <input type="text" id="username" name="username_or_email" class="form-control" required>
                </div>
                
                <div class="form-group">
                    <label for="password">비밀번호</label>
                    <input type="password" id="password" name="password" class="form-control" required>
                </div>
                
                <div class="checkbox-group">
                    <input type="checkbox" id="rememberMe" name="remember_me">
                    <label for="rememberMe">로그인 유지</label>
                </div>
                
                <button type="submit" class="btn-primary" id="loginBtn">
                    로그인
                </button>
            </form>
            
            <div class="register-link">
                <p>계정이 없으신가요? <a href="/register">회원가입</a></p>
            </div>
        </div>
        
        <script>
            const form = document.getElementById('loginForm');
            const alert = document.getElementById('alert');
            const loginBtn = document.getElementById('loginBtn');
            
            function showAlert(message, type = 'error') {{
                alert.textContent = message;
                alert.className = `alert alert-${{type}}`;
                alert.style.display = 'block';
            }}
            
            function hideAlert() {{
                alert.style.display = 'none';
            }}
            
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                hideAlert();
                
                const formData = new FormData(form);
                const data = {{
                    username_or_email: formData.get('username_or_email'),
                    password: formData.get('password'),
                    remember_me: formData.has('remember_me')
                }};
                
                loginBtn.textContent = '로그인 중...';
                loginBtn.disabled = true;
                
                try {{
                    const response = await fetch('/api/auth/login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(data)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        // remember_me에 따른 쿠키 만료 시간 설정
                        const maxAge = result.remember_me ? (7 * 24 * 60 * 60) : (24 * 60 * 60); // 7일 or 24시간
                        const cookieOptions = `path=/; max-age=${{maxAge}}; SameSite=Lax` + (location.protocol === 'https:' ? '; Secure' : '');
                        
                        // JWT 토큰을 쿠키에 저장 (보안 옵션 추가)
                        document.cookie = `auth_token=${{result.token}}; ${{cookieOptions}}`;
                        
                        const keepMessage = result.remember_me ? '7일간 로그인 상태가 유지됩니다.' : '24시간 로그인 상태가 유지됩니다.';
                        showAlert(`로그인 성공! ${{keepMessage}} 잠시 후 이동합니다...`, 'success');
                        
                        // 2초 후 리다이렉트
                        setTimeout(() => {{
                            window.location.href = '{next}';
                        }}, 2000);
                    }} else {{
                        showAlert(result.message);
                    }}
                }} catch (error) {{
                    showAlert('로그인 중 오류가 발생했습니다: ' + error.message);
                }} finally {{
                    loginBtn.textContent = '로그인';
                    loginBtn.disabled = false;
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html_content

@router.get("/register", response_class=HTMLResponse)
async def register_page():
    """회원가입 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>회원가입 - 업비트 자동거래 시스템</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .register-container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 500px;
            }
            .register-header {
                text-align: center;
                margin-bottom: 30px;
            }
            .register-header h1 {
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
            }
            .register-header p {
                color: #666;
                margin: 0;
                font-size: 16px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #333;
                font-weight: 600;
            }
            .form-control {
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            .form-control:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .form-help {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            .btn-primary {
                width: 100%;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 15px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
            }
            .btn-primary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .login-link {
                text-align: center;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e9ecef;
            }
            .login-link a {
                color: #667eea;
                text-decoration: none;
                font-weight: 600;
            }
            .login-link a:hover {
                text-decoration: underline;
            }
            .alert {
                padding: 12px 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: none;
            }
            .alert-error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .alert-success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .password-strength {
                margin-top: 5px;
                font-size: 12px;
            }
            .password-weak { color: #dc3545; }
            .password-medium { color: #ffc107; }
            .password-strong { color: #28a745; }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="register-header">
                <h1>회원가입</h1>
            </div>
            
            <div id="alert" class="alert alert-error"></div>
            
            <form id="registerForm">
                <div class="form-group">
                    <label for="username">사용자명</label>
                    <input type="text" id="username" name="username" class="form-control" required>
                    <div class="form-help">영문, 숫자, 언더스코어 사용 가능 (3-20자)</div>
                </div>
                
                <div class="form-group">
                    <label for="email">이메일</label>
                    <input type="email" id="email" name="email" class="form-control" required>
                </div>
                
                <div class="form-group">
                    <label for="password">비밀번호</label>
                    <input type="password" id="password" name="password" class="form-control" required>
                    <div id="passwordStrength" class="password-strength"></div>
                    <div class="form-help">대문자, 소문자, 숫자, 특수문자 포함 8자 이상</div>
                </div>
                
                <div class="form-group">
                    <label for="confirmPassword">비밀번호 확인</label>
                    <input type="password" id="confirmPassword" name="confirm_password" class="form-control" required>
                </div>
                
                <div class="form-help" style="background: #e8f4fd; padding: 15px; border-radius: 8px; color: #1976d2; margin: 20px 0;">
                    <strong>🔒 보안 강화:</strong> API 키는 저장되지 않습니다. 로그인 후 매번 새로운 API 키를 입력하여 더욱 안전하게 거래하세요!
                </div>
                
                <button type="submit" class="btn-primary" id="registerBtn">
                    회원가입
                </button>
            </form>
            
            <div class="login-link">
                <p>이미 계정이 있으신가요? <a href="/login">로그인</a></p>
            </div>
        </div>
        
        <script>
            const form = document.getElementById('registerForm');
            const alert = document.getElementById('alert');
            const registerBtn = document.getElementById('registerBtn');
            const passwordInput = document.getElementById('password');
            const confirmPasswordInput = document.getElementById('confirmPassword');
            const passwordStrengthDiv = document.getElementById('passwordStrength');
            
            function showAlert(message, type = 'error') {
                alert.textContent = message;
                alert.className = `alert alert-${type}`;
                alert.style.display = 'block';
            }
            
            function hideAlert() {
                alert.style.display = 'none';
            }
            
            function checkPasswordStrength(password) {
                let strength = 0;
                let message = '';
                
                if (password.length >= 8) strength++;
                if (/[a-z]/.test(password)) strength++;
                if (/[A-Z]/.test(password)) strength++;
                if (/[0-9]/.test(password)) strength++;
                if (/[^a-zA-Z0-9]/.test(password)) strength++;
                
                if (strength <= 2) {
                    message = '약한 비밀번호';
                    passwordStrengthDiv.className = 'password-strength password-weak';
                } else if (strength <= 4) {
                    message = '보통 비밀번호';
                    passwordStrengthDiv.className = 'password-strength password-medium';
                } else {
                    message = '강한 비밀번호';
                    passwordStrengthDiv.className = 'password-strength password-strong';
                }
                
                passwordStrengthDiv.textContent = message;
            }
            
            passwordInput.addEventListener('input', (e) => {
                checkPasswordStrength(e.target.value);
            });
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                hideAlert();
                
                const formData = new FormData(form);
                const password = formData.get('password');
                const confirmPassword = formData.get('confirm_password');
                
                // 비밀번호 확인
                if (password !== confirmPassword) {
                    showAlert('비밀번호가 일치하지 않습니다');
                    return;
                }
                
                const data = {
                    username: formData.get('username'),
                    email: formData.get('email'),
                    password: password,
                    confirm_password: confirmPassword
                };
                
                registerBtn.textContent = '회원가입 중...';
                registerBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/auth/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showAlert('회원가입이 완료되었습니다! 로그인 페이지로 이동합니다...', 'success');
                        
                        // 3초 후 로그인 페이지로 이동
                        setTimeout(() => {
                            window.location.href = '/login';
                        }, 3000);
                    } else {
                        showAlert(result.message);
                    }
                } catch (error) {
                    showAlert('회원가입 중 오류가 발생했습니다: ' + error.message);
                } finally {
                    registerBtn.textContent = '회원가입';
                    registerBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

@router.post("/api/auth/register")
async def register_user(request: RegisterRequest):
    """사용자 등록 API - 간소화 (API 키 저장 제거)"""
    try:
        # 비밀번호 확인
        if request.password != request.confirm_password:
            return {"success": False, "message": "비밀번호가 일치하지 않습니다"}
        
        # 사용자 등록 (API 키 없이)
        success, message, user_data = await AuthService.register_user(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        if success:
            return {"success": True, "message": message, "user": user_data}
        else:
            return {"success": False, "message": message}
            
    except Exception as e:
        logger.error(f"회원가입 API 오류: {str(e)}")
        return {"success": False, "message": "회원가입 중 오류가 발생했습니다"}

@router.post("/api/auth/login")
async def login_user(request: LoginRequest):
    """사용자 로그인 API"""
    try:
        # 사용자 인증
        success, message, user_data = await AuthService.authenticate_user(
            username_or_email=request.username_or_email,
            password=request.password
        )
        
        if not success or not user_data:
            return {"success": False, "message": message}
        
        # 세션 생성 (remember_me 옵션 전달)
        session_success, session_message, token = await AuthService.create_session(
            user_data['id'], 
            remember_me=request.remember_me
        )
        
        if session_success and token:
            return {
                "success": True, 
                "message": "로그인 성공",
                "token": token,
                "user": user_data,
                "remember_me": request.remember_me  # 프론트엔드에서 쿠키 설정에 사용
            }
        else:
            return {"success": False, "message": session_message}
            
    except Exception as e:
        logger.error(f"로그인 API 오류: {str(e)}")
        return {"success": False, "message": "로그인 중 오류가 발생했습니다"}

@router.post("/api/auth/logout")
async def logout_user(current_user: Dict[str, Any] = Depends(require_auth)):
    """사용자 로그아웃 API - 세션 데이터 삭제 포함"""
    try:
        # 사용자별 세션 데이터 삭제 및 기존 시스템 정리
        user_id = current_user.get('id')
        username = current_user.get('username')
        if user_id:
            # 새로운 세션 관리자를 통한 세션 정리
            try:
                from core.session import session_manager
                session_manager.remove_session(user_id)
                logger.info(f"✅ 사용자 {username} 세션 관리자에서 정리 완료")
            except Exception as session_error:
                logger.error(f"⚠️ 세션 관리자 정리 실패: {str(session_error)}")
            
            # 레거시 호환성을 위한 기존 방식도 유지 (임시)
            import main
            if hasattr(main, 'user_sessions') and user_id in main.user_sessions:
                del main.user_sessions[user_id]
                logger.info(f"✅ 사용자 {username} 레거시 세션 데이터 삭제 완료")
            
            # 🔗 기존 거래 시스템 상태 초기화
            try:
                from core.services.trading_engine import trading_state
                from core.api.system import upbit_api_keys, login_status
                import core.api.system as system_module
                
                # 거래 상태 초기화
                trading_state.available_budget = 0.0
                
                # API 키 정보 초기화
                upbit_api_keys["access_key"] = ""
                upbit_api_keys["secret_key"] = ""
                system_module.upbit_client = None
                
                # 로그인 상태 초기화
                login_status["logged_in"] = False
                login_status["account_info"] = None
                login_status["login_time"] = None
                
                logger.info(f"🔗 기존 거래 시스템 상태 초기화 완료")
                
            except Exception as cleanup_error:
                logger.warning(f"⚠️ 기존 시스템 정리 실패: {str(cleanup_error)}")
        
        return {"success": True, "message": "로그아웃 및 세션 삭제 완료"}
        
    except Exception as e:
        logger.error(f"로그아웃 API 오류: {str(e)}")
        # 에러가 발생해도 로그아웃은 성공으로 처리 (보안상)
        return {"success": True, "message": "로그아웃 완료"}

@router.post("/api/auth/refresh-token")
async def refresh_token(request: Request):
    """토큰 갱신 API - 자동 토큰 갱신용"""
    try:
        # Authorization 헤더에서 토큰 추출
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return {"success": False, "message": "유효하지 않은 인증 헤더입니다"}
        
        current_token = authorization[7:]  # "Bearer " 제거
        
        # 토큰 갱신
        success, message, new_token, remember_me = await AuthService.refresh_token(current_token)
        
        if success and new_token:
            return {
                "success": True,
                "message": message,
                "token": new_token,
                "remember_me": remember_me
            }
        else:
            return {"success": False, "message": message}
            
    except Exception as e:
        logger.error(f"토큰 갱신 API 오류: {str(e)}")
        return {"success": False, "message": "토큰 갱신 중 오류가 발생했습니다"}

@router.get("/api/auth/server-status")
async def get_server_status():
    """서버 상태 조회 API - 서버 재시작 감지용"""
    from config import SERVER_START_TIME
    from datetime import datetime
    
    return {
        "success": True,
        "server_start_time": SERVER_START_TIME,
        "current_time": datetime.utcnow().timestamp(),
        "uptime_seconds": datetime.utcnow().timestamp() - SERVER_START_TIME
    }

@router.get("/api/auth/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(require_auth)):
    """현재 사용자 정보 조회 API"""
    return {"success": True, "user": current_user}

# API 키 업데이트 엔드포인트 제거됨 - API 키 저장하지 않음

@router.post("/api/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """비밀번호 변경 API"""
    try:
        # AuthService를 통해 비밀번호 변경 처리
        success, message = await AuthService.change_password(
            user_id=current_user["id"],
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        if success:
            logger.info(f"비밀번호 변경 성공: user_id={current_user['id']}, username={current_user.get('username')}")
            return {"success": True, "message": "비밀번호가 성공적으로 변경되었습니다"}
        else:
            return {"success": False, "message": message}
            
    except Exception as e:
        logger.error(f"비밀번호 변경 API 오류: {str(e)}")
        return {"success": False, "message": "비밀번호 변경 중 오류가 발생했습니다"}

# 메모리 기반 세션 저장소 (API 키 임시 저장용)
user_sessions = {}

async def api_key_authentication_endpoint(request: Request):
    """API 키 인증 엔드포인트 - 세션 기반 (저장하지 않음) [메인 엔드포인트]"""
    logger.info("🔑 [AUTH] API 키 인증 요청 수신 - 보안 강화 방식")

    # 사용자 인증 확인
    current_user = await get_current_user(request)
    if not current_user:
        logger.warning("⚠️ [AUTH] 인증되지 않은 사용자의 API 키 요청")
        return {"success": False, "message": "로그인이 필요합니다"}

    try:
        data = await request.json()
        access_key = data.get("access_key", "").strip()
        secret_key = data.get("secret_key", "").strip()

        # 입력 검증
        if not access_key or not secret_key:
            return {"success": False, "message": "모든 API 키 정보를 입력해주세요"}

        # 업비트 API 키 검증 (간단한 계좌 조회로 검증)
        logger.info(f"🔍 [AUTH] API 키 형식 검증 시작: Access Key 길이 {len(access_key)}, Secret Key 길이 {len(secret_key)}")

        import aiohttp
        import jwt
        import uuid

        # JWT 토큰 생성 (업비트 API 규격)
        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
        authorization = f'Bearer {jwt_token}'
        headers = {'Authorization': authorization}

        # 업비트 API 호출 (계좌 정보 조회로 검증)
        url = "https://api.upbit.com/v1/accounts"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    account_data = await response.json()

                    # API 키 검증 성공
                    logger.info("✅ [AUTH] API 키 검증 성공")

                    # 세션에 API 키 임시 저장 (보안 강화)
                    user_id = current_user.get("id")
                    user_sessions[user_id] = {
                        "access_key": access_key,
                        "secret_key": secret_key,
                        "account_info": account_data,
                        "authenticated_at": datetime.now().isoformat()
                    }

                    # 세션 관리자에도 등록
                    try:
                        username = current_user.get('username', f'user_{user_id}')
                        logger.info(f"🔄 세션 생성 시작: user_id={user_id}, username={username}")

                        user_session = session_manager.create_session(user_id, username)
                        logger.info(f"✅ 세션 생성 성공: {user_session}")

                        # API 키 설정
                        user_session.update_api_keys(access_key, secret_key)
                        logger.info("🔑 API 키 설정 완료")

                        # 로그인 상태 설정 (중요: 거래 시작 조건)
                        user_session.update_login_status(logged_in=True, account_info=account_data)
                        logger.info("🔐 로그인 상태 설정 완료")

                        # KRW 잔고 추출 및 available_budget 설정
                        krw_balance = 0
                        for account in account_data:
                            if account.get("currency") == "KRW":
                                krw_balance = float(account.get("balance", 0))
                                break
                        user_session.trading_state.available_budget = krw_balance
                        logger.info(f"💰 사용 가능 예산 설정 완료: {krw_balance:,}원")

                        logger.info(f"📝 세션 관리자에 사용자 {username} 등록 완료")

                        # 세션 검증
                        check_session = session_manager.get_session(user_id)
                        if check_session:
                            logger.info(f"✅ 세션 검증 성공: 사용자 {username} 세션 존재 확인")
                        else:
                            logger.error(f"❌ 세션 검증 실패: 사용자 {username} 세션을 찾을 수 없음")

                    except Exception as e:
                        logger.error(f"❌ 세션 관리자 등록 실패: {str(e)}")
                        import traceback
                        logger.error(f"상세 오류: {traceback.format_exc()}")

                    return {
                        "success": True,
                        "message": "API 키 검증이 완료되었습니다",
                        "account_count": len(account_data)
                    }
                elif response.status == 401:
                    logger.warning("❌ [AUTH] API 키 인증 실패 (잘못된 키)")
                    return {"success": False, "message": "API 키가 올바르지 않습니다"}
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [AUTH] API 검증 실패 ({response.status}): {error_text}")
                    return {"success": False, "message": f"API 키 검증에 실패했습니다 (상태: {response.status})"}

    except Exception as e:
        logger.error(f"❌ API 키 인증 오류: {str(e)}")
        return {"success": False, "message": f"API 키 검증 중 오류가 발생했습니다: {str(e)}"}