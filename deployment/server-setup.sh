#!/bin/bash
# =============================================================================
# 🚀 Cafe24 서버 환경 구축 스크립트
# =============================================================================
# SSH root@172.233.87.201에서 실행할 초기 환경 설정 스크립트
# 사용법: chmod +x server-setup.sh && ./server-setup.sh

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

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
echo -e "${PURPLE}🚀 Cafe24 서버 다중 앱 환경 구축 시작${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# 시스템 정보 확인
log_info "시스템 정보 확인 중..."
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "CPU: $(nproc) cores"
echo "Memory: $(free -h | awk 'NR==2{print $2}') RAM"
echo "Disk: $(df -h / | awk 'NR==2{print $4}') available"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    echo "사용법: sudo $0 또는 root 계정으로 실행"
    exit 1
fi

log_success "Root 권한 확인 완료"

# 1단계: 시스템 업데이트
log_info "1단계: 시스템 패키지 업데이트 중..."
apt update -y
apt upgrade -y
log_success "시스템 업데이트 완료"

# 2단계: 기본 패키지 설치
log_info "2단계: 기본 패키지 설치 중..."
apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx \
    build-essential \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

log_success "기본 패키지 설치 완료"

# 3단계: Python 3.9+ 설치
log_info "3단계: Python 환경 설정 중..."
apt install -y python3.9 python3.9-venv python3.9-dev python3-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3 1

# Python 버전 확인
python3 --version
pip3 --version
log_success "Python 환경 설정 완료"

# 4단계: MySQL 8.0 설치
log_info "4단계: MySQL 8.0 설치 중..."

# MySQL APT Repository 추가
wget -c https://dev.mysql.com/get/mysql-apt-config_0.8.24-1_all.deb
DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.24-1_all.deb
apt update

# MySQL 서버 설치 (비대화형)
DEBIAN_FRONTEND=noninteractive apt install -y mysql-server

# MySQL 보안 설정 (자동)
mysql --execute="ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'TempRootPassword123!';"
mysql --execute="DELETE FROM mysql.user WHERE User='';"
mysql --execute="DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
mysql --execute="DROP DATABASE IF EXISTS test;"
mysql --execute="DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
mysql --execute="FLUSH PRIVILEGES;"

systemctl enable mysql
systemctl start mysql

log_success "MySQL 8.0 설치 및 설정 완료"

# 5단계: Nginx 설치
log_info "5단계: Nginx 설치 중..."
apt install -y nginx
systemctl enable nginx
systemctl start nginx

# Nginx 기본 설정 백업
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

log_success "Nginx 설치 및 시작 완료"

# 6단계: Node.js 설치 (선택적)
log_info "6단계: Node.js LTS 설치 중..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
apt install -y nodejs

# PM2 글로벌 설치
npm install -g pm2

node --version
npm --version
pm2 --version
log_success "Node.js 및 PM2 설치 완료"

# 7단계: Redis 설치 (캐싱용)
log_info "7단계: Redis 설치 중..."
apt install -y redis-server
systemctl enable redis-server
systemctl start redis-server

log_success "Redis 설치 및 시작 완료"

# 8단계: 디렉토리 구조 생성
log_info "8단계: 애플리케이션 디렉토리 구조 생성 중..."

# 기본 디렉토리 생성
mkdir -p /opt/apps
mkdir -p /opt/nginx
mkdir -p /opt/logs
mkdir -p /opt/backups
mkdir -p /opt/scripts
mkdir -p /opt/ssl

# 권한 설정
chown -R www-data:www-data /opt/apps
chown -R www-data:www-data /opt/logs
chmod 755 /opt/apps
chmod 755 /opt/logs
chmod 700 /opt/backups
chmod 700 /opt/ssl

log_success "디렉토리 구조 생성 완료"

# 9단계: 방화벽 설정
log_info "9단계: 방화벽 설정 중..."

# UFW 초기화
ufw --force reset

# 기본 정책 설정
ufw default deny incoming
ufw default allow outgoing

# 필수 포트 허용
ufw allow ssh
ufw allow http
ufw allow https

# 애플리케이션 포트 허용 (8001-8010)
for port in {8001..8010}; do
    ufw allow $port/tcp
done

# MySQL 포트 (로컬에서만)
ufw allow from 127.0.0.1 to any port 3306

# Redis 포트 (로컬에서만)
ufw allow from 127.0.0.1 to any port 6379

# 방화벽 활성화
ufw --force enable

log_success "방화벽 설정 완료"

# 10단계: Fail2ban 설정
log_info "10단계: Fail2ban 보안 설정 중..."

# Fail2ban 기본 설정
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF

systemctl enable fail2ban
systemctl start fail2ban

log_success "Fail2ban 보안 설정 완료"

# 11단계: 로그 로테이션 설정
log_info "11단계: 로그 로테이션 설정 중..."

cat > /etc/logrotate.d/apps << 'EOF'
/opt/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
EOF

log_success "로그 로테이션 설정 완료"

# 12단계: 시스템 최적화
log_info "12단계: 시스템 최적화 설정 중..."

# 파일 디스크립터 한계 증가
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Kernel 매개변수 최적화
cat >> /etc/sysctl.conf << 'EOF'
# Network optimization
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 65536 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 30000
net.ipv4.tcp_max_syn_backlog = 30000

# File system optimization
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
EOF

sysctl -p

log_success "시스템 최적화 완료"

