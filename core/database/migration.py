"""
데이터베이스 마이그레이션 관리
- 사용자 테이블만 생성 (API 키 저장 제거로 보안 강화)
"""

import logging
from sqlalchemy import text
from .mysql_connection import mysql_engine

logger = logging.getLogger(__name__)

# 사용자 테이블 생성 SQL - 권한 시스템 확장
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('owner', 'prime', 'manager', 'member', 'user') DEFAULT 'user',
    promoted_by INT NULL,
    promoted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    FOREIGN KEY (promoted_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 업무 관리 테이블
CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    category ENUM('기획', '개발', '디자인', '운영', '영업', '고객지원', '회계', '법무', '교육', '유지보수', '기타') DEFAULT '기타',
    status ENUM('대기', '진행중', '완료', '보류', '취소') DEFAULT '대기',
    assignee_id INT NULL,
    created_by INT NOT NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_assignee (assignee_id),
    INDEX idx_created_by (created_by),
    INDEX idx_status (status),
    INDEX idx_category (category),
    FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 지출 관리 테이블
CREATE_EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NULL,
    category ENUM('자산', '소모품', '식비', '교통', '출장', '통신', '소프트웨어', '급여', '인센티브', '교육/세미나', '관리비', '인건비', '용역', '세금', '기타', '일반') DEFAULT '기타',
    amount DECIMAL(12,2) NOT NULL,
    description TEXT NOT NULL,
    receipt_file VARCHAR(500),
    participants_internal TEXT COMMENT 'JSON array of internal participant user IDs',
    participants_external INT DEFAULT 0 COMMENT 'Number of external participants',
    external_note TEXT COMMENT 'Names or details of external participants',
    created_by INT NOT NULL,
    status ENUM('제출', '검토', '승인', '반려', '정산') DEFAULT '제출',
    approved_by INT NULL,
    expense_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task (task_id),
    INDEX idx_created_by (created_by),
    INDEX idx_status (status),
    INDEX idx_category (category),
    INDEX idx_expense_date (expense_date),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 수익 관리 테이블
CREATE_INCOMES_TABLE = """
CREATE TABLE IF NOT EXISTS incomes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    category ENUM('틱톡', '유튜브', '애드몹', '광고협찬', '프로젝트', '기타') DEFAULT '기타',
    amount DECIMAL(12,2) NOT NULL,
    source VARCHAR(200),
    description TEXT,
    attachment_file VARCHAR(500),
    created_by INT NOT NULL,
    income_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_created_by (created_by),
    INDEX idx_category (category),
    INDEX idx_income_date (income_date),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# 업무 관계 테이블 (마일스톤 연결용)
CREATE_TASK_RELATIONSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS task_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    predecessor_id INT NOT NULL,
    successor_id INT NOT NULL,
    relationship_type ENUM('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish') DEFAULT 'finish_to_start',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_relationship (predecessor_id, successor_id),
    INDEX idx_predecessor (predecessor_id),
    INDEX idx_successor (successor_id),
    FOREIGN KEY (predecessor_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (successor_id) REFERENCES tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# API 키와 세션 테이블 제거됨 - 보안 강화를 위해 API 키 저장하지 않음

async def run_migration():
    """데이터베이스 마이그레이션 실행 - 회사 관리 시스템 스키마"""
    try:
        async with mysql_engine.begin() as conn:
            # 1. 사용자 테이블 생성/수정 (권한 시스템 포함)
            await conn.execute(text(CREATE_USERS_TABLE))
            logger.info("✅ users 테이블 생성/확인 완료 (권한 시스템 포함)")
            
            # 2. 업무 관리 테이블 생성
            await conn.execute(text(CREATE_TASKS_TABLE))
            logger.info("✅ tasks 테이블 생성/확인 완료")
            
            # 3. 지출 관리 테이블 생성
            await conn.execute(text(CREATE_EXPENSES_TABLE))
            logger.info("✅ expenses 테이블 생성/확인 완료")
            
            # 4. 수익 관리 테이블 생성  
            await conn.execute(text(CREATE_INCOMES_TABLE))
            logger.info("✅ incomes 테이블 생성/확인 완료")
            
            # 5. 업무 관계 테이블 생성 (마일스톤 연결)
            await conn.execute(text(CREATE_TASK_RELATIONSHIPS_TABLE))
            logger.info("✅ task_relationships 테이블 생성/확인 완료")
            
        logger.info("🎉 데이터베이스 마이그레이션 완료 (회사 관리 시스템)")
        
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