"""
📱 Teamprime Mobile API Server

⚠️ 중요 안전 규칙:
1. 이 서버는 기존 웹 시스템 (포트 8001)과 완전히 분리되어 있습니다.
2. 기존 core/ 모듈의 데이터는 읽기 전용으로만 접근합니다.
3. 기존 거래 엔진이나 데이터베이스를 수정하지 않습니다.
4. 독립된 포트 8002에서 실행됩니다.

🚀 Mobile API Server Features:
- JWT 기반 인증 시스템
- 실시간 거래 데이터 조회
- 포트폴리오 관리 API
- WebSocket 실시간 스트리밍
- Flutter 앱 최적화된 응답 형식
"""

import uvicorn
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# 모바일 API 모듈
from mobile import MOBILE_API_VERSION, MOBILE_API_PORT, SAFE_MODE
from mobile.api import mobile_routers
from mobile.services import data_adapter, websocket_manager
from mobile.models.mobile_response import MobileErrorResponse, MobileHealthResponse, ErrorCode

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시 초기화
    logger.info("🚀 모바일 API 서버 시작 중...")
    logger.info(f"📱 안전 모드: {'활성화' if SAFE_MODE else '비활성화'}")
    logger.info(f"🔗 기존 시스템 호환성: 읽기 전용 모드")
    
    # WebSocket 매니저 시작
    try:
        await websocket_manager.start()
        logger.info("🔌 WebSocket 매니저 시작 완료")
    except Exception as e:
        logger.error(f"❌ WebSocket 매니저 시작 실패: {e}")
    
    # 데이터 어댑터 상태 확인
    try:
        status = data_adapter.get_system_status()
        logger.info(f"📊 데이터 어댑터 상태: {'정상' if status.get('system_running') else '오류'}")
    except Exception as e:
        logger.error(f"❌ 데이터 어댑터 상태 확인 실패: {e}")
    
    logger.info(f"✅ 모바일 API 서버 시작 완료 (포트 {MOBILE_API_PORT})")
    
    yield
    
    # 종료 시 정리
    logger.info("🛑 모바일 API 서버 종료 중...")
    try:
        await websocket_manager.stop()
        logger.info("🔌 WebSocket 매니저 정리 완료")
    except Exception as e:
        logger.error(f"❌ WebSocket 매니저 정리 실패: {e}")
    
    logger.info("✅ 모바일 API 서버 종료 완료")

# FastAPI 앱 생성
app = FastAPI(
    title="Teamprime Mobile API",
    description="🚀 Teamprime 암호화폐 거래 시스템 모바일 API",
    version=MOBILE_API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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

# 신뢰할 수 있는 호스트 설정
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # 개발 환경용, 프로덕션에서는 구체적 도메인 설정
)

# 전역 예외 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    error_response = MobileErrorResponse(
        message=exc.detail,
        error_code=ErrorCode.UNKNOWN_ERROR,
        error_details=f"HTTP {exc.status_code} 오류가 발생했습니다",
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"❌ 처리되지 않은 예외: {exc}")
    
    error_response = MobileErrorResponse(
        message="서버 내부 오류가 발생했습니다",
        error_code=ErrorCode.UNKNOWN_ERROR,
        error_details=str(exc) if logger.level <= logging.DEBUG else None,
        debug_info={"exception_type": type(exc).__name__} if logger.level <= logging.DEBUG else None,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )

# 요청 로깅 미들웨어
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """요청 로깅 및 성능 측정"""
    start_time = datetime.utcnow()
    
    # 요청 로깅
    logger.info(f"📱 {request.method} {request.url.path} - {request.client.host}")
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # 응답 로깅
    logger.info(f"✅ {request.method} {request.url.path} - {response.status_code} ({process_time:.1f}ms)")
    
    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 기본 라우트들
@app.get("/")
async def root():
    """모바일 API 루트 엔드포인트"""
    return {
        "service": "Teamprime Mobile API",
        "version": MOBILE_API_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "safe_mode": SAFE_MODE,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """모바일 API 서버 헬스 체크"""
    try:
        # 데이터 어댑터 상태 확인
        data_status = data_adapter.get_system_status()
        
        # WebSocket 매니저 상태 확인
        websocket_status = {
            "healthy": websocket_manager.is_running,
            "status": "active" if websocket_manager.is_running else "inactive",
            "connections": websocket_manager.get_connection_count()
        }
        
        # 기존 시스템 연결 확인
        core_system_status = {
            "healthy": data_status.get("system_running", False),
            "status": "connected" if data_status.get("system_running") else "disconnected",
            "trading_active": data_status.get("trading_active", False)
        }
        
        components = {
            "mobile_api": {
                "healthy": True,
                "status": "running",
                "port": MOBILE_API_PORT
            },
            "data_adapter": {
                "healthy": True,
                "status": "active",
                "safe_mode": SAFE_MODE
            },
            "websocket_manager": websocket_status,
            "core_system": core_system_status
        }
        
        performance = {
            "memory_usage": data_status.get("memory_usage", 0.0),
            "uptime": data_status.get("uptime", "알 수 없음"),
            "response_time": 0.0  # 실제 측정값으로 교체
        }
        
        health_response = MobileHealthResponse(
            status="success",
            components=components,
            performance=performance
        )
        
        return health_response
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {e}")
        
        error_response = MobileErrorResponse(
            message="헬스 체크 중 오류가 발생했습니다",
            error_code=ErrorCode.SYSTEM_DATABASE_ERROR,
            error_details=str(e)
        )
        
        return JSONResponse(
            status_code=503,
            content=error_response.dict()
        )

@app.get("/version")
async def version_info():
    """모바일 API 버전 정보"""
    return {
        "api_version": MOBILE_API_VERSION,
        "app_name": "Teamprime Mobile API",
        "safe_mode": SAFE_MODE,
        "compatible_core_version": "2.1",
        "build_time": datetime.utcnow().isoformat()
    }

# 모바일 API 라우터 등록
for router in mobile_routers:
    app.include_router(router, prefix="/api/v1")
    logger.info(f"🔗 라우터 등록: {router.prefix if hasattr(router, 'prefix') else 'API Router'}")

# 개발 환경 WebSocket 테스트 엔드포인트
@app.websocket("/ws/test")
async def websocket_test_endpoint(websocket):
    """WebSocket 연결 테스트용 엔드포인트"""
    await websocket_manager.handle_connection(websocket, "test")

def run_mobile_server():
    """모바일 API 서버 실행"""
    logger.info(f"🚀 모바일 API 서버 시작 - 포트 {MOBILE_API_PORT}")
    logger.info(f"📱 안전 모드: {'활성화' if SAFE_MODE else '비활성화'}")
    logger.info("🔗 기존 시스템과 완전히 분리된 독립 서버입니다")
    
    uvicorn.run(
        "mobile_main:app",
        host="0.0.0.0",
        port=MOBILE_API_PORT,
        log_level="info",
        reload=False,  # 프로덕션에서는 False
        access_log=True
    )

if __name__ == "__main__":
    # 직접 실행시 서버 시작
    run_mobile_server()