# 13단계: 환경 변수 설정
log_info "13단계: 시스템 환경 변수 설정 중..."

cat > /etc/profile.d/apps.sh << 'EOF'
# Apps environment variables
export APPS_ROOT="/opt/apps"
export APPS_LOGS="/opt/logs"
export APPS_BACKUPS="/opt/backups"

# Python environment
export PYTHONPATH="/opt/apps:$PYTHONPATH"
export PYTHONIOENCODING=utf-8

# Aliases
alias apps="cd /opt/apps"
alias logs="cd /opt/logs"
alias applist="pm2 list"
alias appstatus="systemctl status nginx mysql redis-server"
EOF

chmod +x /etc/profile.d/apps.sh

log_success "환경 변수 설정 완료"

# 14단계: 헬스체크 스크립트 생성
log_info "14단계: 시스템 헬스체크 스크립트 생성 중..."

cat > /opt/scripts/healthcheck.sh << 'EOF'
#!/bin/bash
# 시스템 헬스체크 스크립트

echo "=== System Health Check $(date) ==="
echo ""

# 서비스 상태 확인
echo "📋 서비스 상태:"
systemctl is-active nginx || echo "❌ Nginx 중단됨"
systemctl is-active mysql || echo "❌ MySQL 중단됨"
systemctl is-active redis-server || echo "❌ Redis 중단됨"
systemctl is-active fail2ban || echo "❌ Fail2ban 중단됨"

echo ""

# 리소스 사용량 확인
echo "💾 리소스 사용량:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%"
echo "Memory: $(free | awk 'FNR==2{printf "%.2f%%", $3/($3+$4)*100}')"
echo "Disk: $(df -h / | awk 'FNR==2{print $5}') used"

echo ""

# 포트 상태 확인
echo "🌐 포트 상태:"
netstat -tlnp | grep -E ':(80|443|8001|8002|8003|3306|6379)' | while read line; do
    echo "✅ $line"
done

echo ""
echo "=== Health Check Complete ==="
EOF

chmod +x /opt/scripts/healthcheck.sh

log_success "헬스체크 스크립트 생성 완료"

# 15단계: 자동 백업 설정
log_info "15단계: 자동 백업 스크립트 설정 중..."

cat > /opt/scripts/backup.sh << 'EOF'
#!/bin/bash
# 자동 백업 스크립트

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# MySQL 백업
echo "🗄️ MySQL 백업 중..."
mysqldump --all-databases > "$BACKUP_DIR/mysql_backup_$DATE.sql"

# 애플리케이션 설정 백업
echo "📁 애플리케이션 설정 백업 중..."
tar -czf "$BACKUP_DIR/apps_config_$DATE.tar.gz" /opt/apps/*/config.py /opt/apps/*/.env 2>/dev/null || true

# Nginx 설정 백업
echo "🌐 Nginx 설정 백업 중..."
tar -czf "$BACKUP_DIR/nginx_config_$DATE.tar.gz" /etc/nginx/

# 오래된 백업 정리 (30일 이상)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "✅ 백업 완료: $DATE"
EOF

chmod +x /opt/scripts/backup.sh

# Cron 작업 추가 (매일 새벽 2시)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/scripts/backup.sh >> /opt/logs/backup.log 2>&1") | crontab -

log_success "자동 백업 설정 완료"

# 16단계: 최종 설정 정리
log_info "16단계: 최종 설정 정리 중..."

# 임시 파일 정리
rm -f mysql-apt-config_0.8.24-1_all.deb

# 서비스 재시작
systemctl restart nginx
systemctl restart mysql
systemctl restart redis-server
systemctl restart fail2ban

# 상태 확인
systemctl status nginx --no-pager -l
systemctl status mysql --no-pager -l
systemctl status redis-server --no-pager -l

log_success "최종 설정 정리 완료"

# 완료 메시지
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🎉 서버 환경 구축 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📋 설치된 서비스:${NC}"
echo "✅ Python 3.9+"
echo "✅ MySQL 8.0"
echo "✅ Nginx"
echo "✅ Node.js + PM2"
echo "✅ Redis"
echo "✅ Fail2ban"
echo "✅ UFW 방화벽"
echo ""

echo -e "${BLUE}📂 생성된 디렉토리:${NC}"
echo "✅ /opt/apps (애플리케이션)"
echo "✅ /opt/logs (로그)"
echo "✅ /opt/backups (백업)"
echo "✅ /opt/scripts (스크립트)"
echo ""

echo -e "${BLUE}🔐 보안 설정:${NC}"
echo "✅ 방화벽 활성화 (포트: 22, 80, 443, 8001-8010)"
echo "✅ Fail2ban 활성화"
echo "✅ MySQL root 패스워드: TempRootPassword123!"
echo ""

echo -e "${YELLOW}🚨 다음 단계:${NC}"
echo "1. MySQL root 패스워드 변경하기"
echo "2. 도메인 DNS 설정하기"
echo "3. 애플리케이션 배포 스크립트 실행하기"
echo ""

echo -e "${BLUE}💡 유용한 명령어:${NC}"
echo "- 헬스체크: /opt/scripts/healthcheck.sh"
echo "- 백업 실행: /opt/scripts/backup.sh"
echo "- 서비스 상태: systemctl status nginx mysql redis-server"
echo "- 방화벽 상태: ufw status"
echo ""

log_success "서버 환경 구축이 성공적으로 완료되었습니다!"