"""
업비트 자동거래 시스템 - 메인 애플리케이션 (리팩토링됨)
모듈화된 아키텍처로 재구성 - 클린 버전
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
from core.views import main_views_router, dashboard_views_router, auth_views_router, task_views_router, analytics_views_router, reports_views_router
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
        
        # 24시간 연속 거래를 위한 슬립 방지 시작
        if start_sleep_prevention():
            logger.info("🛡️ 24시간 연속 거래를 위한 슬립 방지 활성화")
        
        # SQLite 데이터베이스 초기화
        try:
            await init_db()
            logger.info("✅ SQLite 데이터베이스 초기화 완료")
        except Exception as e:
            logger.error(f"❌ SQLite 데이터베이스 초기화 실패: {str(e)}")
        
        # MySQL 데이터베이스 연결 테스트 및 마이그레이션
        try:
            if await test_mysql_connection():
                await run_migration()
                logger.info("✅ MySQL 인증 데이터베이스 초기화 완료")
            else:
                logger.error("❌ MySQL 연결 실패")
        except Exception as e:
            logger.error(f"❌ MySQL 초기화 오류: {str(e)}")
        
        # 자동 최적화 스케줄러 시작 (임시 비활성화)
        try:
            # auto_scheduler.start()
            logger.info("✅ 자동 최적화 스케줄러 시작 (비활성화됨)")
        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {str(e)}")
        
        # 모니터링 및 알림 서비스 시작 (임시 비활성화)
        try:
            # from core.services.monitoring_service import monitoring_service
            # from core.services.notification_service import notification_service
            
            # await monitoring_service.start_monitoring()
            # await notification_service.notify_system_start()
            logger.info("📊 모니터링 및 알림 서비스 시작 (비활성화됨)")
            logger.info(f"📊 모니터링 대상 마켓: {DEFAULT_MARKETS}")
            logger.info(f"🌐 웹서버 포트: {WEB_CONFIG['port']}")
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 시작 실패: {str(e)}")
        
        yield
        
        # 시스템 종료 알림 (임시 비활성화)
        try:
            # from core.services.notification_service import notification_service
            # from core.services.monitoring_service import monitoring_service
            
            # await notification_service.notify_system_stop()
            # await monitoring_service.stop_monitoring()
            logger.info("📊 모니터링 서비스 종료 (비활성화됨)")
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 종료 실패: {str(e)}")
        
        stop_sleep_prevention()
        # auto_scheduler.shutdown()  # 비활성화됨
        
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
app.include_router(resilience_router, prefix="/api/resilience")
app.include_router(monitoring_router, prefix="/api/monitoring")
app.include_router(auth_router)
app.include_router(ux_router, prefix="/api/ux")
app.include_router(account_router, prefix="/api/account")
app.include_router(trading_history_router, prefix="/api/trading-history")
app.include_router(business_router)
app.include_router(users_router)

# 분석 API 라우터 추가
from core.api.analytics import router as analytics_router
from core.api.reports import router as reports_router
app.include_router(analytics_router)
app.include_router(reports_router)

# 뷰 라우터 등록
app.include_router(main_views_router)  # 메인 뷰 (/, /api-login, /profile 등)
app.include_router(dashboard_views_router)  # 대시보드 뷰
app.include_router(auth_views_router)  # 인증 관련 뷰
app.include_router(task_views_router)  # 업무 관리 뷰
app.include_router(analytics_views_router)  # 분석 뷰
app.include_router(reports_views_router)  # 리포트 뷰

# 실시간 API 라우터 추가
from core.api.realtime import router as realtime_router
from core.api.mtfa import router as mtfa_router
app.include_router(realtime_router, prefix="/api/realtime")
app.include_router(mtfa_router)

@app.post("/api/collect-recent-data")
async def collect_recent_data_endpoint():
    """최근 캔들 데이터 수집 API"""
    try:
        from core.services.signal_analyzer import collect_recent_candles
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
        import uuid
        import hashlib
        from urllib.parse import urlencode, unquote
        
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
                    logger.info("✅ [MAIN] API 키 검증 성공")
                    
                    # 세션에 API 키 임시 저장 (보안 강화)
                    user_id = current_user.get("id")
                    user_sessions[user_id] = {
                        "access_key": access_key,
                        "secret_key": secret_key,
                        "account_info": account_data,
                        "authenticated_at": datetime.now().isoformat()
                    }
                    
                    # 세션 관리자에도 등록
                    from core.session.session_manager import session_manager
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
                    logger.warning("❌ [MAIN] API 키 인증 실패 (잘못된 키)")
                    return {"success": False, "message": "API 키가 올바르지 않습니다"}
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [MAIN] API 검증 실패 ({response.status}): {error_text}")
                    return {"success": False, "message": f"API 키 검증에 실패했습니다 (상태: {response.status})"}
                    
    except Exception as e:
        logger.error(f"❌ API 키 인증 오류: {str(e)}")
        return {"success": False, "message": f"API 키 검증 중 오류가 발생했습니다: {str(e)}"}

# 메인 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=WEB_CONFIG["port"],
        reload=False,  # 프로덕션에서는 False
        log_level="info"
    )