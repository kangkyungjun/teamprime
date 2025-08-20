"""
데이터베이스 마이그레이션 관리
- 사용자 테이블만 생성 (API 키 저장 제거로 보안 강화)
"""

import logging
from sqlalchemy import text
from .mysql_connection import mysql_engine

logger = logging.getLogger(__name__)

# 사용자 테이블 생성 SQL
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# API 키와 세션 테이블 제거됨 - 보안 강화를 위해 API 키 저장하지 않음

async def run_migration():
    """데이터베이스 마이그레이션 실행 - 간소화된 스키마"""
    try:
        async with mysql_engine.begin() as conn:
            # 사용자 테이블만 생성 (보안 강화)
            await conn.execute(text(CREATE_USERS_TABLE))
            logger.info("✅ users 테이블 생성/확인 완료")
            
        logger.info("🎉 데이터베이스 마이그레이션 완료 (보안 강화된 스키마)")
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 마이그레이션 실패: {str(e)}")
        raise

async def check_tables_exist():
    """테이블 존재 여부 확인 - 간소화된 스키마"""
    try:
        async with mysql_engine.begin() as conn:
            # users 테이블만 확인
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name = 'users'
            """))
            
            existing_tables = [row[0] for row in result.fetchall()]
            
            if 'users' not in existing_tables:
                logger.warning("⚠️ users 테이블이 존재하지 않습니다")
                return False
            else:
                logger.info("✅ users 테이블 존재 확인")
                return True
                
    except Exception as e:
        logger.error(f"❌ 테이블 확인 실패: {str(e)}")
        return False