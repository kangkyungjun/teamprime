"""
애플리케이션 생명주기 관리 모듈
- 시작/종료 시 필요한 초기화/정리 작업을 모듈화
- main.py의 복잡성 감소 및 테스트 용이성 향상
"""

import logging
import subprocess
import os
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime

from core.database import run_migration, test_mysql_connection
from core.services import auto_scheduler
from core.session import session_manager
from database import init_db
from config import DEFAULT_MARKETS, WEB_CONFIG

logger = logging.getLogger(__name__)

class SystemManager:
    """시스템 레벨 서비스 관리"""

    def __init__(self):
        self.caffeinate_process: Optional[subprocess.Popen] = None

    def start_sleep_prevention(self) -> bool:
        """시스템 슬립 방지 시작"""
        try:
            self.caffeinate_process = subprocess.Popen(
                ['caffeinate', '-d', '-i', '-s'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"🛡️ 슬립 방지 활성화 (PID: {self.caffeinate_process.pid})")
            return True
        except Exception as e:
            logger.error(f"⚠️ 슬립 방지 실패: {str(e)}")
            return False

    def stop_sleep_prevention(self):
        """시스템 슬립 방지 중지"""
        if not self.caffeinate_process:
            return

        try:
            if self.caffeinate_process.poll() is None:
                self.caffeinate_process.terminate()
                self.caffeinate_process.wait(timeout=5)
                logger.info("🛡️ 슬립 방지 해제")
        except Exception as e:
            logger.error(f"⚠️ 슬립 방지 해제 실패: {str(e)}")
            try:
                if self.caffeinate_process:
                    self.caffeinate_process.kill()
            except:
                pass

    def optimize_process_priority(self):
        """프로세스 우선순위 최적화"""
        try:
            os.nice(-5)  # 우선순위 상승 (음수일수록 높은 우선순위)
            logger.info("⚡ 프로세스 우선순위 상승 완료")
            return True
        except Exception as e:
            logger.warning(f"⚠️ 프로세스 우선순위 설정 실패: {str(e)} (권한 부족)")
            return False

class DatabaseManager:
    """데이터베이스 초기화 및 관리"""

    @staticmethod
    async def initialize_databases():
        """SQLite 및 MySQL 데이터베이스 초기화"""
        results = {"sqlite": False, "mysql": False}

        # SQLite 초기화
        try:
            await init_db()
            logger.info("✅ SQLite 데이터베이스 초기화 완료")
            results["sqlite"] = True
        except Exception as e:
            logger.error(f"❌ SQLite 데이터베이스 초기화 실패: {str(e)}")

        # MySQL 초기화 및 마이그레이션
        try:
            if await test_mysql_connection():
                await run_migration()
                logger.info("✅ MySQL 인증 데이터베이스 초기화 완료")
                results["mysql"] = True
            else:
                logger.error("❌ MySQL 연결 실패")
        except Exception as e:
            logger.error(f"❌ MySQL 초기화 오류: {str(e)}")

        return results

class ServiceManager:
    """비즈니스 서비스 관리"""

    @staticmethod
    def start_services():
        """비즈니스 서비스 시작"""
        services_started = {"scheduler": False, "monitoring": False}

        # 자동 최적화 스케줄러 (임시 비활성화)
        try:
            # auto_scheduler.start()
            logger.info("✅ 자동 최적화 스케줄러 시작 (비활성화됨)")
            services_started["scheduler"] = True
        except Exception as e:
            logger.error(f"❌ 스케줄러 시작 실패: {str(e)}")

        # 모니터링 서비스 (임시 비활성화)
        try:
            # 모니터링 서비스는 현재 비활성화
            logger.info("📊 모니터링 및 알림 서비스 시작 (비활성화됨)")
            logger.info(f"📊 모니터링 대상 마켓: {DEFAULT_MARKETS}")
            logger.info(f"🌐 웹서버 포트: {WEB_CONFIG['port']}")
            services_started["monitoring"] = True
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 시작 실패: {str(e)}")

        return services_started

    @staticmethod
    def stop_services():
        """비즈니스 서비스 중지"""
        try:
            # 모니터링 서비스 종료 (임시 비활성화)
            logger.info("📊 모니터링 서비스 종료 (비활성화됨)")
            # auto_scheduler.shutdown()  # 비활성화됨
        except Exception as e:
            logger.warning(f"⚠️ 모니터링 서비스 종료 실패: {str(e)}")

class ApplicationLifecycle:
    """애플리케이션 생명주기 총괄 관리"""

    def __init__(self):
        self.system_manager = SystemManager()
        self.db_manager = DatabaseManager()
        self.service_manager = ServiceManager()

    async def startup(self):
        """애플리케이션 시작 시 초기화 작업"""
        logger.info("🚀 업비트 자동거래 시스템 시작")

        startup_results = {
            "process_priority": False,
            "sleep_prevention": False,
            "databases": {"sqlite": False, "mysql": False},
            "services": {"scheduler": False, "monitoring": False}
        }

        # 프로세스 우선순위 최적화
        startup_results["process_priority"] = self.system_manager.optimize_process_priority()

        # 24시간 연속 거래를 위한 슬립 방지
        if self.system_manager.start_sleep_prevention():
            logger.info("🛡️ 24시간 연속 거래를 위한 슬립 방지 활성화")
            startup_results["sleep_prevention"] = True

        # 데이터베이스 초기화
        startup_results["databases"] = await self.db_manager.initialize_databases()

        # 비즈니스 서비스 시작
        startup_results["services"] = self.service_manager.start_services()

        return startup_results

    async def shutdown(self):
        """애플리케이션 종료 시 정리 작업"""
        logger.info("🛑 업비트 자동거래 시스템 종료")

        # 비즈니스 서비스 중지
        self.service_manager.stop_services()

        # 시스템 서비스 중지
        self.system_manager.stop_sleep_prevention()

# 전역 인스턴스
app_lifecycle = ApplicationLifecycle()

@asynccontextmanager
async def lifespan_manager(app):
    """FastAPI 애플리케이션 생명주기 관리"""
    try:
        # 시작 시 초기화
        await app_lifecycle.startup()
        yield
    except Exception as e:
        logger.error(f"❌ 시스템 시작 중 오류: {str(e)}")
        app_lifecycle.system_manager.stop_sleep_prevention()  # 오류 시에도 슬립 방지 해제
        raise
    finally:
        # 종료 시 정리
        await app_lifecycle.shutdown()