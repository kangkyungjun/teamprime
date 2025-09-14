"""
업비트 자동거래 시스템 - 모듈화된 메인 애플리케이션
- 운영 효율성을 위한 완전 모듈화 구조
- 자동 라우터 등록 및 생명주기 관리
- 환경별 설정 지원
- 테스트 용이성 향상
"""

import logging
import os
from contextlib import asynccontextmanager

# 설정 관리자를 가장 먼저 초기화
from core.config_manager import config_manager
from core.app_factory import create_application

# 로거 설정 (config_manager 초기화 후)
logger = logging.getLogger(__name__)

def main():
    """메인 애플리케이션 진입점"""

    # 환경 감지
    environment = os.getenv('ENVIRONMENT', 'development').lower()

    logger.info(f"🚀 업비트 자동거래 시스템 v2.0 시작 - 환경: {environment}")
    logger.info(f"📊 설정 요약:")

    config_summary = config_manager.get_config_summary()
    for key, value in config_summary.items():
        logger.info(f"   {key}: {value}")

    # 애플리케이션 생성
    app = create_application(environment)

    logger.info("✅ 애플리케이션 초기화 완료")

    return app

# FastAPI 애플리케이션 인스턴스 생성
app = main()

# 개발 서버 실행을 위한 진입점
if __name__ == "__main__":
    import uvicorn

    # 환경별 설정
    if config_manager.is_production():
        # 운영 환경 설정
        uvicorn.run(
            "main_modular:app",
            host=config_manager.webserver.host,
            port=config_manager.webserver.port,
            workers=config_manager.webserver.workers,
            reload=False,
            log_level="info",
            access_log=True
        )
    else:
        # 개발 환경 설정
        uvicorn.run(
            "main_modular:app",
            host=config_manager.webserver.host,
            port=config_manager.webserver.port,
            reload=config_manager.webserver.reload,
            log_level="debug" if config_manager.system.debug else "info",
            access_log=True
        )