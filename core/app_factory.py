"""
FastAPI 애플리케이션 팩토리
- 애플리케이션 생성 및 설정을 모듈화
- 환경별 다른 설정 적용 가능
- 테스트 용이성 향상
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config_manager import config_manager
from core.router_registry import router_registry
from core.app_lifecycle import lifespan_manager

logger = logging.getLogger(__name__)

def setup_logging():
    """로깅 설정"""
    handlers = []

    # 파일 핸들러
    if config_manager.logging.file_path:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config_manager.logging.file_path,
            maxBytes=config_manager.logging.max_bytes,
            backupCount=config_manager.logging.backup_count
        )
        handlers.append(file_handler)

    # 콘솔 핸들러
    if config_manager.logging.console_enabled:
        handlers.append(logging.StreamHandler())

    # 로깅 기본 설정
    logging.basicConfig(
        level=getattr(logging, config_manager.logging.level),
        format=config_manager.logging.format,
        handlers=handlers,
        force=True  # 기존 설정 덮어쓰기
    )

def setup_cors_middleware(app: FastAPI):
    """CORS 미들웨어 설정"""
    if not config_manager.webserver.cors_enabled:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config_manager.webserver.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"✅ CORS 미들웨어 설정 완료 - Origins: {len(config_manager.webserver.cors_origins)}개")

def setup_exception_handlers(app: FastAPI):
    """예외 처리기 설정"""

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc: Exception):
        logger.error(f"Internal server error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"}
        )

def add_custom_endpoints(app: FastAPI):
    """커스텀 엔드포인트 추가"""

    @app.get("/health")
    async def health_check():
        """헬스 체크 엔드포인트"""
        return {
            "status": "healthy",
            "environment": config_manager.system.environment,
            "version": "2.0.0"
        }

    @app.get("/config")
    async def get_config_summary():
        """설정 요약 정보"""
        return config_manager.get_config_summary()

    @app.post("/config/validate")
    async def validate_config():
        """설정 유효성 검증"""
        return config_manager.validate_config()

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

    # API 키 인증 엔드포인트 추가 (auth 모듈로 이전됨)
    from core.api.auth import api_key_authentication_endpoint
    app.add_api_route("/api/auth-login", api_key_authentication_endpoint, methods=["POST"])

def create_application(environment: str = None) -> FastAPI:
    """
    FastAPI 애플리케이션 생성 팩토리

    Args:
        environment: 환경 설정 (development, production, testing)

    Returns:
        FastAPI: 구성된 FastAPI 애플리케이션 인스턴스
    """

    # 환경별 설정 오버라이드
    if environment:
        config_manager.system.environment = environment
        config_manager.system.debug = environment in ["development", "testing"]

    # 로깅 설정
    setup_logging()

    logger.info(f"🚀 애플리케이션 생성 시작 - 환경: {config_manager.system.environment}")

    # 설정 검증
    validation_result = config_manager.validate_config()
    if not validation_result["valid"]:
        logger.error(f"❌ 설정 검증 실패: {validation_result['issues']}")
        raise ValueError(f"Invalid configuration: {validation_result['issues']}")

    if validation_result["warnings"]:
        logger.warning(f"⚠️ 설정 경고: {validation_result['warnings']}")

    # FastAPI 앱 생성
    app = FastAPI(
        title="Upbit Cryptocurrency Trading System",
        description="모듈화된 업비트 자동거래 시스템 - v2.0",
        version="2.0.0",
        debug=config_manager.system.debug,
        lifespan=lifespan_manager
    )

    # 미들웨어 설정
    setup_cors_middleware(app)

    # 예외 처리기 설정
    setup_exception_handlers(app)

    # 라우터 등록
    registration_results = router_registry.register_all_routers(app)

    # 커스텀 엔드포인트 추가
    add_custom_endpoints(app)

    logger.info("✅ 애플리케이션 생성 완료")

    # 등록 결과 로그
    total_api_routers = len(registration_results["api"])
    successful_api_routers = sum(registration_results["api"].values())
    total_view_routers = len(registration_results["views"])
    successful_view_routers = sum(registration_results["views"].values())

    logger.info(f"📊 라우터 등록 완료 - API: {successful_api_routers}/{total_api_routers}, Views: {successful_view_routers}/{total_view_routers}")

    return app

def create_development_app() -> FastAPI:
    """개발환경용 애플리케이션 생성"""
    return create_application("development")

def create_production_app() -> FastAPI:
    """운영환경용 애플리케이션 생성"""
    return create_application("production")

def create_testing_app() -> FastAPI:
    """테스트환경용 애플리케이션 생성"""
    return create_application("testing")