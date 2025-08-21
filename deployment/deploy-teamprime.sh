#!/bin/bash
# =============================================================================
# 🚀 Teamprime 업비트 자동거래 시스템 배포 스크립트
# =============================================================================
# Cafe24 서버에 Teamprime 애플리케이션을 자동 배포하는 스크립트
# 사용법: chmod +x deploy-teamprime.sh && ./deploy-teamprime.sh

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 로그 함수
log_info() {
    echo -e "${BLUE}📋 INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

# 헤더 출력
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${PURPLE}🚀 Teamprime 업비트 자동거래 시스템 배포${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    exit 1
fi

# 변수 설정
APP_NAME="teamprime"
APP_ROOT="/opt/apps/$APP_NAME"
APP_SOURCE="$APP_ROOT/source"
APP_CONFIG="$APP_ROOT/config"
APP_LOGS="$APP_ROOT/logs"
APP_VENV="$APP_ROOT/venv"
GITHUB_REPO="https://github.com/your-username/teamprime.git"  # 실제 저장소로 변경 필요
SERVICE_NAME="teamprime"

# 사용자 입력
echo -e "${BLUE}📋 Teamprime 배포 설정${NC}"
read -p "GitHub 저장소 URL을 입력하세요 (기본값: $GITHUB_REPO): " INPUT_REPO
if [ ! -z "$INPUT_REPO" ]; then
    GITHUB_REPO="$INPUT_REPO"
fi

read -p "배포할 브랜치를 입력하세요 (기본값: main): " BRANCH
BRANCH=${BRANCH:-main}

read -p "MySQL 데이터베이스 비밀번호를 입력하세요: " DB_PASSWORD
if [ -z "$DB_PASSWORD" ]; then
    log_error "데이터베이스 비밀번호는 필수입니다."
    exit 1
fi

read -p "JWT Secret Key를 입력하세요 (최소 32자): " JWT_SECRET
if [ ${#JWT_SECRET} -lt 32 ]; then
    log_error "JWT Secret Key는 최소 32자 이상이어야 합니다."
    exit 1
fi

echo ""

# 1단계: 애플리케이션 디렉토리 준비
log_info "1단계: 애플리케이션 디렉토리 준비 중..."

# 기존 소스 백업 (있는 경우)
if [ -d "$APP_SOURCE" ]; then
    BACKUP_DIR="$APP_ROOT/backups/source_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$APP_ROOT/backups"
    mv "$APP_SOURCE" "$BACKUP_DIR"
    log_warning "기존 소스를 $BACKUP_DIR로 백업했습니다."
fi

# 디렉토리 생성
mkdir -p "$APP_SOURCE"
mkdir -p "$APP_CONFIG"
mkdir -p "$APP_LOGS"

log_success "애플리케이션 디렉토리 준비 완료"

# 2단계: 소스 코드 클론
log_info "2단계: GitHub에서 소스 코드 클론 중..."

cd "$APP_SOURCE"
git clone -b "$BRANCH" "$GITHUB_REPO" .
git config --global --add safe.directory "$APP_SOURCE"

# Git 정보 표시
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B | head -n 1)
log_info "배포된 커밋: $COMMIT_HASH - $COMMIT_MSG"

log_success "소스 코드 클론 완료"

# 3단계: Python 가상환경 설정
log_info "3단계: Python 가상환경 설정 중..."

# 기존 가상환경 제거 (있는 경우)
if [ -d "$APP_VENV" ]; then
    rm -rf "$APP_VENV"
fi

# 새 가상환경 생성
python3 -m venv "$APP_VENV"
source "$APP_VENV/bin/activate"

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
if [ -f "$APP_SOURCE/requirements.txt" ]; then
    pip install -r "$APP_SOURCE/requirements.txt"
    log_success "Python 패키지 설치 완료"
else
    log_error "requirements.txt 파일이 없습니다."
    exit 1
fi

log_success "Python 가상환경 설정 완료"

# 4단계: 데이터베이스 설정
log_info "4단계: 데이터베이스 설정 중..."

# MySQL 데이터베이스 및 사용자 생성
mysql -u root -pTempRootPassword123! << EOF
CREATE DATABASE IF NOT EXISTS teamprime_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'teamprime_user'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON teamprime_db.* TO 'teamprime_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# 데이터베이스 테이블 생성
if [ -f "$APP_SOURCE/setup_mysql.sql" ]; then
    mysql -u teamprime_user -p$DB_PASSWORD teamprime_db < "$APP_SOURCE/setup_mysql.sql"
    log_success "데이터베이스 테이블 생성 완료"
else
    log_warning "setup_mysql.sql 파일이 없습니다. 수동으로 테이블을 생성해야 합니다."
fi

log_success "데이터베이스 설정 완료"

# 5단계: 환경 설정 파일 생성
log_info "5단계: 환경 설정 파일 생성 중..."

cat > "$APP_CONFIG/.env" << EOF
# =============================================================================
# Teamprime 애플리케이션 환경 변수
# =============================================================================

# 서버 설정
HOST=0.0.0.0
PORT=8001
DEBUG=False
ENVIRONMENT=production

# 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=teamprime_db
MYSQL_USERNAME=teamprime_user
MYSQL_PASSWORD=$DB_PASSWORD

# JWT 인증 설정
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis 캐시 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# 업비트 API 설정
UPBIT_BASE_URL=https://api.upbit.com
API_RATE_LIMIT=600

# 로그 설정
LOG_LEVEL=INFO
LOG_FILE=/opt/logs/apps/teamprime/application.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# 백업 설정
BACKUP_ENABLED=True
BACKUP_INTERVAL_HOURS=6
BACKUP_RETENTION_DAYS=30

# 모니터링 설정
HEALTHCHECK_ENABLED=True
HEALTHCHECK_INTERVAL=60
METRICS_ENABLED=True

# 업비트 거래 설정
MARKETS=KRW-BTC,KRW-XRP,KRW-ETH,KRW-DOGE,KRW-BTT
YEARS=3

# 배포 정보
DEPLOY_VERSION=$COMMIT_HASH
DEPLOY_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# 환경 파일 보안 설정
chmod 600 "$APP_CONFIG/.env"
chown www-data:www-data "$APP_CONFIG/.env"

log_success "환경 설정 파일 생성 완료"

# 6단계: systemd 서비스 파일 생성
log_info "6단계: systemd 서비스 설정 중..."

cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Teamprime 업비트 자동거래 시스템
Documentation=https://github.com/your-repo/teamprime
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_SOURCE
Environment=PATH=$APP_VENV/bin
Environment=PYTHONPATH=$APP_SOURCE
EnvironmentFile=$APP_CONFIG/.env
ExecStart=$APP_VENV/bin/python main.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=5
TimeoutStopSec=30

# 리소스 제한
LimitNOFILE=65536
MemoryMax=1G
CPUQuota=80%

# 보안 설정
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_LOGS /opt/logs/apps/teamprime

[Install]
WantedBy=multi-user.target
EOF

# systemd 서비스 등록
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

log_success "systemd 서비스 설정 완료"

# 7단계: 권한 설정
log_info "7단계: 파일 권한 설정 중..."

# 애플리케이션 파일 권한
chown -R www-data:www-data "$APP_ROOT"
find "$APP_SOURCE" -type d -exec chmod 755 {} \;
find "$APP_SOURCE" -type f -exec chmod 644 {} \;
chmod +x "$APP_SOURCE/main.py"

# 로그 디렉토리 권한
mkdir -p "/opt/logs/apps/$APP_NAME"
chown -R www-data:www-data "/opt/logs/apps/$APP_NAME"
chmod 755 "/opt/logs/apps/$APP_NAME"

log_success "파일 권한 설정 완료"

# 8단계: 데이터베이스 연결 테스트
log_info "8단계: 데이터베이스 연결 테스트 중..."

# 데이터베이스 연결 테스트 스크립트 생성
cat > "/tmp/test_db_connection.py" << EOF
import asyncio
import sys
import os
sys.path.append('$APP_SOURCE')

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv('$APP_CONFIG/.env')

async def test_connection():
    try:
        from core.database.mysql_connection import test_mysql_connection
        result = await test_mysql_connection()
        print(f"Database connection test: {'SUCCESS' if result else 'FAILED'}")
        return result
    except Exception as e:
        print(f"Database connection error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
EOF

# 가상환경에서 테스트 실행
cd "$APP_SOURCE"
source "$APP_VENV/bin/activate"
if python "/tmp/test_db_connection.py"; then
    log_success "데이터베이스 연결 테스트 성공"
else
    log_error "데이터베이스 연결 테스트 실패"
    exit 1
fi

# 임시 파일 정리
rm "/tmp/test_db_connection.py"

# 9단계: 애플리케이션 시작
log_info "9단계: 애플리케이션 서비스 시작 중..."

# 서비스 시작
systemctl start "$SERVICE_NAME"

# 시작 대기
sleep 5

# 서비스 상태 확인
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_success "Teamprime 서비스 시작 성공"
else
    log_error "Teamprime 서비스 시작 실패"
    systemctl status "$SERVICE_NAME" --no-pager -l
    journalctl -u "$SERVICE_NAME" --no-pager -l --since "1 minute ago"
    exit 1
fi

# 10단계: 헬스 체크
log_info "10단계: 애플리케이션 헬스 체크 중..."

# 포트 확인
sleep 3
if netstat -tlnp | grep -q ":8001.*python"; then
    log_success "포트 8001에서 애플리케이션이 실행 중입니다"
else
    log_error "포트 8001에서 애플리케이션을 찾을 수 없습니다"
    exit 1
fi

# HTTP 헬스 체크
for i in {1..10}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/system-status | grep -q "200"; then
        log_success "HTTP 헬스 체크 성공 (시도: $i/10)"
        break
    elif [ $i -eq 10 ]; then
        log_error "HTTP 헬스 체크 실패"
        exit 1
    else
        log_info "HTTP 헬스 체크 재시도 중... ($i/10)"
        sleep 2
    fi
done

# 11단계: 배포 정보 기록
log_info "11단계: 배포 정보 기록 중..."

cat > "$APP_ROOT/DEPLOYMENT_INFO.md" << EOF
# Teamprime 배포 정보

## 배포 세부사항
- **배포 일시**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **배포 버전**: $COMMIT_HASH
- **브랜치**: $BRANCH
- **커밋 메시지**: $COMMIT_MSG

## 서버 정보
- **호스트**: $(hostname)
- **OS**: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')
- **Python 버전**: $(python3 --version)
- **애플리케이션 경로**: $APP_SOURCE
- **서비스 상태**: $(systemctl is-active $SERVICE_NAME)

## 네트워크 정보
- **애플리케이션 포트**: 8001
- **프록시**: Nginx (trading.yourdomain.com)
- **데이터베이스**: MySQL (teamprime_db)
- **Redis**: localhost:6379

## 로그 파일
- **애플리케이션 로그**: /opt/logs/apps/teamprime/application.log
- **시스템 로그**: journalctl -u teamprime
- **Nginx 로그**: /opt/logs/nginx/teamprime.access.log

## 관리 명령어
\`\`\`bash
# 서비스 상태 확인
systemctl status teamprime

# 로그 확인
journalctl -u teamprime -f

# 서비스 재시작
systemctl restart teamprime

# 헬스 체크
curl http://localhost:8001/api/system-status
\`\`\`
EOF

log_success "배포 정보 기록 완료"

# 12단계: 자동 백업 설정
log_info "12단계: 자동 백업 크론 작업 설정 중..."

# 백업 스크립트 생성
cat > "/opt/scripts/backup-teamprime.sh" << 'EOF'
#!/bin/bash
# Teamprime 애플리케이션 백업 스크립트

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="/opt/apps/teamprime/backups"
APP_SOURCE="/opt/apps/teamprime/source"
APP_CONFIG="/opt/apps/teamprime/config"

mkdir -p "$BACKUP_ROOT"

# 소스 코드 백업
tar -czf "$BACKUP_ROOT/source_$DATE.tar.gz" -C "$APP_SOURCE" .

# 설정 파일 백업
cp "$APP_CONFIG/.env" "$BACKUP_ROOT/env_$DATE.backup"

# 데이터베이스 백업
mysqldump -u teamprime_user -p$(grep MYSQL_PASSWORD $APP_CONFIG/.env | cut -d= -f2) teamprime_db > "$BACKUP_ROOT/database_$DATE.sql"

# 오래된 백업 정리 (30일 이상)
find "$BACKUP_ROOT" -name "*.tar.gz" -mtime +30 -delete
find "$BACKUP_ROOT" -name "*.backup" -mtime +30 -delete
find "$BACKUP_ROOT" -name "*.sql" -mtime +30 -delete

echo "$(date): Teamprime backup completed - $DATE" >> /opt/logs/apps/teamprime/backup.log
EOF

chmod +x "/opt/scripts/backup-teamprime.sh"

# 크론 작업 추가 (매일 새벽 3시)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/scripts/backup-teamprime.sh") | crontab -

log_success "자동 백업 설정 완료"

# 완료 메시지
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🎉 Teamprime 배포 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📊 배포 정보:${NC}"
echo "✅ 애플리케이션: Teamprime 업비트 자동거래 시스템"
echo "✅ 버전: $COMMIT_HASH ($BRANCH)"
echo "✅ 포트: 8001"
echo "✅ 서비스: $SERVICE_NAME"
echo "✅ 상태: $(systemctl is-active $SERVICE_NAME)"
echo ""

echo -e "${BLUE}🌐 접속 정보:${NC}"
echo "✅ 로컬 접속: http://localhost:8001"
echo "✅ 외부 접속: https://trading.yourdomain.com (Nginx 설정 후)"
echo "✅ 시스템 상태: http://localhost:8001/api/system-status"
echo ""

echo -e "${BLUE}📁 주요 경로:${NC}"
echo "✅ 소스 코드: $APP_SOURCE"
echo "✅ 설정 파일: $APP_CONFIG/.env"
echo "✅ 로그 파일: /opt/logs/apps/teamprime/"
echo "✅ 백업 파일: $APP_ROOT/backups/"
echo ""

echo -e "${BLUE}🛠️ 관리 명령어:${NC}"
echo "- 서비스 상태: systemctl status teamprime"
echo "- 서비스 재시작: systemctl restart teamprime"
echo "- 실시간 로그: journalctl -u teamprime -f"
echo "- 헬스 체크: curl http://localhost:8001/api/system-status"
echo "- 수동 백업: /opt/scripts/backup-teamprime.sh"
echo ""

echo -e "${YELLOW}🚨 다음 단계:${NC}"
echo "1. DNS 설정: trading.yourdomain.com → 서버 IP"
echo "2. SSL 인증서 설치 (Let's Encrypt)"
echo "3. 업비트 API 키 설정 (애플리케이션에서)"
echo "4. 모니터링 및 알림 설정"
echo ""

log_success "Teamprime 배포가 성공적으로 완료되었습니다!"

# 최종 상태 확인
echo -e "${BLUE}🔍 최종 상태 확인:${NC}"
systemctl status "$SERVICE_NAME" --no-pager -l
netstat -tlnp | grep ":8001"