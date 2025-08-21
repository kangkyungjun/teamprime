#!/bin/bash
# =============================================================================
# 🚀 Cafe24 서버 통합 배포 마스터 스크립트
# =============================================================================
# SSH root@172.233.87.201 서버에 다중 애플리케이션 환경을 완전 자동 배포
# 사용법: chmod +x deploy.sh && ./deploy.sh

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 로그 함수
log_step() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}📋 STEP $1: $2${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

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

log_critical() {
    echo -e "${RED}🚨 CRITICAL: $1${NC}"
    echo -e "${RED}배포를 중단합니다.${NC}"
    exit 1
}

# 배포 시작 헤더
clear
cat << 'EOF'
████████╗███████╗ █████╗ ███╗   ███╗██████╗ ██████╗ ██╗███╗   ███╗███████╗
╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██╔══██╗██╔══██╗██║████╗ ████║██╔════╝
   ██║   █████╗  ███████║██╔████╔██║██████╔╝██████╔╝██║██╔████╔██║█████╗  
   ██║   ██╔══╝  ██╔══██║██║╚██╔╝██║██╔═══╝ ██╔══██╗██║██║╚██╔╝██║██╔══╝  
   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║     ██║  ██║██║██║ ╚═╝ ██║███████╗
   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝
                                                                           
EOF

echo -e "${PURPLE}=================================================================${NC}"
echo -e "${PURPLE}🚀 Cafe24 서버 통합 배포 시스템${NC}"
echo -e "${PURPLE}🌐 다중 애플리케이션 자동 배포 및 설정${NC}"
echo -e "${PURPLE}📅 $(date '+%Y년 %m월 %d일 %H시 %M분')${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_critical "이 스크립트는 root 권한으로 실행해야 합니다."
fi

# 시스템 정보 표시
log_info "서버 정보:"
echo "- 호스트: $(hostname)"
echo "- OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "- 커널: $(uname -r)"
echo "- CPU: $(nproc) cores"
echo "- 메모리: $(free -h | awk 'NR==2{print $2}')"
echo "- 디스크: $(df -h / | awk 'NR==2{print $4}') 여유공간"
echo ""

# 배포 설정 입력
echo -e "${BLUE}📋 배포 설정을 입력해주세요${NC}"
echo ""

# 필수 정보 수집
read -p "메인 도메인을 입력하세요 (예: teamprime.com): " MAIN_DOMAIN
if [ -z "$MAIN_DOMAIN" ]; then
    log_critical "도메인은 필수입니다."
fi

read -p "관리자 이메일을 입력하세요 (SSL 인증서용): " ADMIN_EMAIL
if [ -z "$ADMIN_EMAIL" ]; then
    log_critical "관리자 이메일은 필수입니다."
fi

read -p "GitHub 저장소 URL을 입력하세요: " GITHUB_REPO
if [ -z "$GITHUB_REPO" ]; then
    log_critical "GitHub 저장소 URL은 필수입니다."
fi

read -p "배포할 브랜치를 입력하세요 (기본값: main): " BRANCH
BRANCH=${BRANCH:-main}

read -s -p "MySQL 데이터베이스 비밀번호를 입력하세요: " DB_PASSWORD
echo ""
if [ ${#DB_PASSWORD} -lt 8 ]; then
    log_critical "데이터베이스 비밀번호는 최소 8자 이상이어야 합니다."
fi

read -s -p "JWT Secret Key를 입력하세요 (최소 32자): " JWT_SECRET
echo ""
if [ ${#JWT_SECRET} -lt 32 ]; then
    log_critical "JWT Secret Key는 최소 32자 이상이어야 합니다."
fi

# 배포 옵션 선택
echo ""
echo -e "${BLUE}📋 배포 옵션을 선택하세요${NC}"
read -p "SSL 인증서를 설치하시겠습니까? [Y/n]: " INSTALL_SSL
INSTALL_SSL=${INSTALL_SSL:-Y}

read -p "모니터링 시스템을 설치하시겠습니까? [Y/n]: " INSTALL_MONITORING
INSTALL_MONITORING=${INSTALL_MONITORING:-Y}

read -p "샘플 앱 2, 3을 함께 설치하시겠습니까? [y/N]: " INSTALL_SAMPLE_APPS
INSTALL_SAMPLE_APPS=${INSTALL_SAMPLE_APPS:-N}

echo ""
echo -e "${BLUE}📋 배포 설정 확인${NC}"
echo "- 도메인: $MAIN_DOMAIN"
echo "- 이메일: $ADMIN_EMAIL"  
echo "- 저장소: $GITHUB_REPO"
echo "- 브랜치: $BRANCH"
echo "- SSL 설치: $INSTALL_SSL"
echo "- 모니터링: $INSTALL_MONITORING"
echo "- 샘플 앱: $INSTALL_SAMPLE_APPS"

echo ""
read -p "위 설정으로 배포를 진행하시겠습니까? [Y/n]: " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$|^$ ]]; then
    log_info "배포를 취소합니다."
    exit 0
fi

# 배포 로그 설정
DEPLOY_LOG="/opt/logs/deployment.log"
mkdir -p /opt/logs
exec > >(tee -a "$DEPLOY_LOG")
exec 2>&1

log_info "배포 로그: $DEPLOY_LOG"

# =============================================================================
# STEP 1: 서버 환경 구축
# =============================================================================

log_step "1" "서버 기본 환경 구축"

log_info "시스템 업데이트 및 기본 패키지 설치 중..."
if ! ./server-setup.sh; then
    log_critical "서버 환경 구축에 실패했습니다."
fi

log_success "서버 기본 환경 구축 완료"

# =============================================================================
# STEP 2: 다중 앱 디렉토리 구조 설정
# =============================================================================

log_step "2" "다중 애플리케이션 디렉토리 구조 설정"

log_info "애플리케이션 디렉토리 구조 생성 중..."
if ! ./setup-multi-apps.sh; then
    log_critical "디렉토리 구조 설정에 실패했습니다."
fi

log_success "디렉토리 구조 설정 완료"

# =============================================================================
# STEP 3: 데이터베이스 설정
# =============================================================================

log_step "3" "데이터베이스 초기 설정"

log_info "데이터베이스 및 사용자 생성 중..."
if ! /opt/scripts/utils/db-manager.sh; then
    log_warning "데이터베이스 자동 생성에 실패했습니다. 수동으로 설정하세요."
fi

log_success "데이터베이스 설정 완료"

# =============================================================================
# STEP 4: Nginx 프록시 설정
# =============================================================================

log_step "4" "Nginx Reverse Proxy 설정"

log_info "Nginx 다중 앱 프록시 설정 중..."
cd nginx
if ! echo "$MAIN_DOMAIN" | ./setup-nginx.sh; then
    log_critical "Nginx 설정에 실패했습니다."
fi
cd ..

log_success "Nginx 프록시 설정 완료"

# =============================================================================
# STEP 5: Teamprime 애플리케이션 배포
# =============================================================================

log_step "5" "Teamprime 애플리케이션 배포"

log_info "Teamprime 업비트 거래 시스템 배포 중..."

# 환경변수 전달
export GITHUB_REPO
export BRANCH
export DB_PASSWORD
export JWT_SECRET

if ! ./deploy-teamprime.sh; then
    log_critical "Teamprime 애플리케이션 배포에 실패했습니다."
fi

log_success "Teamprime 애플리케이션 배포 완료"

# =============================================================================
# STEP 6: SSL 인증서 설치 (선택사항)
# =============================================================================

if [[ "$INSTALL_SSL" =~ ^[Yy]$|^$ ]]; then
    log_step "6" "SSL 인증서 설치"
    
    log_info "Let's Encrypt SSL 인증서 설치 중..."
    
    # 환경변수 전달
    export MAIN_DOMAIN
    export ADMIN_EMAIL
    
    if ! ./setup-ssl.sh; then
        log_warning "SSL 인증서 설치에 실패했습니다. 나중에 수동으로 설치하세요."
    else
        log_success "SSL 인증서 설치 완료"
    fi
else
    log_info "SSL 인증서 설치를 건너뛰었습니다."
fi

# =============================================================================
# STEP 7: 샘플 애플리케이션 설치 (선택사항)
# =============================================================================

if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    log_step "7" "샘플 애플리케이션 설치"
    
    log_info "App2, App3 샘플 애플리케이션 생성 중..."
    
    # App2 샘플 생성
    mkdir -p /opt/apps/app2/source
    cat > /opt/apps/app2/source/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="App2 Sample", version="1.0.0")

@app.get("/")
async def root():
    return HTMLResponse("""
    <html><head><title>App2 Sample</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🌟 App2 Sample Application</h1>
        <p>This is a sample application running on port 8002</p>
        <p>Time: <script>document.write(new Date().toLocaleString());</script></p>
    </body></html>
    """)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "app2", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
EOF

    # App3 샘플 생성
    mkdir -p /opt/apps/app3/source
    cat > /opt/apps/app3/source/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="App3 Sample", version="1.0.0")

@app.get("/")
async def root():
    return HTMLResponse("""
    <html><head><title>App3 Sample</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🎯 App3 Sample Application</h1>
        <p>This is a sample application running on port 8003</p>
        <p>Time: <script>document.write(new Date().toLocaleString());</script></p>
    </body></html>
    """)

@app.get("/health")
async def health():
    return {"status": "ok", "app": "app3", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
EOF

    # 가상환경 및 서비스 설정
    for app in app2 app3; do
        port=$((8000 + ${app: -1} + 1))
        python3 -m venv "/opt/apps/$app/venv"
        source "/opt/apps/$app/venv/bin/activate"
        pip install fastapi uvicorn
        
        # systemd 서비스 생성
        cat > "/etc/systemd/system/$app.service" << EOF
[Unit]
Description=$app Sample Application
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/apps/$app/source
Environment=PATH=/opt/apps/$app/venv/bin
ExecStart=/opt/apps/$app/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        
        # 권한 설정
        chown -R www-data:www-data "/opt/apps/$app"
        
        # 서비스 시작
        systemctl daemon-reload
        systemctl enable "$app"
        systemctl start "$app"
    done
    
    log_success "샘플 애플리케이션 설치 완료"
else
    log_info "샘플 애플리케이션 설치를 건너뛰었습니다."
fi

# =============================================================================
# STEP 8: 모니터링 시스템 설치 (선택사항)
# =============================================================================

if [[ "$INSTALL_MONITORING" =~ ^[Yy]$|^$ ]]; then
    log_step "8" "모니터링 시스템 설치"
    
    log_info "시스템 모니터링 스크립트 설치 중..."
    
    # 모니터링 스크립트 복사
    cp monitoring/system-monitor.sh /opt/scripts/
    chmod +x /opt/scripts/system-monitor.sh
    
    # 모니터링 cron 작업 추가 (매시간)
    if ! crontab -l | grep -q "system-monitor.sh"; then
        (crontab -l 2>/dev/null; echo "0 * * * * /opt/scripts/system-monitor.sh >/dev/null 2>&1") | crontab -
        log_info "시간당 자동 모니터링 cron 작업이 추가되었습니다."
    fi
    
    # 심볼릭 링크 생성
    ln -sf /opt/scripts/system-monitor.sh /usr/local/bin/monitor
    
    log_success "모니터링 시스템 설치 완료"
else
    log_info "모니터링 시스템 설치를 건너뛰었습니다."
fi

# =============================================================================
# STEP 9: 최종 시스템 검증
# =============================================================================

log_step "9" "최종 시스템 검증 및 테스트"

log_info "전체 시스템 상태 확인 중..."

# 서비스 상태 확인
SERVICES=("nginx" "mysql" "redis-server" "teamprime")
if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    SERVICES+=("app2" "app3")
fi

failed_services=()
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        log_success "$service 서비스 정상 실행 중"
    else
        log_error "$service 서비스 실행 실패"
        failed_services+=("$service")
    fi
done

# 포트 상태 확인
PORTS=(80 443 8001)
if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    PORTS+=(8002 8003)
fi

for port in "${PORTS[@]}"; do
    if netstat -tlnp | grep -q ":$port "; then
        log_success "포트 $port 정상 바인딩됨"
    else
        log_warning "포트 $port 바인딩되지 않음"
    fi
done

# 애플리케이션 헬스 체크
log_info "애플리케이션 헬스 체크 중..."
sleep 5

HEALTH_ENDPOINTS=("localhost:8001/api/system-status")
if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    HEALTH_ENDPOINTS+=("localhost:8002/health" "localhost:8003/health")
fi

for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
    if curl -s "http://$endpoint" >/dev/null; then
        log_success "$endpoint 헬스 체크 성공"
    else
        log_warning "$endpoint 헬스 체크 실패"
    fi
done

# SSL 인증서 확인
if [[ "$INSTALL_SSL" =~ ^[Yy]$|^$ ]]; then
    log_info "SSL 인증서 상태 확인 중..."
    if [ -f "/opt/ssl/$MAIN_DOMAIN.crt" ]; then
        expiry=$(openssl x509 -in "/opt/ssl/$MAIN_DOMAIN.crt" -noout -enddate | cut -d= -f2)
        log_success "SSL 인증서 설치됨 (만료일: $expiry)"
    else
        log_warning "SSL 인증서가 설치되지 않았습니다"
    fi
fi

log_success "최종 시스템 검증 완료"

# =============================================================================
# STEP 10: 배포 완료 및 정보 정리
# =============================================================================

log_step "10" "배포 완료 정리"

# 배포 정보 생성
cat > /opt/DEPLOYMENT_SUMMARY.md << EOF
# 🚀 Teamprime 다중 애플리케이션 배포 완료

## 📋 배포 정보
- **배포 일시**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **서버**: $(hostname) ($(curl -s ipinfo.io/ip || echo "IP 확인 실패"))
- **도메인**: $MAIN_DOMAIN
- **GitHub**: $GITHUB_REPO (브랜치: $BRANCH)

## 🌐 접속 정보

### 웹 애플리케이션
- **Teamprime 거래 시스템**: https://trading.$MAIN_DOMAIN (포트: 8001)
EOF

if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    cat >> /opt/DEPLOYMENT_SUMMARY.md << EOF
- **App2 샘플**: https://app2.$MAIN_DOMAIN (포트: 8002)
- **App3 샘플**: https://app3.$MAIN_DOMAIN (포트: 8003)
EOF
fi

cat >> /opt/DEPLOYMENT_SUMMARY.md << EOF

### 관리 인터페이스
- **시스템 모니터링**: /opt/logs/system-report.html
- **서버 상태**: /opt/scripts/healthcheck.sh

## 🔧 관리 명령어

### 애플리케이션 관리
\`\`\`bash
# 전체 앱 상태 확인
apps status

# 특정 앱 관리
apps start teamprime
apps stop teamprime  
apps restart teamprime
apps logs teamprime

# 시스템 모니터링
monitor
\`\`\`

### 서비스 관리  
\`\`\`bash
# 서비스 상태 확인
systemctl status nginx mysql redis-server teamprime

# Nginx 설정 테스트
nginx -t

# 로그 확인
tail -f /opt/logs/nginx/access.log
journalctl -u teamprime -f
\`\`\`

### SSL 인증서 관리
\`\`\`bash
# 인증서 상태 확인
/opt/scripts/check-ssl-expiry.sh

# 수동 갱신
/opt/scripts/renew-ssl.sh
\`\`\`

## 📊 모니터링 대시보드

### 자동 생성 리포트
- **시스템 리포트**: /opt/logs/system-report.html
- **모니터링 로그**: /opt/logs/system-monitor.log
- **배포 로그**: /opt/logs/deployment.log

## 🛡️ 보안 설정

### 방화벽 (UFW)
- SSH (22), HTTP (80), HTTPS (443)
- 애플리케이션 포트: 8001-8010

### 침입 차단 (Fail2ban)
- SSH 무차별 대입 공격 차단
- Nginx 기반 공격 차단

### SSL/TLS
- Let's Encrypt 인증서 (자동 갱신)
- TLS 1.2/1.3 only
- HSTS 헤더 적용

## 📞 문제 해결

### 자주 발생하는 문제
1. **애플리케이션 접속 불가**
   - 서비스 상태: \`systemctl status teamprime\`
   - 포트 확인: \`netstat -tlnp | grep 8001\`

2. **SSL 인증서 오류**
   - 인증서 확인: \`/opt/scripts/check-ssl-expiry.sh\`
   - 갱신 시도: \`/opt/scripts/renew-ssl.sh\`

3. **데이터베이스 연결 오류**
   - MySQL 상태: \`systemctl status mysql\`
   - 연결 테스트: 애플리케이션 로그 확인

### 로그 위치
- **애플리케이션**: /opt/logs/apps/teamprime/
- **Nginx**: /opt/logs/nginx/
- **시스템**: /var/log/syslog
- **MySQL**: /var/log/mysql/error.log

---
**배포 완료 시간**: $(date)
EOF

# 배포 요약 출력
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🎉 Teamprime 다중 애플리케이션 배포 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📊 배포 결과 요약:${NC}"
echo "✅ 서버 환경: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "✅ 도메인: $MAIN_DOMAIN"
echo "✅ 애플리케이션: Teamprime 업비트 자동거래 시스템"
if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    echo "✅ 샘플 앱: App2, App3"
fi
echo "✅ SSL 인증서: $([[ "$INSTALL_SSL" =~ ^[Yy]$|^$ ]] && echo "설치됨" || echo "건너뜀")"
echo "✅ 모니터링: $([[ "$INSTALL_MONITORING" =~ ^[Yy]$|^$ ]] && echo "설치됨" || echo "건너뜀")"
echo ""

echo -e "${BLUE}🌐 접속 URL:${NC}"
echo "- Teamprime: https://trading.$MAIN_DOMAIN"
if [[ "$INSTALL_SAMPLE_APPS" =~ ^[Yy]$ ]]; then
    echo "- App2: https://app2.$MAIN_DOMAIN"
    echo "- App3: https://app3.$MAIN_DOMAIN" 
fi
echo ""

echo -e "${BLUE}🔧 관리 도구:${NC}"
echo "- 앱 관리: apps [command]"
echo "- 시스템 모니터링: monitor"
echo "- 헬스 체크: /opt/scripts/healthcheck.sh"
echo "- 배포 요약: cat /opt/DEPLOYMENT_SUMMARY.md"
echo ""

echo -e "${BLUE}📋 중요 파일:${NC}"
echo "- 배포 요약: /opt/DEPLOYMENT_SUMMARY.md"
echo "- 배포 로그: /opt/logs/deployment.log"
echo "- 모니터링 리포트: /opt/logs/system-report.html"
echo ""

if [ ${#failed_services[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️ 주의사항:${NC}"
    echo "다음 서비스에서 문제가 발생했습니다: ${failed_services[*]}"
    echo "각 서비스의 상태를 확인하고 필요시 재시작하세요."
    echo ""
fi

echo -e "${YELLOW}🚨 다음 단계:${NC}"
echo "1. DNS 설정: 각 서브도메인을 이 서버 IP로 연결"
echo "2. 업비트 API 키 설정 (Teamprime 웹 인터페이스에서)"
echo "3. 시스템 모니터링 대시보드 확인"
echo "4. SSL 인증서 작동 확인"
echo "5. 정기적인 백업 및 모니터링 확인"
echo ""

log_success "🎉 모든 배포 과정이 성공적으로 완료되었습니다!"
log_info "배포 소요 시간: $((SECONDS / 60))분 $((SECONDS % 60))초"

# 최종 상태 리포트 실행
if [[ "$INSTALL_MONITORING" =~ ^[Yy]$|^$ ]]; then
    log_info "최종 시스템 상태 리포트 생성 중..."
    /opt/scripts/system-monitor.sh >/dev/null 2>&1 || true
    echo "📊 시스템 리포트가 생성되었습니다: /opt/logs/system-report.html"
fi

echo ""
echo -e "${CYAN}🎯 배포 완료! 성공적인 운영을 위해 정기적인 모니터링을 권장합니다.${NC}"