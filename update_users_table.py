#!/usr/bin/env python3
"""
기존 users 테이블에 역할 시스템 컬럼 추가
- role 컬럼 추가
- promoted_by, promoted_at 컬럼 추가
- 인덱스 추가
"""

import asyncio
import logging
from sqlalchemy import text
from core.database.mysql_connection import mysql_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 테이블 업데이트 SQL
UPDATE_USERS_TABLE_SQL = """
ALTER TABLE users 
ADD COLUMN role ENUM('owner', 'prime', 'manager', 'member', 'user') DEFAULT 'user' AFTER password_hash,
ADD COLUMN promoted_by INT NULL AFTER role,
ADD COLUMN promoted_at TIMESTAMP NULL AFTER promoted_by,
ADD INDEX idx_role (role),
ADD CONSTRAINT fk_promoted_by FOREIGN KEY (promoted_by) REFERENCES users(id) ON DELETE SET NULL;
"""

async def update_users_table():
    """기존 users 테이블에 역할 시스템 컬럼 추가"""
    try:
        logger.info("🔧 users 테이블 업데이트 시작...")
        
        async with mysql_engine.begin() as conn:
            # 컬럼 존재 확인
            result = await conn.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'teamprime_trading' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'role'
            """))
            
            role_exists = result.fetchone()
            
            if role_exists:
                logger.info("✅ role 컬럼이 이미 존재합니다")
            else:
                logger.info("📊 role 시스템 컬럼들 추가 중...")
                await conn.execute(text(UPDATE_USERS_TABLE_SQL))
                logger.info("✅ users 테이블 업데이트 완료")
        
        # 업데이트된 테이블 구조 확인
        async with mysql_engine.begin() as conn:
            result = await conn.execute(text("DESCRIBE users"))
            columns = result.fetchall()
            
            logger.info("📋 업데이트된 users 테이블 구조:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]} {col[2]} {col[3]} {col[4]} {col[5]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ users 테이블 업데이트 실패: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(update_users_table())