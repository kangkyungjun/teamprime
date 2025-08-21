#!/bin/bash
# =============================================================================
# 🏗️ 다중 앱 디렉토리 구조 설정 스크립트
# =============================================================================
# 여러 웹 애플리케이션을 위한 표준화된 디렉토리 구조를 생성합니다.
# 사용법: chmod +x setup-multi-apps.sh && ./setup-multi-apps.sh

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
echo -e "${PURPLE}🏗️ 다중 애플리케이션 디렉토리 구조 설정${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    exit 1
fi

# 기본 경로 설정
APPS_ROOT="/opt/apps"
NGINX_ROOT="/opt/nginx"
LOGS_ROOT="/opt/logs"
SCRIPTS_ROOT="/opt/scripts"

# 1단계: 메인 애플리케이션 디렉토리 구조 생성
log_info "1단계: 메인 애플리케이션 디렉토리 구조 생성 중..."

# Teamprime 앱 구조
mkdir -p $APPS_ROOT/teamprime/{source,logs,backups,config,venv}
mkdir -p $APPS_ROOT/teamprime/source/{core,deployment,docs}

# 미래의 앱들을 위한 템플릿 구조
for app in app2 app3 admin-panel; do
    mkdir -p $APPS_ROOT/$app/{source,logs,backups,config,venv}
done

log_success "메인 애플리케이션 디렉토리 구조 생성 완료"

# 2단계: 공용 리소스 디렉토리 생성
log_info "2단계: 공용 리소스 디렉토리 생성 중..."

mkdir -p $APPS_ROOT/shared/{config,scripts,templates,ssl,uploads,static}
mkdir -p $APPS_ROOT/shared/database/{mysql,redis,backups}

log_success "공용 리소스 디렉토리 생성 완료"

# 3단계: Nginx 설정 디렉토리 구조
log_info "3단계: Nginx 설정 디렉토리 구조 생성 중..."

mkdir -p $NGINX_ROOT/{sites-available,sites-enabled,ssl,logs,conf.d}
mkdir -p $NGINX_ROOT/templates/{apps,api,static}

log_success "Nginx 설정 디렉토리 구조 생성 완료"

# 4단계: 로그 디렉토리 구조
log_info "4단계: 로그 디렉토리 구조 생성 중..."

mkdir -p $LOGS_ROOT/{nginx,mysql,redis,apps,system,backups}
mkdir -p $LOGS_ROOT/apps/{teamprime,app2,app3,admin-panel}

log_success "로그 디렉토리 구조 생성 완료"

# 5단계: 스크립트 디렉토리 구조
log_info "5단계: 스크립트 디렉토리 구조 생성 중..."

mkdir -p $SCRIPTS_ROOT/{deployment,monitoring,backup,maintenance,utils}

log_success "스크립트 디렉토리 구조 생성 완료"

# 6단계: 애플리케이션별 설정 파일 템플릿 생성
log_info "6단계: 애플리케이션별 설정 파일 템플릿 생성 중..."

# Teamprime 앱 환경변수 템플릿
cat > $APPS_ROOT/teamprime/config/.env.template << 'EOF'
# =============================================================================
# Teamprime 애플리케이션 환경 변수 템플릿
# =============================================================================

# 서버 설정
HOST=0.0.0.0
PORT=8001
DEBUG=False
ENVIRONMENT=production

# 데이터베이스 설정 (MySQL)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=teamprime_db
MYSQL_USERNAME=teamprime_user
MYSQL_PASSWORD=your_secure_password_here

# JWT 인증 설정
JWT_SECRET_KEY=your_super_secret_jwt_key_here_minimum_32_characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Redis 캐시 설정 (선택사항)
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
EOF

# 범용 앱 환경변수 템플릿 생성 함수
create_app_template() {
    local app_name=$1
    local port=$2
    
    cat > $APPS_ROOT/$app_name/config/.env.template << EOF
# =============================================================================
# $app_name 애플리케이션 환경 변수 템플릿
# =============================================================================

# 서버 설정
HOST=0.0.0.0
PORT=$port
DEBUG=False
ENVIRONMENT=production

# 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=${app_name}_db
MYSQL_USERNAME=${app_name}_user
MYSQL_PASSWORD=your_secure_password_here

# JWT 인증 설정
JWT_SECRET_KEY=your_super_secret_jwt_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 로그 설정
LOG_LEVEL=INFO
LOG_FILE=/opt/logs/apps/$app_name/application.log

# 백업 설정
BACKUP_ENABLED=True
BACKUP_RETENTION_DAYS=30
EOF
}

# 각 앱별 템플릿 생성
create_app_template "app2" "8002"
create_app_template "app3" "8003"
create_app_template "admin-panel" "8010"

