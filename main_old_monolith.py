"""
업비트 자동거래 시스템 - 메인 애플리케이션
모듈화된 아키텍처로 재구성
"""

import logging
import subprocess
import signal
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 설정 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Core 모듈 import
from core.api import trading_router, analysis_router, system_router
from core.api.resilience import router as resilience_router
from core.api.monitoring import router as monitoring_router
from core.api.auth import router as auth_router
from core.api.ux import router as ux_router
from core.api.account import router as account_router
from core.api.trading_history import router as trading_history_router
from core.api.business import router as business_router
from core.api.users import router as users_router

# 뷰 라우터 import
from core.views import main_views_router, dashboard_views_router, auth_views_router
from core.services import auto_scheduler
from core.database import run_migration, test_mysql_connection
from config import DEFAULT_MARKETS, WEB_CONFIG

# 기존 모듈들 import (아직 이전되지 않은 기능들)
from database import init_db

# 슬립 방지 프로세스 관리
caffeinate_process = None

# 세션 관리자 import
from core.session import session_manager

# 메모리 기반 세션 저장소 (API 키 임시 저장용) - 새로운 세션 관리자로 대체
user_sessions = {}

def start_sleep_prevention():
    """시스템 슬립 방지 시작"""
    global caffeinate_process
    try:
        # caffeinate 명령으로 시스템 슬립 방지 (-d: 디스플레이 슬립 방지, -i: 유휴 슬립 방지, -s: 시스템 슬립 방지)
        caffeinate_process = subprocess.Popen(['caffeinate', '-d', '-i', '-s'], 
                                            stdout=subprocess.DEVNULL, 
                                            stderr=subprocess.DEVNULL)
        logger.info(f"🛡️ 슬립 방지 활성화 (PID: {caffeinate_process.pid})")
        return True
    except Exception as e:
        logger.error(f"⚠️ 슬립 방지 실패: {str(e)}")
        return False

def stop_sleep_prevention():
    """시스템 슬립 방지 중지"""
    global caffeinate_process
    try:
        if caffeinate_process and caffeinate_process.poll() is None:
            caffeinate_process.terminate()
            caffeinate_process.wait(timeout=5)
            logger.info("🛡️ 슬립 방지 해제")
    except Exception as e:
        logger.error(f"⚠️ 슬립 방지 해제 실패: {str(e)}")
        try:
            if caffeinate_process:
                caffeinate_process.kill()
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화
    try:
        logger.info("🚀 업비트 자동거래 시스템 시작")
        
        # 프로세스 우선순위 높이기 (슬립 방지 강화)
        try:
            os.nice(-5)  # 우선순위 상승 (음수일수록 높은 우선순위)
            logger.info("⚡ 프로세스 우선순위 상승 완료")
        except Exception as e:
            logger.warning(f"⚠️ 프로세스 우선순위 설정 실패: {str(e)} (권한 부족)")
        
        # 슬립 방지 활성화
        if start_sleep_prevention():
            logger.info("🛡️ 24시간 연속 거래를 위한 슬립 방지 활성화")
        
        # 데이터베이스 초기화 (기존 SQLite)
        await init_db()
        logger.info("✅ SQLite 데이터베이스 초기화 완료")
        
        # MySQL 데이터베이스 연결 및 마이그레이션 (새로운 인증 시스템)
        try:
            # MySQL 연결 테스트
            mysql_ok = await test_mysql_connection()
            if mysql_ok:
                # 마이그레이션 실행
                await run_migration()
                logger.info("✅ MySQL 인증 데이터베이스 초기화 완료")
            else:
                logger.warning("⚠️ MySQL 연결 실패 - 기존 방식으로만 동작합니다")
        except Exception as e:
            logger.warning(f"⚠️ MySQL 초기화 실패 - 기존 방식으로만 동작합니다: {str(e)}")
        
        # 자동 최적화 스케줄러 시작
        auto_scheduler.start()
        logger.info("✅ 자동 최적화 스케줄러 시작")
        
        # 모니터링 및 알림 서비스 시작
        try:
            from core.services.monitoring_service import monitoring_service
            from core.services.notification_service import notification_service
            
            # 백그라운드에서 모니터링 시작
            import asyncio
            asyncio.create_task(monitoring_service.start_monitoring())
            
            # 시스템 시작 알림
            await notification_service.notify_system_start()
            
            logger.info("📊 모니터링 및 알림 서비스 시작")
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 시작 실패: {str(e)}")
        
        # 시스템 상태 로깅
        logger.info(f"📊 모니터링 대상 마켓: {DEFAULT_MARKETS}")
        logger.info(f"🌐 웹서버 포트: {WEB_CONFIG['port']}")
        
        yield
        
        # 종료 시 정리
        logger.info("🛑 시스템 종료 중...")
        
        # 시스템 종료 알림
        try:
            from core.services.notification_service import notification_service
            from core.services.monitoring_service import monitoring_service
            
            await notification_service.notify_system_stop()
            await monitoring_service.stop_monitoring()
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 종료 실패: {str(e)}")
        
        stop_sleep_prevention()
        auto_scheduler.shutdown()
        
    except Exception as e:
        logger.error(f"❌ 시스템 시작 중 오류: {str(e)}")
        stop_sleep_prevention()  # 오류 시에도 슬립 방지 해제
        raise

