"""
MySQL 데이터베이스 연결 관리
- MySQL 연결 설정 및 관리
- 세션 관리
- 연결 풀 설정
"""

import os
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# 설정 로드
load_dotenv()

logger = logging.getLogger(__name__)

# MySQL 연결 설정
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "teamprime_trading")
MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

# MySQL URL 구성
MYSQL_URL = f"mysql+aiomysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# SQLAlchemy Base 클래스
class Base(DeclarativeBase):
    metadata = MetaData()

# 비동기 엔진 생성
mysql_engine: AsyncEngine = create_async_engine(
    MYSQL_URL,
    echo=False,  # SQL 쿼리 로깅 (개발시 True)
    pool_size=20,  # 연결 풀 크기
    max_overflow=30,  # 추가 연결 허용 수
    pool_timeout=30,  # 연결 대기 시간
    pool_recycle=3600,  # 연결 재활용 시간 (1시간)
    pool_pre_ping=True,  # 연결 상태 확인
)

# 세션 팩토리 생성
AsyncSessionLocal = async_sessionmaker(
    mysql_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@asynccontextmanager
async def get_mysql_session() -> AsyncGenerator[AsyncSession, None]:
    """MySQL 세션 컨텍스트 매니저"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"데이터베이스 오류: {str(e)}")
            raise
        finally:
            await session.close()

async def init_mysql_db():
    """MySQL 데이터베이스 초기화"""
    try:
        async with mysql_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ MySQL 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ MySQL 데이터베이스 초기화 실패: {str(e)}")
        raise

async def test_mysql_connection():
    """MySQL 연결 테스트"""
    try:
        from sqlalchemy import text
        async with get_mysql_session() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info("✅ MySQL 연결 테스트 성공")
            return True
    except Exception as e:
        logger.error(f"❌ MySQL 연결 테스트 실패: {str(e)}")
        return False