log_success "애플리케이션별 설정 파일 템플릿 생성 완료"

# 7단계: 애플리케이션별 systemd 서비스 템플릿 생성
log_info "7단계: systemd 서비스 템플릿 생성 중..."

# Teamprime 서비스 템플릿
cat > $APPS_ROOT/teamprime/config/teamprime.service << 'EOF'
[Unit]
Description=Teamprime Trading System
Documentation=https://github.com/your-repo/teamprime
After=network.target mysql.service redis-server.service
Wants=mysql.service redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/apps/teamprime/source
Environment=PATH=/opt/apps/teamprime/venv/bin
Environment=PYTHONPATH=/opt/apps/teamprime/source
EnvironmentFile=/opt/apps/teamprime/config/.env
ExecStart=/opt/apps/teamprime/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
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
ReadWritePaths=/opt/apps/teamprime/logs /opt/logs/apps/teamprime

[Install]
WantedBy=multi-user.target
EOF

# 범용 서비스 템플릿 생성 함수
create_service_template() {
    local app_name=$1
    
    cat > $APPS_ROOT/$app_name/config/$app_name.service << EOF
[Unit]
Description=$app_name Application
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/apps/$app_name/source
Environment=PATH=/opt/apps/$app_name/venv/bin
EnvironmentFile=/opt/apps/$app_name/config/.env
ExecStart=/opt/apps/$app_name/venv/bin/python main.py
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
}

# 각 앱별 서비스 파일 생성
create_service_template "app2"
create_service_template "app3"
create_service_template "admin-panel"

log_success "systemd 서비스 템플릿 생성 완료"

# 8단계: 애플리케이션 관리 스크립트 생성
log_info "8단계: 애플리케이션 관리 스크립트 생성 중..."

# 앱 관리 스크립트
cat > $SCRIPTS_ROOT/utils/app-manager.sh << 'EOF'
#!/bin/bash
# =============================================================================
# 애플리케이션 관리 스크립트
# =============================================================================
# 사용법: ./app-manager.sh [command] [app_name]
# Commands: list, status, start, stop, restart, logs, deploy

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APPS_ROOT="/opt/apps"
AVAILABLE_APPS=("teamprime" "app2" "app3" "admin-panel")

show_help() {
    echo "애플리케이션 관리 스크립트"
    echo ""
    echo "사용법: $0 [command] [app_name]"
    echo ""
    echo "Commands:"
    echo "  list          - 모든 앱 목록 표시"
    echo "  status        - 모든 앱 또는 특정 앱 상태 확인"
    echo "  start [app]   - 앱 시작"
    echo "  stop [app]    - 앱 중지"
    echo "  restart [app] - 앱 재시작"
    echo "  logs [app]    - 앱 로그 보기"
    echo "  deploy [app]  - 앱 배포"
    echo ""
    echo "Available apps: ${AVAILABLE_APPS[*]}"
}

list_apps() {
    echo -e "${BLUE}📱 등록된 애플리케이션:${NC}"
    for app in "${AVAILABLE_APPS[@]}"; do
        if systemctl is-enabled $app >/dev/null 2>&1; then
            status=$(systemctl is-active $app 2>/dev/null || echo "inactive")
            if [ "$status" = "active" ]; then
                echo -e "  ✅ $app (running)"
            else
                echo -e "  ❌ $app (stopped)"
            fi
        else
            echo -e "  ⚪ $app (not installed)"
        fi
    done
}

show_status() {
    local app_name=$1
    
    if [ -z "$app_name" ]; then
        # 모든 앱 상태 표시
        for app in "${AVAILABLE_APPS[@]}"; do
            show_status $app
        done
        return
    fi
    
    if systemctl is-enabled $app_name >/dev/null 2>&1; then
        echo -e "${BLUE}📊 $app_name 상태:${NC}"
        systemctl status $app_name --no-pager -l
    else
        echo -e "${YELLOW}⚠️ $app_name 서비스가 설치되지 않았습니다${NC}"
    fi
}

start_app() {
    local app_name=$1
    echo -e "${GREEN}🚀 $app_name 시작 중...${NC}"
    systemctl start $app_name
    echo -e "${GREEN}✅ $app_name 시작 완료${NC}"
}

stop_app() {
    local app_name=$1
    echo -e "${YELLOW}⏹️ $app_name 중지 중...${NC}"
    systemctl stop $app_name
    echo -e "${YELLOW}✅ $app_name 중지 완료${NC}"
}

restart_app() {
    local app_name=$1
    echo -e "${BLUE}🔄 $app_name 재시작 중...${NC}"
    systemctl restart $app_name
    echo -e "${GREEN}✅ $app_name 재시작 완료${NC}"
}