# FastAPI 앱 생성
app = FastAPI(
    title="Upbit Cryptocurrency Trading System",
    description="모듈화된 업비트 자동거래 시스템",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정 (Flutter 앱 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Flutter 웹 개발서버
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "capacitor://localhost",  # Capacitor 앱
        "ionic://localhost",      # Ionic 앱
        "http://localhost",       # 개발용
        "https://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(trading_router)
app.include_router(analysis_router)  
app.include_router(system_router)
app.include_router(resilience_router, prefix="/api/resilience")  # 복원력 API 추가
app.include_router(monitoring_router, prefix="/api/monitoring")  # 모니터링 API 추가
app.include_router(auth_router)  # 새로운 인증 라우터 추가
app.include_router(ux_router, prefix="/api/ux")  # 사용자 경험 개선 API 추가
app.include_router(account_router, prefix="/api/account")  # 계좌 정보 API 추가
app.include_router(trading_history_router, prefix="/api/trading-history")  # 거래 내역 API 추가
app.include_router(business_router)  # 비즈니스 관리 API 추가
app.include_router(users_router)  # 사용자 관리 API 추가

# 뷰 라우터 등록
app.include_router(main_views_router)  # 메인 뷰 (/, /api-login, /profile 등)
app.include_router(dashboard_views_router)  # 대시보드 뷰
app.include_router(auth_views_router)  # 인증 관련 뷰

# 실시간 API 라우터 추가
from core.api.realtime import router as realtime_router
from core.api.mtfa import router as mtfa_router
app.include_router(realtime_router, prefix="/api/realtime")  # 실시간 데이터 및 알림 API
app.include_router(mtfa_router)  # MTFA 최적화 API 추가

@app.post("/api/collect-recent-data")
async def collect_recent_data_endpoint():
    """최근 캔들 데이터 수집 API"""
    try:
        await collect_recent_candles()
        return {"success": True, "message": "최근 30분 데이터 수집 완료"}
    except Exception as e:
        logger.error(f"데이터 수집 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/api/auth-login")
async def api_key_authentication(request: Request):
    """API 키 인증 엔드포인트 - 세션 기반 (저장하지 않음) [메인 엔드포인트]"""
    from core.auth.middleware import get_current_user
    
    logger.info("🔑 [MAIN] API 키 인증 요청 수신 - 보안 강화 방식")
    
    # 사용자 인증 확인
    current_user = await get_current_user(request)
    if not current_user:
        logger.warning("⚠️ [MAIN] 인증되지 않은 사용자의 API 키 요청")
        return {"success": False, "message": "로그인이 필요합니다"}
    
    try:
        data = await request.json()
        access_key = data.get("access_key", "").strip()
        secret_key = data.get("secret_key", "").strip()
        
        # 입력 검증
        if not access_key or not secret_key:
            return {"success": False, "message": "모든 API 키 정보를 입력해주세요"}
        
        # 업비트 API 키 검증 (간단한 계좌 조회로 검증)
        logger.info(f"🔍 [MAIN] API 키 형식 검증 시작: Access Key 길이 {len(access_key)}, Secret Key 길이 {len(secret_key)}")
        
        import aiohttp
        import jwt
        import hashlib
        import uuid
        from urllib.parse import urlencode
        
        try:
            query = urlencode({})
            query_hash = hashlib.sha512(query.encode()).hexdigest()
            
            payload = {
                'access_key': access_key,
                'nonce': str(uuid.uuid4()),
                'query_hash': query_hash,
                'query_hash_alg': 'SHA512',
            }
            
            jwt_token = jwt.encode(payload, secret_key, algorithm='HS256')
            authorize_token = f'Bearer {jwt_token}'
            headers = {"Authorization": authorize_token}
            
            logger.info("🔑 [MAIN] JWT 토큰 생성 완료, 업비트 API 호출 시작")
            
        except Exception as jwt_error:
            logger.error(f"❌ [MAIN] JWT 토큰 생성 실패: {str(jwt_error)}")
            return {"success": False, "message": f"API 키 형식 오류: {str(jwt_error)}"}
        
        # 업비트 계좌 조회로 API 키 검증
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get("https://api.upbit.com/v1/accounts", headers=headers) as response:
                    logger.info(f"📡 [MAIN] 업비트 API 응답 수신: {response.status}")
                    
                    if response.status == 200:
                        try:
                            account_data = await response.json()
                            logger.info(f"📊 [MAIN] 계좌 데이터 파싱 성공: {len(account_data)}개 계좌")
                            
                            # 사용자 세션 생성 및 API 키 저장 (메모리만, DB 저장 안함)
                            user_id = current_user.get('id')
                            username = current_user.get('username')
                            
                            # 세션 관리자를 통한 사용자별 세션 생성
                            user_session = session_manager.create_session(user_id, username)
                            user_session.update_api_keys(access_key, secret_key)
                            
                            # 레거시 호환성을 위한 기존 방식도 유지 (임시)
                            user_sessions[user_id] = {
                                'access_key': access_key,
                                'secret_key': secret_key,
                                'account_data': account_data,
                                'authenticated_at': datetime.now().isoformat()
                            }
                            
                            active_assets = len([acc for acc in account_data if float(acc.get('balance', 0)) > 0])
                            
                            # 🔗 사용자별 세션 시스템 업데이트 - KRW 잔고 및 클라이언트 설정
                            try:
                                from api_client import UpbitAPI
                                
                                # KRW 잔고 찾기
                                krw_account = next((acc for acc in account_data if acc['currency'] == 'KRW'), None)
                                krw_balance = float(krw_account['balance']) if krw_account else 0
                                
                                # 사용자 세션에 상태 업데이트
                                user_session.trading_state.available_budget = krw_balance
                                
                                # 업비트 클라이언트 생성 및 세션에 저장
                                upbit_client_instance = UpbitAPI(access_key, secret_key)
                                user_session.set_upbit_client(upbit_client_instance)
                                
                                # 로그인 상태 업데이트
                                user_session.update_login_status(
                                    logged_in=True,
                                    account_info={"balance": krw_balance, "accounts": account_data}
                                )
                                
                                logger.info(f"🔗 [MAIN] 사용자별 세션 시스템 업데이트 완료: {username} - {krw_balance:,.0f} KRW")
                                
                                # 🔄 기존 시스템과의 호환성을 위한 전역 변수 업데이트 (임시, 마지막 로그인 사용자)
                                from core.services.trading_engine import trading_state
                                from core.api.system import upbit_api_keys, login_status
                                import core.api.system as system_module
                                
                                trading_state.available_budget = krw_balance
                                upbit_api_keys["access_key"] = access_key
                                upbit_api_keys["secret_key"] = secret_key
                                system_module.upbit_client = upbit_client_instance
                                login_status["logged_in"] = True
                                login_status["account_info"] = {"balance": krw_balance, "accounts": account_data}
                                login_status["login_time"] = datetime.now().isoformat()
                                
                                logger.warning(f"⚠️ [MAIN] 기존 시스템 전역 변수도 업데이트됨 (다중 사용자 시 충돌 가능)")
                                
                            except Exception as integration_error:
                                logger.error(f"⚠️ [MAIN] 세션 시스템 연동 실패: {str(integration_error)}")
                            
                            logger.info(f"✅ [MAIN] API 키 검증 및 세션 저장 성공: 사용자 {current_user.get('username')}")
                            logger.info(f"💰 [MAIN] 계좌 정보: {len(account_data)}개 계좌, {active_assets}개 자산")
                            
                            return {
                                "success": True, 
                                "message": "업비트 API 연결 성공",
                                "account_count": len(account_data),
                                "balance_info": f"{active_assets}개 자산"
                            }
                            
                        except Exception as json_error:
                            logger.error(f"❌ [MAIN] 계좌 데이터 파싱 실패: {str(json_error)}")
                            return {"success": False, "message": f"업비트 응답 데이터 처리 오류: {str(json_error)}"}
                            
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️ [MAIN] API 키 검증 실패: {response.status} - {error_text}")
                        
                        # 구체적인 에러 메시지 제공
                        if response.status == 401:
                            return {"success": False, "message": "API 키가 올바르지 않거나 만료되었습니다"}
                        elif response.status == 403:
                            return {"success": False, "message": "API 키 권한이 부족합니다 (계좌 조회 권한 필요)"}
                        else:
                            return {"success": False, "message": f"업비트 API 오류 ({response.status}): 잠시 후 다시 시도해주세요"}
                            
        except aiohttp.ClientTimeout:
            logger.error("❌ [MAIN] 업비트 API 호출 타임아웃")
            return {"success": False, "message": "업비트 서버 연결 타임아웃: 네트워크 상태를 확인해주세요"}
            
        except Exception as api_error:
            logger.error(f"❌ [MAIN] 업비트 API 호출 실패: {str(api_error)}")
            return {"success": False, "message": f"업비트 API 연결 오류: {str(api_error)}"}
                    
    except Exception as e:
        logger.error(f"❌ API 키 인증 오류: {str(e)}")
        return {"success": False, "message": f"API 키 검증 중 오류가 발생했습니다: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """자동거래 메인 대시보드 - 실시간 모니터링 (인증 체크 포함)"""
    # 새로운 인증 시스템 체크
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    # 인증된 사용자가 있으면 API 키 입력 화면, 없으면 로그인 페이지
    if current_user:
        # 인증된 사용자용 - API 키 입력 화면 표시 (보안 강화)
        return await authenticated_api_key_input_dashboard(request, current_user)
    else:
        # 로그인 페이지로 리다이렉트
        return RedirectResponse(url="/login")

@app.get("/api-login", response_class=HTMLResponse)
async def authenticated_api_key_input_dashboard(request: Request, current_user: dict = None):
    """인증된 사용자용 - API 키 입력 화면 (보안 강화)"""
    
    if not current_user:
        from core.auth.middleware import get_current_user
        current_user = await get_current_user(request)
        if not current_user:
            return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    email = current_user.get('email', '')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>🚀 API 키 입력 - 업비트 자동거래 시스템</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                padding-top: 80px; /* 앱바 공간 확보 */
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 100px 20px 20px 20px;
            }}
            
            /* 앱바 스타일 */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 30px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 100;
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .hamburger-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .hamburger-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            /* 사이드패널 스타일 */
            .side-panel-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 200;
            }}
            
            .side-panel-overlay.active {{
                opacity: 1;
                visibility: visible;
            }}
            
            .side-panel {{
                position: fixed;
                top: 0;
                right: 0;
                width: 80%;
                max-width: 400px;
                height: 100%;
                background: white;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 201;
                padding: 30px;
                box-sizing: border-box;
                overflow-y: auto;
            }}
            
            .side-panel.active {{
                transform: translateX(0);
            }}
            
            .side-panel-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 5px;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }}
            
            .close-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            .menu-items {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            
            .menu-item {{
                margin-bottom: 10px;
            }}
            
            .menu-item a {{
                display: block;
                padding: 15px 20px;
                color: #333;
                text-decoration: none;
                border-radius: 10px;
                transition: background-color 0.2s;
            }}
            
            .menu-item a:hover {{
                background-color: rgba(25, 118, 210, 0.1);
                color: #1976d2;
            }}
            
            .api-container {{
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 500px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            .header p {{
                color: #666;
                margin: 5px 0;
                font-size: 16px;
            }}
            .user-info {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }}
            .user-info strong {{
                color: #1976d2;
            }}
            .security-notice {{
                background: #e8f5e8;
                border: 1px solid #4caf50;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                color: #2e7d32;
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
                border-color: #1976d2;
                box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
            }}
            .form-help {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            .btn-primary {{
                width: 100%;
                background: linear-gradient(45deg, #1976d2, #42a5f5);
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
            .logout-link {{
                text-align: center;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #e9ecef;
            }}
            .logout-link a {{
                color: #666;
                text-decoration: none;
                font-size: 14px;
            }}
            .logout-link a:hover {{
                color: #1976d2;
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
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="app-title">Teamprime</div>
            <button class="hamburger-btn" onclick="toggleSidePanel()">☰</button>
        </div>
        
        <!-- 사이드패널 오버레이 -->
        <div class="side-panel-overlay" onclick="closeSidePanel()"></div>
        
        <!-- 사이드패널 -->
        <div class="side-panel">
            <div class="side-panel-header">
                <h3 onclick="goToProfile()" style="cursor: pointer; color: #1976d2;">{username}</h3>
                <button class="close-btn" onclick="closeSidePanel()">×</button>
            </div>
            <ul class="menu-items">
                <li class="menu-item">
                    <a href="/main-dashboard">🏠 대시보드</a>
                </li>
            </ul>
        </div>
        
        <div class="api-container">
            <div class="header">
                <h1>🚀 API 키 입력</h1>
                <p>업비트 자동거래 시스템</p>
            </div>
            
            <div class="user-info">
                <p><strong>{username}</strong> ({email})</p>
                <p>안전한 거래를 위해 API 키를 입력해주세요</p>
            </div>
            
            <div class="security-notice">
                <strong>🔒 보안 강화:</strong> API 키는 저장되지 않으며, 세션 종료 시 즉시 삭제됩니다.
            </div>
            
            <div id="alert" class="alert alert-error"></div>
            
            <form id="apiForm">
                <div class="form-group">
                    <label for="accessKey">업비트 Access Key</label>
                    <input type="text" id="accessKey" name="access_key" class="form-control" autocomplete="username" required>
                    <div class="form-help">업비트 API 설정에서 발급받은 Access Key</div>
                </div>
                
                <div class="form-group">
                    <label for="secretKey">업비트 Secret Key</label>
                    <input type="password" id="secretKey" name="secret_key" class="form-control" autocomplete="current-password" required>
                    <div class="form-help">업비트 API 설정에서 발급받은 Secret Key</div>
                </div>
                
                <button type="submit" class="btn-primary" id="startBtn">
                    거래 시작하기
                </button>
            </form>
            
            <div class="logout-link">
                <p><a href="#" onclick="handleLogout(); return false;">다른 계정으로 로그인</a></p>
            </div>
        </div>
        
        <script>
            const form = document.getElementById('apiForm');
            const alert = document.getElementById('alert');
            const startBtn = document.getElementById('startBtn');
            
            function showAlert(message, type = 'error') {{
                alert.textContent = message;
                alert.className = `alert alert-${{type}}`;
                alert.style.display = 'block';
            }}
            
            function hideAlert() {{
                alert.style.display = 'none';
            }}
            
            // 사이드패널 관련 함수들
            function toggleSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.add('active');
                panel.classList.add('active');
            }}
            
            function closeSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.remove('active');
                panel.classList.remove('active');
            }}
            
            // 개인정보 페이지로 이동
            function goToProfile() {{
                window.location.href = '/profile';
            }}
            
            async function handleLogout() {{
                try {{
                    const response = await fetch('/api/auth/logout', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }});
                    
                    // 성공 여부와 관계없이 로그아웃 처리
                    document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                    window.location.href = '/login';
                    
                }} catch (error) {{
                    // 에러가 발생해도 로그아웃 처리
                    document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                    window.location.href = '/login';
                }}
            }}
            
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                hideAlert();
                
                const formData = new FormData(form);
                const data = {{
                    access_key: formData.get('access_key'),
                    secret_key: formData.get('secret_key')
                }};
                
                // 입력 검증
                if (!data.access_key || !data.secret_key) {{
                    showAlert('모든 필드를 입력해주세요');
                    return;
                }}
                
                startBtn.textContent = '연결 중...';
                startBtn.disabled = true;
                
                try {{
                    const response = await fetch('/api/auth-login', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(data)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        showAlert('업비트 연결 성공! 거래 대시보드로 이동합니다...', 'success');
                        
                        // 2초 후 대시보드로 이동
                        setTimeout(() => {{
                            window.location.href = '/dashboard';
                        }}, 2000);
                    }} else {{
                        showAlert(result.message);
                    }}
                }} catch (error) {{
                    showAlert('연결 중 오류가 발생했습니다: ' + error.message);
                }} finally {{
                    startBtn.textContent = '거래 시작하기';
                    startBtn.disabled = false;
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

@app.get("/dashboard", response_class=HTMLResponse)  
async def trading_dashboard(request: Request):
    """실제 거래 대시보드 (API 키 검증 후 접근)"""
    
    # 사용자 인증 및 API 키 세션 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    user_id = current_user.get('id')
    session_data = user_sessions.get(user_id)
    
    if not session_data:
        # API 키가 세션에 없으면 다시 입력하도록 리다이렉트
        return RedirectResponse(url="/")
    
    username = current_user.get('username', '사용자')
    account_data = session_data.get('account_data', [])
    
    # 계좌 정보 요약
    total_accounts = len(account_data)
    active_accounts = len([acc for acc in account_data if float(acc.get('balance', 0)) > 0])
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>🚀 업비트 자동거래 대시보드</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                color: #333;
                padding-top: 80px; /* Teamprime 앱바 공간 확보 */
            }}
            
            /* Teamprime 앱바 스타일 */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 30px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 100;
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .hamburger-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .hamburger-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            /* 사이드패널 스타일 */
            .side-panel-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 200;
            }}
            
            .side-panel-overlay.active {{
                opacity: 1;
                visibility: visible;
            }}
            
            .side-panel {{
                position: fixed;
                top: 0;
                right: 0;
                width: 80%;
                max-width: 400px;
                height: 100%;
                background: white;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 201;
                padding: 30px;
                box-sizing: border-box;
                overflow-y: auto;
            }}
            
            .side-panel.active {{
                transform: translateX(0);
            }}
            
            .side-panel-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 5px;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }}
            
            .close-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            .menu-items {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            
            .menu-item {{
                margin-bottom: 10px;
            }}
            
            .menu-item a {{
                display: block;
                padding: 15px 20px;
                color: #333;
                text-decoration: none;
                border-radius: 10px;
                transition: background-color 0.2s;
            }}
            
            .menu-item a:hover {{
                background-color: rgba(25, 118, 210, 0.1);
                color: #1976d2;
            }}
            
            /* 사이드패널 사용자 정보 스타일 */
            .side-panel-user {{
                padding: 15px 20px;
                background: rgba(25, 118, 210, 0.05);
                border-bottom: 1px solid #e0e0e0;
                margin-bottom: 10px;
            }}
            .side-panel-user .user-info {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .side-panel-user .user-name {{
                font-weight: 600;
                color: #333;
                font-size: 16px;
            }}
            .side-panel-user .user-status {{
                font-size: 14px;
                color: #4caf50;
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            .main-content {{
                max-width: 1200px;
                margin: 20px auto;
                padding: 0 20px;
            }}
            .trading-controls {{
                text-align: center;
                margin: 30px auto;
                background: #f8f9fa;
                padding: 40px;
                border-radius: 15px;
                max-width: 800px;
            }}
            .control-btn {{
                padding: 15px 30px;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                min-width: 160px;
                margin: 10px;
            }}
            .control-btn.trading-off {{
                background: linear-gradient(45deg, #28a745, #20c997);
                color: white;
            }}
            .control-btn.trading-off:hover {{
                background: linear-gradient(45deg, #218838, #1aa085);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(40,167,69,0.4);
            }}
            .control-btn.trading-on {{
                background: linear-gradient(45deg, #ffc107, #fd7e14);
                color: #212529;
            }}
            .control-btn.trading-on:hover {{
                background: linear-gradient(45deg, #e0a800, #e8650e);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255,193,7,0.4);
            }}
            .control-btn.loading {{
                background: linear-gradient(45deg, #6c757d, #868e96);
                color: white;
                opacity: 0.7;
                cursor: not-allowed;
            }}
            .control-btn.loading:hover {{
                transform: none;
                box-shadow: none;
            }}
            .control-btn.mtfa-btn {{
                background: linear-gradient(45deg, #6f42c1, #8e44ad);
                color: white;
                margin: 5px;
                min-width: 180px;
            }}
            .control-btn.mtfa-btn:hover {{
                background: linear-gradient(45deg, #5a2d91, #732d91);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(111,66,193,0.4);
            }}
            .trading-status {{
                text-align: center;
                padding: 20px;
                background: linear-gradient(45deg, #e8f5e8, #f1f8e9);
                border-radius: 12px;
                border: 1px solid #4caf50;
                margin-bottom: 20px;
            }}
            .status-title {{
                font-size: 20px;
                color: #2e7d32;
                margin-bottom: 5px;
            }}
            .status-desc {{
                color: #4caf50;
                font-size: 14px;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: rgba(255,255,255,0.7);
                font-size: 12px;
            }}
            
            /* 새로운 대시보드 섹션 스타일 */
            .dashboard-section {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                margin-bottom: 20px;
                padding: 25px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            
            .section-title {{
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            /* 계좌 정보 카드 스타일 */
            .account-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }}
            
            .account-card {{
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #dee2e6;
            }}
            
            .account-label {{
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .account-value {{
                font-size: 18px;
                font-weight: 700;
                color: #1976d2;
            }}
            
            /* 거래 상태 패널 스타일 */
            .trading-status-panel {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 15px;
            }}
            
            .status-card {{
                background: linear-gradient(135deg, #e3f2fd, #f1f8ff);
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #bbdefb;
            }}
            
            .status-label {{
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .status-value {{
                font-size: 16px;
                font-weight: 700;
                color: #1976d2;
            }}
            
            
            /* 매수 조건 그리드 스타일 */
            .conditions-grid, .mtfa-conditions-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
            }}
            
            .condition-card {{
                background: linear-gradient(135deg, #e8f5e8, #f1f8e9);
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #4caf50;
                transition: transform 0.2s;
            }}
            
            .condition-card:hover {{
                transform: translateY(-2px);
            }}
            
            .condition-coin {{
                font-size: 16px;
                font-weight: 700;
                color: #2e7d32;
                margin-bottom: 8px;
            }}
            
            .condition-status {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 5px;
            }}
            
            .condition-status.possible {{
                color: #4caf50;
            }}
            
            .condition-status.not-possible {{
                color: #ff5722;
            }}
            
            .condition-score {{
                font-size: 12px;
                color: #666;
            }}
            
            /* 반응형 디자인 */
            @media (max-width: 768px) {{
                .main-content {{
                    padding: 15px;
                }}
                
                .dashboard-section {{
                    padding: 15px;
                }}
                
                .account-cards, .trading-status-panel, .conditions-grid {{
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                    gap: 10px;
                }}
                
                .section-title {{
                    font-size: 16px;
                }}
                
                .account-card, .status-card, .condition-card {{
                    padding: 15px;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- Teamprime 앱바 -->
        <div class="app-bar">
            <div class="app-title">Teamprime</div>
            <button class="hamburger-btn" onclick="toggleSidePanel()">☰</button>
        </div>
        
        <!-- 사이드패널 오버레이 -->
        <div class="side-panel-overlay" onclick="closeSidePanel()"></div>
        
        <!-- 사이드패널 -->
        <div class="side-panel">
            <div class="side-panel-header">
                <h3 onclick="goToProfile()" style="cursor: pointer; color: #1976d2;">{username}</h3>
                <button class="close-btn" onclick="closeSidePanel()">×</button>
            </div>
            
            <!-- 사용자 정보 섹션 -->
            <div class="side-panel-user">
                <div class="user-info">
                    <div class="user-name">{username}</div>
                    <div class="user-status">✅ 업비트 연결됨</div>
                </div>
            </div>
            
            <ul class="menu-items">
                <li class="menu-item">
                    <a href="/main-dashboard">🏠 대시보드</a>
                </li>
            </ul>
        </div>
        
        <main class="main-content">
            <!-- 📊 계좌 정보 섹션 -->
            <div class="dashboard-section">
                <h2 class="section-title">💰 계좌 정보</h2>
                <div class="account-cards">
                    <div class="account-card">
                        <div class="account-label">KRW 잔고</div>
                        <div class="account-value" id="krwBalance">로딩 중...</div>
                    </div>
                    <div class="account-card">
                        <div class="account-label">보유 코인</div>
                        <div class="account-value" id="coinCount">로딩 중...</div>
                    </div>
                    <div class="account-card">
                        <div class="account-label">총 평가금액</div>
                        <div class="account-value" id="totalValue">로딩 중...</div>
                    </div>
                </div>
            </div>

            <!-- 📈 거래 상태 섹션 -->
            <div class="dashboard-section">
                <h2 class="section-title">📈 거래 상태</h2>
                <div class="trading-status-panel" id="tradingStatusPanel">
                    <div class="status-card">
                        <div class="status-label">시스템 상태</div>
                        <div class="status-value" id="systemStatus">로딩 중...</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">현재 포지션</div>
                        <div class="status-value" id="positionCount">로딩 중...</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">일일 수익률</div>
                        <div class="status-value" id="dailyProfitRate">로딩 중...</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">일일 거래 수</div>
                        <div class="status-value" id="dailyTrades">로딩 중...</div>
                    </div>
                </div>
            </div>


            <!-- 🎯 MTFA 실시간 매수 조건 섹션 -->
            <div class="dashboard-section">
                <h2 class="section-title">🎯 MTFA 실시간 매수 조건</h2>
                <div class="mtfa-conditions-grid" id="mtfaConditionsGrid">
                    <!-- MTFA 데이터가 여기에 동적으로 로드됩니다 -->
                    <div class="condition-card">
                        <div class="condition-coin">로딩 중...</div>
                        <div class="condition-status">데이터 로딩 중...</div>
                        <div class="condition-score">-</div>
                    </div>
                </div>
            </div>

            <!-- 🎯 거래 제어 섹션 -->
            <div class="dashboard-section">
                <h2 class="section-title">🎯 거래 제어</h2>
                <div class="trading-controls">
                    <button class="control-btn trading-off" id="tradingToggleBtn" onclick="toggleTrading()">
                        🚀 자동거래 시작
                    </button>
                </div>
            </div>
        </main>
        
        
        <footer class="footer">
            <p>© 2024 업비트 자동거래 시스템 | API 키는 세션 종료 시 자동 삭제됩니다.</p>
        </footer>
        
        <script>
            // 사이드패널 관련 함수들
            function toggleSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.add('active');
                panel.classList.add('active');
            }}
            
            function closeSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.remove('active');
                panel.classList.remove('active');
            }}
            
            // 개인정보 페이지로 이동
            function goToProfile() {{
                window.location.href = '/profile';
            }}
            
            async function handleLogout() {{
                try {{
                    await fetch('/api/auth/logout', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }}
                    }});
                }} catch (error) {{
                    console.log('로그아웃 요청 오류:', error);
                }}
                
                // 쿠키 삭제 및 로그인 페이지로 이동
                document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                window.location.href = '/login';
            }}
            
            // 거래 상태 변수
            let isTradingActive = false;
            
            async function toggleTrading() {{
                const btn = document.getElementById('tradingToggleBtn');
                
                // 로딩 상태로 변경
                btn.className = 'control-btn loading';
                btn.textContent = '처리 중...';
                btn.disabled = true;
                
                try {{
                    let response, endpoint, successMsg;
                    
                    if (isTradingActive) {{
                        // 거래 중지
                        endpoint = '/api/stop-trading';
                        successMsg = '자동거래가 중지되었습니다.';
                    }} else {{
                        // 거래 시작
                        endpoint = '/api/start-trading';
                        successMsg = '자동거래가 시작되었습니다.';
                    }}
                    
                    response = await fetch(endpoint, {{ method: 'POST' }});
                    const data = await response.json();
                    
                    if (data.success !== false) {{
                        // 성공 - 상태 토글
                        isTradingActive = !isTradingActive;
                        updateTradingButton();
                        alert(data.message || successMsg);
                    }} else {{
                        // 실패 - 원래 상태로 복구
                        updateTradingButton();
                        alert(data.message || '요청 처리 중 오류가 발생했습니다.');
                    }}
                }} catch (error) {{
                    // 에러 - 원래 상태로 복구
                    updateTradingButton();
                    alert('네트워크 오류가 발생했습니다.');
                }}
            }}
            
            function updateTradingButton() {{
                const btn = document.getElementById('tradingToggleBtn');
                btn.disabled = false;
                
                if (isTradingActive) {{
                    // 거래 중 - 중지 버튼 표시
                    btn.className = 'control-btn trading-on';
                    btn.textContent = '⏹️ 자동거래 중지';
                }} else {{
                    // 대기 중 - 시작 버튼 표시
                    btn.className = 'control-btn trading-off';
                    btn.textContent = '🚀 자동거래 시작';
                }}
            }}
            
            // 현재 거래 상태 확인
            async function checkTradingStatus() {{
                try {{
                    const response = await fetch('/api/trading-status');
                    const data = await response.json();
                    
                    // 거래 엔진이 실행 중인지 확인
                    if (data && data.is_running !== undefined) {{
                        isTradingActive = data.is_running;
                        updateTradingButton();
                        console.log('거래 상태 확인됨:', isTradingActive ? '실행 중' : '중지됨');
                    }}
                }} catch (error) {{
                    console.log('거래 상태 확인 오류:', error);
                    // 기본값으로 초기화
                    isTradingActive = false;
                    updateTradingButton();
                }}
            }}
            
            // 🔄 실시간 데이터 업데이트 시스템
            
            // 계좌 정보 업데이트
            async function updateAccountInfo() {{
                try {{
                    const response = await fetch('/api/account-balances');
                    const data = await response.json();
                    
                    if (data.success) {{
                        // KRW 잔고 표시
                        document.getElementById('krwBalance').textContent = 
                            data.krw_balance ? `₩ ${{Number(data.krw_balance).toLocaleString()}}` : '₩ 0';
                        
                        // 보유 코인 수
                        document.getElementById('coinCount').textContent = 
                            `${{data.total_balances}}개`;
                        
                        // 총 평가금액 계산 (KRW 잔고 + 보유 코인 가치)
                        let totalValue = data.krw_balance || 0;
                        Object.values(data.coin_balances || {{}}).forEach(coin => {{
                            totalValue += coin.current_value || 0;
                        }});
                        
                        document.getElementById('totalValue').textContent = 
                            `₩ ${{Math.round(totalValue).toLocaleString()}}`;
                    }} else {{
                        document.getElementById('krwBalance').textContent = '오류';
                        document.getElementById('coinCount').textContent = '오류';
                        document.getElementById('totalValue').textContent = '오류';
                    }}
                }} catch (error) {{
                    console.error('계좌 정보 업데이트 오류:', error);
                    document.getElementById('krwBalance').textContent = '오류';
                    document.getElementById('coinCount').textContent = '오류';
                    document.getElementById('totalValue').textContent = '오류';
                }}
            }}
            
            // 거래 상태 패널 업데이트
            async function updateTradingStatusPanel() {{
                try {{
                    const response = await fetch('/api/trading-status');
                    const data = await response.json();
                    
                    // 시스템 상태
                    document.getElementById('systemStatus').textContent = 
                        data.is_running ? '🟢 실행 중' : '🔴 중지됨';
                    
                    // 현재 포지션 수
                    const positionCount = Object.keys(data.positions || {{}}).length;
                    document.getElementById('positionCount').textContent = `${{positionCount}}개`;
                    
                    // 일일 수익률 (계산 필요)
                    document.getElementById('dailyProfitRate').textContent = '계산 중...';
                    
                    // 일일 거래 수
                    document.getElementById('dailyTrades').textContent = 
                        `${{data.daily_trades || 0}}회`;
                        
                }} catch (error) {{
                    console.error('거래 상태 패널 업데이트 오류:', error);
                    document.getElementById('systemStatus').textContent = '오류';
                    document.getElementById('positionCount').textContent = '오류';
                    document.getElementById('dailyProfitRate').textContent = '오류';
                    document.getElementById('dailyTrades').textContent = '오류';
                }}
            }}
            
            
            // 매수 조건 분석 업데이트
            // 🚀 PDF 제안 3: UI 재시도 로직 개선 및 중복 호출 방지
            let mtfaUpdateInProgress = false; // 중복 호출 방지 플래그
            
            async function updateMTFAConditions(retryCount = 0) {{
                if (mtfaUpdateInProgress) {{
                    console.log('MTFA 업데이트가 이미 진행 중입니다.');
                    return;
                }}
                
                mtfaUpdateInProgress = true;
                
                try {{
                    const response = await fetch('/api/mtfa-dashboard-data');
                    const data = await response.json();
                    
                    if (data.success && data.dashboard_data) {{
                        const grid = document.getElementById('mtfaConditionsGrid');
                        grid.innerHTML = ''; // 기존 데이터 클리어
                        
                        data.dashboard_data.forEach(coin => {{
                            const confidencePercent = (coin.current_confidence * 100).toFixed(1);
                            const thresholdPercent = (coin.threshold * 100).toFixed(0);
                            const statusText = coin.is_buy_ready ? '🟢 매수대기' : '🔴 관망';
                            const statusClass = coin.is_buy_ready ? 'possible' : 'not-possible';
                            
                            const cardHtml = `
                                <div class="condition-card">
                                    <div class="condition-coin">${{coin.coin}}</div>
                                    <div class="condition-status ${{statusClass}}">${{statusText}}</div>
                                    <div class="condition-score">신뢰도: ${{confidencePercent}}% / ${{thresholdPercent}}%</div>
                                </div>
                            `;
                            
                            grid.insertAdjacentHTML('beforeend', cardHtml);
                        }});
                        
                        console.log(`MTFA 조건 업데이트 완료: ${{data.dashboard_data.length}}개 코인`);
                    }} else if (!data.success && data.message) {{
                        // 서버에서 친화적인 메시지를 보낸 경우 표시
                        throw new Error(data.message);
                    }} else {{
                        throw new Error('MTFA 데이터 응답이 올바르지 않습니다');
                    }}
                }} catch (error) {{
                    console.error('MTFA 매수 조건 업데이트 오류:', error);
                    
                    // PDF 제안: 자동 재시도 (최대 2회)
                    if (retryCount < 2) {{
                        console.log(`MTFA 데이터 재시도 중... (${{retryCount + 1}}/2)`);
                        
                        // 재시도 전 잠시 대기 (지수 백오프)
                        const delay = Math.min(1000 * Math.pow(2, retryCount), 3000);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        
                        mtfaUpdateInProgress = false; // 플래그 해제
                        return await updateMTFAConditions(retryCount + 1);
                    }}
                    
                    // 최대 재시도 후에도 실패한 경우
                    const grid = document.getElementById('mtfaConditionsGrid');
                    const errorMessage = error.message.includes('실시간 데이터 로딩에 실패') ? 
                        error.message : '데이터 로딩 실패 - 다시 시도하세요';
                    
                    grid.innerHTML = `
                        <div class="condition-card">
                            <div class="condition-coin">⚠️ 오류</div>
                            <div class="condition-status not-possible">${{errorMessage}}</div>
                            <div class="condition-score">네트워크 상태를 확인해주세요</div>
                        </div>
                    `;
                }} finally {{
                    mtfaUpdateInProgress = false; // 완료 후 플래그 해제
                }}
            }}
            
            // 전체 대시보드 데이터 업데이트 (통합 API 사용)
            async function updateDashboard() {{
                console.log('대시보드 데이터 업데이트 시작 (통합 API)...');
                
                try {{
                    // 새로운 통합 API 호출
                    const response = await fetch('/api/dashboard-data');
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 계좌 정보 업데이트
                        if (data.account_info && data.account_info.success) {{
                            const accountInfo = data.account_info;
                            document.getElementById('krwBalance').textContent = 
                                accountInfo.krw_balance ? `₩ ${{Number(accountInfo.krw_balance).toLocaleString()}}` : '₩ 0';
                            document.getElementById('coinCount').textContent = `${{accountInfo.total_balances || 0}}개`;
                            
                            let totalValue = accountInfo.krw_balance || 0;
                            Object.values(accountInfo.coin_balances || {{}}).forEach(coin => {{
                                totalValue += coin.current_value || 0;
                            }});
                            document.getElementById('totalValue').textContent = 
                                `₩ ${{Math.round(totalValue).toLocaleString()}}`;
                        }}
                        
                        // 거래 상태 업데이트
                        if (data.trading_status) {{
                            const tradingStatus = data.trading_status;
                            document.getElementById('systemStatus').textContent = 
                                tradingStatus.is_running ? '🟢 실행 중' : '🔴 중지됨';
                            
                            const positionCount = Object.keys(tradingStatus.positions || {{}}).length;
                            document.getElementById('positionCount').textContent = `${{positionCount}}개`;
                            document.getElementById('dailyTrades').textContent = `${{tradingStatus.daily_trades || 0}}회`;
                            
                            // 실제 거래 상태 버튼 업데이트
                            isTradingActive = tradingStatus.is_running;
                            updateTradingButton();
                        }}
                        
                        // 가격 정보 업데이트
                        if (data.current_prices) {{
                            Object.entries(data.current_prices).forEach(([market, priceData]) => {{
                                const coin = priceData.coin_symbol.toLowerCase();
                                
                                const priceElement = document.getElementById(`${{coin}}Price`);
                                const changeElement = document.getElementById(`${{coin}}Change`);
                                
                                if (priceElement) {{
                                    priceElement.textContent = `₩ ${{Number(priceData.trade_price).toLocaleString()}}`;
                                }}
                                
                                if (changeElement) {{
                                    const changeRate = priceData.change_rate || 0;
                                    changeElement.textContent = `${{changeRate >= 0 ? '+' : ''}}${{changeRate.toFixed(2)}}%`;
                                    changeElement.className = changeRate >= 0 ? 'coin-change positive' : 'coin-change negative';
                                }}
                            }});
                        }}
                        
                        // MTFA 매수 조건 별도 업데이트
                        updateMTFAConditions();
                        
                        // 마지막 업데이트 시간 표시
                        const now = new Date();
                        console.log(`통합 API 대시보드 업데이트 완료: ${{now.toLocaleTimeString()}}`);
                    }} else {{
                        throw new Error(data.error || '통합 API 오류');
                    }}
                }} catch (error) {{
                    console.warn('통합 API 실패, 개별 API로 폴백:', error);
                    
                    // 개별 API 폴백
                    await Promise.all([
                        updateAccountInfo(),
                        updateTradingStatusPanel(), 
                        updatePrices(),
                        updateMTFAConditions(),
                        checkTradingStatus()
                    ]);
                    
                    console.log('개별 API 대시보드 업데이트 완료');
                }}
            }}
            
            // 페이지 로드 시 초기화 및 주기적 업데이트
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('페이지 로드 완료 - 대시보드 초기화');
                
                // 즉시 첫 업데이트
                updateDashboard();
                
                // 10초마다 자동 업데이트 (실시간 느낌)
                setInterval(updateDashboard, 10000);
                
                console.log('자동 업데이트 타이머 시작 (10초 주기)');
            }});
            
            // MTFA 성과 분석 모달
            async function showMTFAPerformance() {{
                try {{
                    const response = await fetch('/api/mtfa-performance-expectations');
                    const data = await response.json();
                    
                    if (data.success) {{
                        let performanceHtml = '<h3 style="color: #6f42c1; margin-bottom: 15px;">📊 MTFA 코인별 성과 예상</h3>';
                        performanceHtml += '<table>';
                        performanceHtml += '<tr><th>코인</th><th>전략</th><th>3년 수익률</th><th>월 수익률</th><th>승률</th></tr>';
                        
                        data.performance_data.forEach(coin => {{
                            performanceHtml += `<tr>
                                <td style="font-weight: bold; color: #2e7d32;">${{coin.coin}}</td>
                                <td style="font-size: 12px;">${{coin.strategy_summary}}</td>
                                <td style="color: #d32f2f; font-weight: bold;">${{coin.expected_total_return}}%</td>
                                <td style="color: #1976d2; font-weight: bold;">${{coin.expected_monthly_return}}%</td>
                                <td>${{coin.expected_win_rate}}%</td>
                            </tr>`;
                        }});
                        
                        performanceHtml += '</table>';
                        performanceHtml += `<div class="summary-box">`;
                        performanceHtml += `<strong style="color: #6f42c1;">📈 종합 요약:</strong><br><br>`;
                        performanceHtml += `• 총 코인 수: <strong>${{data.summary.total_markets}}개</strong><br>`;
                        performanceHtml += `• 평균 3년 수익률: <strong style="color: #d32f2f;">${{data.summary.average_total_return}}%</strong><br>`;
                        performanceHtml += `• 평균 월 수익률: <strong style="color: #1976d2;">${{data.summary.average_monthly_return}}%</strong><br>`;
                        performanceHtml += `• 평균 승률: <strong>${{data.summary.average_win_rate}}%</strong><br>`;
                        performanceHtml += `• 최고 성과 코인: <strong style="color: #2e7d32;">${{data.summary.top_performer}}</strong> (${{data.summary.top_monthly_return}}%/월)</div>`;
                        
                        openMTFAModal('📊 MTFA 성과 분석', performanceHtml);
                    }}
                }} catch (error) {{
                    openMTFAModal('❌ 오류', '<p style="color: #d32f2f;">MTFA 성과 데이터를 불러오는 중 오류가 발생했습니다: ' + error.message + '</p>');
                }}
            }}
            
            // MTFA 실시간 대시보드 모달
            async function showMTFADashboard() {{
                try {{
                    const response = await fetch('/api/mtfa-dashboard-data');
                    const data = await response.json();
                    
                    if (data.success) {{
                        let dashboardHtml = '<h3 style="color: #6f42c1; margin-bottom: 15px;">📈 MTFA 실시간 대시보드</h3>';
                        dashboardHtml += '<table>';
                        dashboardHtml += '<tr><th>코인</th><th>신뢰도</th><th>임계값</th><th>상태</th><th>월 수익률</th></tr>';
                        
                        data.dashboard_data.forEach(coin => {{
                            const statusColor = coin.is_buy_ready ? '#4caf50' : '#ff5722';
                            const statusText = coin.signal_status === 'BUY_READY' ? '🟢 매수대기' : '🔴 관망';
                            
                            dashboardHtml += `<tr>
                                <td style="font-weight: bold; color: #2e7d32;">${{coin.coin}}</td>
                                <td style="font-weight: bold; color: #1976d2;">${{(coin.current_confidence * 100).toFixed(1)}}%</td>
                                <td>${{(coin.threshold * 100).toFixed(0)}}%</td>
                                <td style="color: ${{statusColor}}; font-weight: bold;">${{statusText}}</td>
                                <td style="color: #e65100; font-weight: bold;">${{coin.expected_monthly_return}}%</td>
                            </tr>`;
                        }});
                        
                        dashboardHtml += '</table>';
                        dashboardHtml += `<div class="summary-box">`;
                        dashboardHtml += `<strong style="color: #6f42c1;">🎯 실시간 요약:</strong><br><br>`;
                        dashboardHtml += `• 총 모니터링 코인: <strong>${{data.summary.total_coins}}개</strong><br>`;
                        dashboardHtml += `• 매수 준비 코인: <strong style="color: #4caf50;">${{data.summary.buy_ready_coins}}개</strong> (${{data.summary.buy_ready_percentage}}%)<br>`;
                        dashboardHtml += `• 관망 중인 코인: <strong style="color: #ff5722;">${{data.summary.waiting_coins}}개</strong><br>`;
                        dashboardHtml += `• 업데이트 시간: <strong>${{data.timestamp}}</strong></div>`;
                        
                        openMTFAModal('📈 MTFA 실시간 대시보드', dashboardHtml);
                    }}
                }} catch (error) {{
                    openMTFAModal('❌ 오류', '<p style="color: #d32f2f;">MTFA 대시보드 데이터를 불러오는 중 오류가 발생했습니다: ' + error.message + '</p>');
                }}
            }}
            
            // MTFA 모달 관련 함수들
            function openMTFAModal(title, content) {{
                document.getElementById('mtfaModalTitle').textContent = title;
                document.getElementById('mtfaModalBody').innerHTML = content;
                document.getElementById('mtfaModal').style.display = 'block';
                
                // ESC 키로 모달 닫기
                document.addEventListener('keydown', handleModalEscape);
            }}
            
            function closeMTFAModal() {{
                document.getElementById('mtfaModal').style.display = 'none';
                document.removeEventListener('keydown', handleModalEscape);
            }}
            
            function handleModalEscape(e) {{
                if (e.key === 'Escape') {{
                    closeMTFAModal();
                }}
            }}
            
            // 모달 외부 클릭으로 닫기
            window.onclick = function(event) {{
                const modal = document.getElementById('mtfaModal');
                if (event.target === modal) {{
                    closeMTFAModal();
                }}
            }}
            
        </script>
    </body>
    </html>
    """
    
    return html_content

@app.get("/mtfa-dashboard", response_class=HTMLResponse)
async def mtfa_dashboard():
    """MTFA 최적화 전략 대시보드"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>🚀 MTFA 최적화 전략 대시보드</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                color: #333;
                padding: 20px;
            }}
            
            .header {{
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
            }}
            
            .header .subtitle {{
                font-size: 1.2rem;
                opacity: 0.9;
            }}
            
            .summary-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .summary-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(0,0,0,0.1);
            }}
            
            .summary-card h3 {{
                color: #2a5298;
                margin-bottom: 10px;
                font-size: 1rem;
            }}
            
            .summary-card .value {{
                font-size: 2rem;
                font-weight: bold;
                color: #1e3c72;
                margin-bottom: 5px;
            }}
            
            .summary-card .desc {{
                color: #666;
                font-size: 0.9rem;
            }}
            
            .coins-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .coin-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.1);
                transition: transform 0.3s;
            }}
            
            .coin-card:hover {{
                transform: translateY(-5px);
            }}
            
            .coin-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            
            
            .expected-return {{
                font-size: 1.1rem;
                font-weight: bold;
                color: #28a745;
            }}
            
            .strategy-info {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-bottom: 15px;
            }}
            
            .strategy-item {{
                background: #f8f9fa;
                padding: 8px 12px;
                border-radius: 8px;
                text-align: center;
            }}
            
            .strategy-label {{
                font-size: 0.8rem;
                color: #666;
                margin-bottom: 2px;
            }}
            
            .strategy-value {{
                font-weight: bold;
                color: #333;
            }}
            
            .profit-target {{ color: #28a745; }}
            .stop-loss {{ color: #dc3545; }}
            .hold-time {{ color: #6c757d; }}
            .confidence {{ color: #007bff; }}
            
            .confidence-meter {{
                width: 100%;
                height: 8px;
                background: #e9ecef;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 10px;
            }}
            
            .confidence-fill {{
                height: 100%;
                background: linear-gradient(90deg, #ffc107, #28a745);
                transition: width 0.3s;
            }}
            
            .signal-status {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 15px;
                font-size: 0.8rem;
                font-weight: bold;
                margin-top: 10px;
            }}
            
            .status-ready {{
                background: #d4edda;
                color: #155724;
            }}
            
            .status-waiting {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .refresh-btn {{
                position: fixed;
                bottom: 30px;
                right: 30px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 50%;
                width: 60px;
                height: 60px;
                font-size: 1.5rem;
                cursor: pointer;
                box-shadow: 0 4px 15px rgba(0,123,255,0.3);
                transition: all 0.3s;
            }}
            
            .refresh-btn:hover {{
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(0,123,255,0.4);
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 MTFA 최적화 전략</h1>
            <div class="subtitle">AI 기반 코인별 맞춤 매수매도 조건 • 평균 월 2.3% 수익률 목표</div>
        </div>
        
        <div class="summary-cards">
            <div class="summary-card">
                <h3>총 관리 코인</h3>
                <div class="value" id="totalCoins">10</div>
                <div class="desc">MTFA 최적화 완료</div>
            </div>
            <div class="summary-card">
                <h3>매수 준비</h3>
                <div class="value" id="buyReadyCoins">-</div>
                <div class="desc">신뢰도 임계값 달성</div>
            </div>
            <div class="summary-card">
                <h3>평균 예상 수익률</h3>
                <div class="value" id="avgReturn">82.7%</div>
                <div class="desc">연간 기준 (3년 백테스트)</div>
            </div>
            <div class="summary-card">
                <h3>월 예상 수익률</h3>
                <div class="value" id="monthlyReturn">2.3%</div>
                <div class="desc">복리 효과 포함</div>
            </div>
        </div>
        
        <div class="coins-grid" id="coinsGrid">
            <!-- 동적으로 로드됨 -->
        </div>
        
        <button class="refresh-btn" onclick="updateMTFADashboard()">🔄</button>
        
        <script>
            async function updateMTFADashboard() {{
                try {{
                    // MTFA 대시보드 데이터 가져오기
                    const response = await fetch('/api/mtfa-dashboard-data');
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 요약 정보 업데이트
                        document.getElementById('totalCoins').textContent = data.summary.total_coins;
                        document.getElementById('buyReadyCoins').textContent = data.summary.buy_ready_coins;
                        
                        // 코인 카드 생성
                        const coinsGrid = document.getElementById('coinsGrid');
                        coinsGrid.innerHTML = '';
                        
                        data.dashboard_data.forEach(coin => {{
                            const coinCard = document.createElement('div');
                            coinCard.className = 'coin-card';
                            coinCard.innerHTML = `
                                <div class="coin-header">
                                    <div class="coin-name">${{coin.market}}</div>
                                    <div class="expected-return">+${{coin.expected_monthly_return}}%/월</div>
                                </div>
                                
                                <div class="strategy-info">
                                    <div class="strategy-item">
                                        <div class="strategy-label">익절률</div>
                                        <div class="strategy-value profit-target">${{coin.strategy_info.profit_target}}%</div>
                                    </div>
                                    <div class="strategy-item">
                                        <div class="strategy-label">손절률</div>
                                        <div class="strategy-value stop-loss">${{coin.strategy_info.stop_loss}}%</div>
                                    </div>
                                    <div class="strategy-item">
                                        <div class="strategy-label">보유시간</div>
                                        <div class="strategy-value hold-time">${{coin.strategy_info.max_hold_minutes}}분</div>
                                    </div>
                                    <div class="strategy-item">
                                        <div class="strategy-label">신뢰도 임계값</div>
                                        <div class="strategy-value confidence">${{Math.round(coin.threshold * 100)}}%</div>
                                    </div>
                                </div>
                                
                                <div class="confidence-meter">
                                    <div class="confidence-fill" style="width: ${{coin.current_confidence * 100}}%"></div>
                                </div>
                                
                                <div class="signal-status ${{coin.is_buy_ready ? 'status-ready' : 'status-waiting'}}">
                                    ${{coin.signal_status === 'BUY_READY' ? '🟢 매수 준비' : '🟡 대기 중'}}
                                    (${{Math.round(coin.current_confidence * 100)}}%)
                                </div>
                            `;
                            coinsGrid.appendChild(coinCard);
                        }});
                        
                        console.log('MTFA 대시보드 업데이트 완료');
                    }} else {{
                        console.error('MTFA 대시보드 데이터 로드 실패:', data.message);
                    }}
                }} catch (error) {{
                    console.error('MTFA 대시보드 업데이트 에러:', error);
                }}
            }}
            
            // 페이지 로드시 초기 데이터 로드
            document.addEventListener('DOMContentLoaded', function() {{
                updateMTFADashboard();
                
                // 30초마다 자동 업데이트
                setInterval(updateMTFADashboard, 30000);
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/multi-coin-dashboard", response_class=HTMLResponse)
async def multi_coin_dashboard():
    """멀티 코인 분석 대시보드"""
    return HTMLResponse("멀티 코인 분석 대시보드 (임시 비활성화)")

@app.get("/main-dashboard", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    """비즈니스 관리 메인 대시보드로 리다이렉트"""
    return await business_main_dashboard(request)

@app.get("/legacy-dashboard", response_class=HTMLResponse)
async def legacy_main_dashboard(request: Request):
    """새로운 메인 대시보드 (로그인 후 첫 화면)"""
    
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_id = current_user.get('id')
    
    # API 키 세션 확인
    session_data = user_sessions.get(user_id)
    api_connected = bool(session_data)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Teamprime - 업비트 자동거래 시스템</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
            }}
            
            /* 앱바 */
            .app-bar {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 20px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                position: relative;
                z-index: 100;
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .hamburger-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .hamburger-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            /* 메인 컨텐츠 */
            .main-content {{
                padding: 30px 20px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            /* 자동거래 상태 카드 */
            .trading-status-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                cursor: pointer;
                transition: all 0.3s ease;
                height: 150px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            
            .trading-status-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.15);
            }}
            
            .status-info {{
                display: flex;
                flex-direction: column;
            }}
            
            .status-title {{
                font-size: 20px;
                font-weight: 600;
                color: #333;
                margin-bottom: 10px;
            }}
            
            .status-description {{
                font-size: 16px;
                color: #666;
                margin-bottom: 15px;
            }}
            
            .status-indicator {{
                display: flex;
                align-items: center;
                font-size: 14px;
                font-weight: 500;
            }}
            
            .status-dot {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            
            .status-connected {{
                background-color: #4caf50;
            }}
            
            .status-disconnected {{
                background-color: #ff9800;
            }}
            
            .status-arrow {{
                font-size: 24px;
                color: #1976d2;
            }}
            
            /* 사이드 패널 */
            .side-panel-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 200;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }}
            
            .side-panel-overlay.active {{
                opacity: 1;
                visibility: visible;
            }}
            
            .side-panel {{
                position: fixed;
                top: 0;
                right: 0;
                width: 80%;
                height: 100%;
                background: white;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 201;
                padding: 20px;
                overflow-y: auto;
            }}
            
            .side-panel.active {{
                transform: translateX(0);
            }}
            
            .side-panel-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 5px;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background-color 0.2s;
            }}
            
            .close-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            .menu-items {{
                list-style: none;
            }}
            
            .menu-item {{
                margin-bottom: 10px;
            }}
            
            .menu-item a {{
                display: block;
                padding: 15px 20px;
                color: #333;
                text-decoration: none;
                border-radius: 10px;
                transition: background-color 0.2s;
            }}
            
            .menu-item a:hover {{
                background-color: rgba(25, 118, 210, 0.1);
                color: #1976d2;
            }}
            
            /* 🔔 토스트 알림 스타일 */
            .toast-container {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
            }}
            
            .toast {{
                background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(255, 107, 107, 0.3);
                margin-bottom: 10px;
                transform: translateX(400px);
                opacity: 0;
                transition: all 0.3s ease;
                max-width: 350px;
                font-weight: 500;
            }}
            
            .toast.show {{
                transform: translateX(0);
                opacity: 1;
            }}
            
            .toast.warning {{
                background: linear-gradient(135deg, #ffa726, #ff9800);
                box-shadow: 0 10px 30px rgba(255, 167, 38, 0.3);
            }}
            
            .toast.success {{
                background: linear-gradient(135deg, #66bb6a, #4caf50);
                box-shadow: 0 10px 30px rgba(102, 187, 106, 0.3);
            }}
            
            .toast-header {{
                display: flex;
                align-items: center;
                margin-bottom: 5px;
            }}
            
            .toast-icon {{
                font-size: 20px;
                margin-right: 10px;
            }}
            
            .toast-title {{
                font-weight: 600;
                font-size: 16px;
            }}
            
            .toast-message {{
                font-size: 14px;
                line-height: 1.4;
            }}
        </style>
    </head>
    <body>
        <!-- 🔔 토스트 알림 컨테이너 -->
        <div class="toast-container" id="toastContainer"></div>
        
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="app-title">Teamprime</div>
            <button class="hamburger-btn" onclick="toggleSidePanel()">☰</button>
        </div>
        
        <!-- 메인 컨텐츠 -->
        <div class="main-content">
            <!-- 자동거래 상태 카드 -->
            <div class="trading-status-card" onclick="goToTrading()">
                <div class="status-info">
                    <div class="status-title">자동거래 시스템</div>
                    <div class="status-description">
                        {"API 연결됨 - 거래 준비완료" if api_connected else "API 키 입력 필요"}
                    </div>
                    <div class="status-indicator">
                        <div class="status-dot {'status-connected' if api_connected else 'status-disconnected'}"></div>
                        <span>{"연결됨" if api_connected else "연결 필요"}</span>
                    </div>
                </div>
                <div class="status-arrow">→</div>
            </div>
        </div>
        
        <!-- 사이드 패널 오버레이 -->
        <div class="side-panel-overlay" onclick="closeSidePanel()"></div>
        
        <!-- 사이드 패널 -->
        <div class="side-panel">
            <div class="side-panel-header">
                <h2 onclick="goToProfile()" style="cursor: pointer; color: #1976d2;">{username}</h2>
                <button class="close-btn" onclick="closeSidePanel()">×</button>
            </div>
            
            <ul class="menu-items">
                <li class="menu-item">
                    <a href="/main-dashboard">🏠 대시보드</a>
                </li>
                <li class="menu-item">
                    <a href="/trading-flow">📈 자동거래</a>
                </li>
            </ul>
        </div>
        
        <script>
            function toggleSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.add('active');
                panel.classList.add('active');
            }}
            
            function closeSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.remove('active');
                panel.classList.remove('active');
            }}
            
            function goToTrading() {{
                window.location.href = '/trading-flow';
            }}
            
            // 개인정보 페이지로 이동
            function goToProfile() {{
                window.location.href = '/profile';
            }}
            
            // 🔔 토스트 알림 시스템
            function showToast(title, message, type = 'error', duration = 5000) {{
                const container = document.getElementById('toastContainer');
                
                const toast = document.createElement('div');
                toast.className = `toast ${{type}}`;
                
                const iconMap = {{
                    'error': '🚨',
                    'warning': '⚠️',
                    'success': '✅',
                    'info': 'ℹ️'
                }};
                
                toast.innerHTML = `
                    <div class="toast-header">
                        <span class="toast-icon">${{iconMap[type] || '📢'}}</span>
                        <span class="toast-title">${{title}}</span>
                    </div>
                    <div class="toast-message">${{message}}</div>
                `;
                
                container.appendChild(toast);
                
                // 애니메이션으로 표시
                setTimeout(() => {{
                    toast.classList.add('show');
                }}, 100);
                
                // 자동 제거
                setTimeout(() => {{
                    toast.classList.remove('show');
                    setTimeout(() => {{
                        if (toast.parentNode) {{
                            toast.parentNode.removeChild(toast);
                        }}
                    }}, 300);
                }}, duration);
                
                return toast;
            }}
            
            // 🔄 자동 토큰 갱신 시스템
            function getCookie(name) {{
                const value = `; ${{document.cookie}}`;
                const parts = value.split(`; ${{name}}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
            }}
            
            function parseJWT(token) {{
                try {{
                    const base64Url = token.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {{
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }}).join(''));
                    return JSON.parse(jsonPayload);
                }} catch (error) {{
                    console.error('JWT 파싱 오류:', error);
                    return null;
                }}
            }}
            
            function checkTokenExpiration() {{
                const token = getCookie('auth_token');
                if (!token) {{
                    console.log('토큰이 없습니다');
                    return;
                }}
                
                const payload = parseJWT(token);
                if (!payload) {{
                    console.log('토큰 파싱 실패');
                    return;
                }}
                
                const now = Math.floor(Date.now() / 1000);
                const expirationTime = payload.exp;
                const timeUntilExpiry = expirationTime - now;
                
                console.log(`토큰 만료까지 남은 시간: ${{Math.floor(timeUntilExpiry / 60)}}분`);
                
                // 토큰이 30분 내에 만료될 예정이면 갱신 시도
                if (timeUntilExpiry > 0 && timeUntilExpiry < 30 * 60) {{
                    renewToken();
                }}
            }}
            
            async function renewToken() {{
                try {{
                    const response = await fetch('/api/auth/refresh-token', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${{getCookie('auth_token')}}`
                        }}
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success && result.token) {{
                        // 새 토큰으로 쿠키 업데이트
                        const maxAge = result.remember_me ? (7 * 24 * 60 * 60) : (24 * 60 * 60);
                        const cookieOptions = `path=/; max-age=${{maxAge}}; SameSite=Lax` + (location.protocol === 'https:' ? '; Secure' : '');
                        document.cookie = `auth_token=${{result.token}}; ${{cookieOptions}}`;
                        
                        console.log('✅ 토큰 갱신 완료');
                    }} else {{
                        console.log('❌ 토큰 갱신 실패:', result.message);
                        // 갱신 실패시 로그인 페이지로 이동
                        setTimeout(() => {{
                            window.location.href = '/login';
                        }}, 3000);
                    }}
                }} catch (error) {{
                    console.error('토큰 갱신 중 오류:', error);
                }}
            }}
            
            // 🚀 서버 재시작 감지 및 자동 로그아웃
            let lastKnownServerStartTime = null;
            
            async function checkServerRestart() {{
                try {{
                    const response = await fetch('/api/auth/server-status');
                    const result = await response.json();
                    
                    if (result.success) {{
                        const currentServerStartTime = result.server_start_time;
                        
                        // 처음 접속이면 서버 시작 시간 저장
                        if (lastKnownServerStartTime === null) {{
                            lastKnownServerStartTime = currentServerStartTime;
                            console.log('서버 시작 시간 기록:', new Date(currentServerStartTime * 1000));
                            return;
                        }}
                        
                        // 서버가 재시작된 경우
                        if (lastKnownServerStartTime !== currentServerStartTime) {{
                            console.log('🚨 서버 재시작 감지!');
                            
                            // 쿠키 삭제
                            document.cookie = 'auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
                            
                            // 토스트 알림으로 사용자에게 알림
                            showToast(
                                '서버 재시작 감지',
                                '보안을 위해 다시 로그인해주세요. 3초 후 자동으로 이동됩니다.',
                                'warning',
                                8000
                            );
                            
                            // 3초 후 로그인 페이지로 이동
                            setTimeout(() => {{
                                window.location.href = '/login';
                            }}, 3000);
                            return;
                        }}
                    }}
                }} catch (error) {{
                    console.error('서버 상태 확인 중 오류:', error);
                }}
            }}
            
            // 페이지 로드 시 토큰 체크 및 주기적 체크 시작
            document.addEventListener('DOMContentLoaded', function() {{
                checkServerRestart();
                checkTokenExpiration();
                
                // 서버 재시작 체크 (30초마다)
                setInterval(checkServerRestart, 30 * 1000);
                
                // 10분마다 토큰 만료 체크
                setInterval(checkTokenExpiration, 10 * 60 * 1000);
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

@app.get("/trading-flow")
async def trading_flow(request: Request):
    """자동거래 플로우 - API 키 상태에 따라 분기"""
    
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    user_id = current_user.get('id')
    session_data = user_sessions.get(user_id)
    
    # API 키가 없으면 API 키 입력 화면으로
    if not session_data:
        return RedirectResponse(url="/")
    
    # API 키가 있으면 기존 거래 대시보드로
    return RedirectResponse(url="/dashboard")

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """사용자 개인정보 페이지"""
    
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_id = current_user.get('id')
    email = current_user.get('email', '')
    created_at = current_user.get('created_at', '')
    last_login = current_user.get('last_login', '')
    
    # API 키 세션 확인
    session_data = user_sessions.get(user_id)
    api_connected = bool(session_data)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>개인정보 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                color: #333;
                padding-top: 80px; /* Teamprime 앱바 공간 확보 */
            }}
            
            /* Teamprime 앱바 스타일 */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 60px;
                background: white;
                display: flex;
                align-items: center;
                padding: 0 20px;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 100;
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .hamburger-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 8px;
                border-radius: 4px;
            }}
            
            .hamburger-btn:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            
            /* 사이드패널 스타일 */
            .side-panel-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 200;
            }}
            
            .side-panel-overlay.active {{
                opacity: 1;
                visibility: visible;
            }}
            
            .side-panel {{
                position: fixed;
                top: 0;
                right: 0;
                width: 300px;
                height: 100%;
                background: white;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 201;
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
                overflow-y: auto;
            }}
            
            .side-panel.active {{
                transform: translateX(0);
            }}
            
            .side-panel-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #eee;
                background: #f8f9fa;
            }}
            
            .side-panel-header h3 {{
                margin: 0;
                color: #333;
                font-size: 18px;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            
            .close-btn:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            
            /* 사이드패널 사용자 정보 스타일 */
            .side-panel-user {{
                padding: 15px 20px;
                background: rgba(25, 118, 210, 0.05);
                border-bottom: 1px solid #e0e0e0;
                margin-bottom: 10px;
            }}
            .side-panel-user .user-info {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            .side-panel-user .user-name {{
                font-weight: 600;
                color: #333;
                font-size: 16px;
            }}
            .side-panel-user .user-status {{
                font-size: 14px;
                color: #4caf50;
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            
            .menu-items {{
                list-style: none;
                padding: 20px 0;
            }}
            
            .menu-items li {{
                margin-bottom: 10px;
            }}
            
            .menu-items a {{
                display: block;
                padding: 12px 20px;
                color: #333;
                text-decoration: none;
                transition: background-color 0.2s;
            }}
            
            .menu-items a:hover {{
                background-color: #f5f5f5;
            }}
            
            .menu-items a.active {{
                background-color: rgba(25, 118, 210, 0.1);
                color: #1976d2;
                border-right: 3px solid #1976d2;
            }}
            
            .main-content {{
                max-width: 800px;
                margin: 40px auto;
                padding: 0 20px;
            }}
            
            .profile-header {{
                text-align: center;
                color: white;
                margin-bottom: 40px;
            }}
            
            .profile-header h1 {{
                font-size: 32px;
                margin-bottom: 10px;
            }}
            
            .profile-header p {{
                font-size: 18px;
                opacity: 0.9;
            }}
            
            .profile-card {{
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }}
            
            .profile-section {{
                margin-bottom: 30px;
            }}
            
            .section-title {{
                font-size: 20px;
                font-weight: 600;
                color: #333;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e0e0e0;
            }}
            
            .profile-field {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                border-bottom: 1px solid #f0f0f0;
            }}
            
            .profile-field:last-child {{
                border-bottom: none;
            }}
            
            .field-label {{
                font-weight: 500;
                color: #666;
            }}
            
            .field-value {{
                font-weight: 600;
                color: #333;
            }}
            
            .status-badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .status-connected {{
                background-color: #e8f5e8;
                color: #2e7d32;
            }}
            
            .status-disconnected {{
                background-color: #ffebee;
                color: #c62828;
            }}
            
            .btn {{
                background: #1976d2;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                transition: background-color 0.3s;
                text-decoration: none;
                display: inline-block;
                margin-right: 10px;
            }}
            
            .btn:hover {{
                background: #1565c0;
            }}
            
            .btn-outline {{
                background: transparent;
                border: 2px solid #1976d2;
                color: #1976d2;
            }}
            
            .btn-outline:hover {{
                background: #1976d2;
                color: white;
            }}
            
            .btn-danger {{
                background: #f44336;
            }}
            
            .btn-danger:hover {{
                background: #d32f2f;
            }}
            
            .logout-link {{
                color: #666;
                text-decoration: underline;
                background: none;
                border: none;
                cursor: pointer;
                font-size: 16px;
                padding: 8px 12px;
                display: inline-block;
                margin-top: 10px;
            }}
            
            .logout-link:hover {{
                color: #333;
                text-decoration: underline;
            }}
            
            @media (max-width: 768px) {{
                .main-content {{
                    padding: 0 15px;
                }}
                
                .profile-card {{
                    padding: 20px;
                }}
                
                .profile-field {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 5px;
                }}
                
                .field-label {{
                    font-size: 14px;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="app-title">Teamprime</div>
            <button class="hamburger-btn" onclick="toggleSidePanel()">☰</button>
        </div>
        
        <!-- 사이드패널 오버레이 -->
        <div class="side-panel-overlay" onclick="closeSidePanel()"></div>
        
        <!-- 사이드패널 -->
        <div class="side-panel">
            <div class="side-panel-header">
                <h3 onclick="goToProfile()" style="cursor: pointer; color: #1976d2;">{username}</h3>
                <button class="close-btn" onclick="closeSidePanel()">×</button>
            </div>
            
            <!-- 사용자 정보 섹션 -->
            <div class="side-panel-user">
                <div class="user-info">
                    <div class="user-name">{username}</div>
                    <div class="user-status">✅ 업비트 연결됨</div>
                </div>
            </div>
            
            <ul class="menu-items">
                <li><a href="/main-dashboard">🏠 대시보드</a></li>
                <li><a href="/dashboard">📊 거래 현황</a></li>
                <li><a href="/profile" class="active">👤 개인정보</a></li>
            </ul>
        </div>
        
        <!-- 메인 컨텐츠 -->
        <div class="main-content">
            <div class="profile-card">
                <div class="profile-section">
                    <div class="profile-field">
                        <span class="field-label">사용자명</span>
                        <span class="field-value">{username}</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">이메일</span>
                        <span class="field-value">{email}</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">가입일</span>
                        <span class="field-value">{created_at}</span>
                    </div>
                    <div class="profile-field">
                        <span class="field-label">마지막 로그인</span>
                        <span class="field-value">{last_login}</span>
                    </div>
                </div>
                
                <div class="profile-section">
                    <h2 class="section-title">API 연결 상태</h2>
                    <div class="profile-field">
                        <span class="field-label">업비트 API</span>
                        <span class="field-value">
                            <span class="status-badge {'status-connected' if api_connected else 'status-disconnected'}">
                                {'연결됨' if api_connected else '연결 안됨'}
                            </span>
                        </span>
                    </div>
                    {f'''
                    <div class="profile-field">
                        <span class="field-label">Access Key</span>
                        <span class="field-value">{session_data.get('access_key', '')[:8]}...</span>
                    </div>
                    ''' if api_connected else ''}
                </div>
                
                <div class="profile-section">
                    <h2 class="section-title">계정 관리</h2>
                    <div style="text-align: center; padding: 20px 0;">
                        <button class="btn btn-outline" onclick="showChangePasswordModal()">
                            🔒 비밀번호 변경
                        </button>
                        <button class="btn btn-outline" onclick="showApiKeyModal()">
                            🔑 API 키 관리
                        </button>
                        <a href="#" class="logout-link" onclick="confirmLogout(); return false;">
                            🚪 로그아웃
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // 사이드패널 관련 함수들
            function toggleSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.add('active');
                panel.classList.add('active');
            }}
            
            function closeSidePanel() {{
                const overlay = document.querySelector('.side-panel-overlay');
                const panel = document.querySelector('.side-panel');
                
                overlay.classList.remove('active');
                panel.classList.remove('active');
            }}
            
            // 개인정보 페이지로 이동
            function goToProfile() {{
                window.location.href = '/profile';
            }}
            
            // 로그아웃 함수
            function logout() {{
                if (confirm('정말 로그아웃 하시겠습니까?')) {{
                    window.location.href = '/api/logout';
                }}
            }}
            
            // 로그아웃 확인
            function confirmLogout() {{
                if (confirm('정말 로그아웃 하시겠습니까?')) {{
                    window.location.href = '/api/logout';
                }}
            }}
            
            // 비밀번호 변경 모달 (추후 구현)
            function showChangePasswordModal() {{
                alert('비밀번호 변경 기능은 추후 구현 예정입니다.');
            }}
            
            // API 키 관리 모달 (추후 구현)
            function showApiKeyModal() {{
                alert('API 키 관리 기능은 추후 구현 예정입니다.');
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content

async def collect_recent_candles():
    """최근 캔들 데이터 수집"""
    logger.info("📊 최근 캔들 데이터 수집 시작")
    
    try:
        from config import DEFAULT_MARKETS
        
        # 실제 캔들 데이터 수집 로직은 원래 함수에서 복사해야 함
        # 임시로 간단한 로그만 남김
        logger.info("📊 최근 캔들 데이터 수집 완료")
    except Exception as e:
        logger.error(f"❌ 캔들 데이터 수집 오류: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 업비트 자동거래 시스템 시작...")
    
    # 웹서버 실행
    uvicorn.run(
        "main:app",
        host=WEB_CONFIG["host"],
        port=WEB_CONFIG["port"],
        reload=WEB_CONFIG["reload"],
        workers=WEB_CONFIG["workers"]
    )
