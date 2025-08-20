-- ============================================
-- Cafe24 MySQL 데이터베이스 초기화 스크립트
-- ============================================
-- 실행 방법: mysql -u root -p < setup_mysql.sql
-- 또는 phpMyAdmin에서 직접 실행

-- 1. 데이터베이스 생성 (이미 존재하면 무시)
CREATE DATABASE IF NOT EXISTS teamprime_trading 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 2. 데이터베이스 사용
USE teamprime_trading;

-- 3. 사용자 테이블 생성
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 거래 히스토리 테이블 (선택사항 - 새로운 거래 기록용)
CREATE TABLE IF NOT EXISTS trade_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    market VARCHAR(20) NOT NULL,
    side ENUM('BUY', 'SELL') NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    total DECIMAL(20, 8) NOT NULL,
    profit_loss DECIMAL(20, 8) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_market (user_id, market),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 시스템 설정 테이블 (선택사항)
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_setting_key (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 기본 설정 값 입력
INSERT IGNORE INTO system_settings (setting_key, setting_value, description) VALUES
('system_version', '2.1', '시스템 버전'),
('maintenance_mode', 'false', '유지보수 모드'),
('max_concurrent_users', '100', '최대 동시 사용자 수');

-- 7. 데이터베이스 정보 확인
SELECT 
    'Database Created' as Status,
    DATABASE() as Current_Database,
    USER() as Current_User,
    NOW() as Setup_Time;

-- 8. 테이블 목록 확인
SHOW TABLES;

-- 9. 사용자 테이블 구조 확인
DESCRIBE users;