show_logs() {
    local app_name=$1
    echo -e "${BLUE}📋 $app_name 로그:${NC}"
    journalctl -u $app_name -f --no-pager
}

# 메인 로직
case "$1" in
    "list")
        list_apps
        ;;
    "status")
        show_status $2
        ;;
    "start")
        if [ -z "$2" ]; then
            echo "Error: 앱 이름을 지정해주세요"
            show_help
            exit 1
        fi
        start_app $2
        ;;
    "stop")
        if [ -z "$2" ]; then
            echo "Error: 앱 이름을 지정해주세요"
            show_help
            exit 1
        fi
        stop_app $2
        ;;
    "restart")
        if [ -z "$2" ]; then
            echo "Error: 앱 이름을 지정해주세요"
            show_help
            exit 1
        fi
        restart_app $2
        ;;
    "logs")
        if [ -z "$2" ]; then
            echo "Error: 앱 이름을 지정해주세요"
            show_help
            exit 1
        fi
        show_logs $2
        ;;
    *)
        show_help
        ;;
esac
EOF

chmod +x $SCRIPTS_ROOT/utils/app-manager.sh

log_success "애플리케이션 관리 스크립트 생성 완료"

# 9단계: 데이터베이스 관리 스크립트 생성
log_info "9단계: 데이터베이스 관리 스크립트 생성 중..."

cat > $SCRIPTS_ROOT/utils/db-manager.sh << 'EOF'
#!/bin/bash
# =============================================================================
# 데이터베이스 관리 스크립트
# =============================================================================
# MySQL 데이터베이스와 사용자 생성/관리

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-"TempRootPassword123!"}

create_database() {
    local db_name=$1
    local user_name=$2
    local user_password=$3
    
    echo -e "${BLUE}🗄️ 데이터베이스 생성: $db_name${NC}"
    
    mysql -u root -p$MYSQL_ROOT_PASSWORD << EOF
CREATE DATABASE IF NOT EXISTS $db_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$user_name'@'localhost' IDENTIFIED BY '$user_password';
GRANT ALL PRIVILEGES ON $db_name.* TO '$user_name'@'localhost';
FLUSH PRIVILEGES;
EOF
    
    echo -e "${GREEN}✅ 데이터베이스 $db_name 생성 완료${NC}"
}

# 앱별 데이터베이스 생성
echo -e "${BLUE}📋 애플리케이션 데이터베이스 생성 중...${NC}"

create_database "teamprime_db" "teamprime_user" "TeamprimePwd2024!"
create_database "app2_db" "app2_user" "App2Pwd2024!"
create_database "app3_db" "app3_user" "App3Pwd2024!"
create_database "admin_panel_db" "admin_user" "AdminPwd2024!"
create_database "shared_db" "shared_user" "SharedPwd2024!"

echo -e "${GREEN}✅ 모든 데이터베이스 생성 완료${NC}"
EOF

chmod +x $SCRIPTS_ROOT/utils/db-manager.sh

log_success "데이터베이스 관리 스크립트 생성 완료"

# 10단계: 권한 설정
log_info "10단계: 디렉토리 권한 설정 중..."

# 애플리케이션 디렉토리 권한
chown -R www-data:www-data $APPS_ROOT
find $APPS_ROOT -type d -exec chmod 755 {} \;
find $APPS_ROOT -type f -exec chmod 644 {} \;

# 실행 스크립트 권한
find $SCRIPTS_ROOT -name "*.sh" -exec chmod +x {} \;

# 로그 디렉토리 권한
chown -R www-data:www-data $LOGS_ROOT
chmod -R 755 $LOGS_ROOT

# 설정 파일 보안 권한
find $APPS_ROOT -name ".env*" -exec chmod 600 {} \;
find $APPS_ROOT -name "*.service" -exec chmod 644 {} \;

log_success "디렉토리 권한 설정 완료"

# 11단계: 심볼릭 링크 생성
log_info "11단계: 편의를 위한 심볼릭 링크 생성 중..."

# /usr/local/bin에 관리 스크립트 링크
ln -sf $SCRIPTS_ROOT/utils/app-manager.sh /usr/local/bin/apps
ln -sf $SCRIPTS_ROOT/utils/db-manager.sh /usr/local/bin/dbmanager

# 빠른 접근을 위한 링크
ln -sf $APPS_ROOT /root/apps
ln -sf $LOGS_ROOT /root/logs
ln -sf $SCRIPTS_ROOT /root/scripts

log_success "심볼릭 링크 생성 완료"

# 12단계: 디렉토리 구조 문서화
log_info "12단계: 디렉토리 구조 문서화 중..."

cat > $APPS_ROOT/README.md << 'EOF'
# 🏗️ 다중 애플리케이션 디렉토리 구조

## 📂 디렉토리 구조

```
/opt/
├── apps/                           # 애플리케이션 루트
│   ├── teamprime/                 # 업비트 거래 시스템
│   │   ├── source/                # 소스 코드
│   │   ├── config/                # 설정 파일 (.env, .service)
│   │   ├── venv/                  # Python 가상환경
│   │   ├── logs/                  # 앱별 로그
│   │   └── backups/               # 앱별 백업
│   ├── app2/                      # 두 번째 애플리케이션
│   ├── app3/                      # 세 번째 애플리케이션
│   ├── admin-panel/               # 관리자 패널
│   └── shared/                    # 공용 리소스
│       ├── config/                # 공용 설정
│       ├── database/              # 데이터베이스 관련
│       ├── ssl/                   # SSL 인증서
│       └── static/                # 정적 파일
├── nginx/                         # Nginx 설정
│   ├── sites-available/           # 사이트 설정 파일
│   ├── sites-enabled/             # 활성화된 사이트
│   └── ssl/                       # SSL 설정
├── logs/                          # 통합 로그 관리
│   ├── nginx/                     # Nginx 로그
│   ├── mysql/                     # MySQL 로그
│   └── apps/                      # 애플리케이션 로그
└── scripts/                       # 관리 스크립트
    ├── deployment/                # 배포 스크립트
    ├── monitoring/                # 모니터링 스크립트
    ├── backup/                    # 백업 스크립트
    └── utils/                     # 유틸리티 스크립트
```

## 🎯 포트 할당

| 애플리케이션 | 포트 | 설명 |
|------------|------|------|
| teamprime | 8001 | 업비트 자동거래 시스템 |
| app2 | 8002 | 두 번째 애플리케이션 |
| app3 | 8003 | 세 번째 애플리케이션 |
| admin-panel | 8010 | 통합 관리자 패널 |

## 🛠️ 관리 명령어

```bash
# 애플리케이션 관리
apps list                    # 모든 앱 목록
apps status [app_name]       # 앱 상태 확인
apps start [app_name]        # 앱 시작
apps stop [app_name]         # 앱 중지
apps restart [app_name]      # 앱 재시작
apps logs [app_name]         # 앱 로그 보기

# 데이터베이스 관리
dbmanager                    # 데이터베이스 초기 설정

# 시스템 헬스체크
/opt/scripts/healthcheck.sh  # 전체 시스템 상태 확인
```

## 📝 새 애플리케이션 추가 방법

1. **디렉토리 생성**: `/opt/apps/new-app/` 구조 생성
2. **환경설정**: `.env` 파일 설정
3. **데이터베이스**: 전용 DB 및 사용자 생성
4. **서비스**: systemd 서비스 파일 등록
5. **Nginx**: 프록시 설정 추가
6. **포트**: 8011+ 포트 할당

## 🔐 보안 설정

- 모든 설정 파일은 `600` 권한
- 애플리케이션은 `www-data` 사용자로 실행
- 각 앱별 독립된 데이터베이스 사용자
- 방화벽으로 필요한 포트만 개방
EOF

log_success "디렉토리 구조 문서화 완료"

# 완료 메시지
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🎉 다중 애플리케이션 디렉토리 구조 설정 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📂 생성된 구조:${NC}"
echo "✅ /opt/apps/ - 애플리케이션 루트"
echo "✅ /opt/nginx/ - Nginx 설정"
echo "✅ /opt/logs/ - 통합 로그"
echo "✅ /opt/scripts/ - 관리 스크립트"
echo ""

echo -e "${BLUE}🛠️ 생성된 도구:${NC}"
echo "✅ apps - 애플리케이션 관리 도구"
echo "✅ dbmanager - 데이터베이스 관리 도구"
echo "✅ 설정 템플릿 - 각 앱별 환경변수"
echo "✅ 서비스 템플릿 - systemd 서비스 파일"
echo ""

echo -e "${BLUE}📋 다음 단계:${NC}"
echo "1. 데이터베이스 설정: dbmanager"
echo "2. Nginx 프록시 설정"
echo "3. 애플리케이션 소스 코드 배포"
echo "4. SSL 인증서 설정"
echo ""

echo -e "${YELLOW}💡 유용한 명령어:${NC}"
echo "- 앱 목록: apps list"
echo "- 전체 상태: apps status"
echo "- 문서 보기: cat /opt/apps/README.md"
echo ""

log_success "다중 애플리케이션 환경 설정이 완료되었습니다!"