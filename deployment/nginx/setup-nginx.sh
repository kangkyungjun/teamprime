#!/bin/bash
# =============================================================================
# 🌐 Nginx 다중 앱 설정 자동화 스크립트
# =============================================================================
# 모든 애플리케이션의 Nginx 설정을 자동으로 구성합니다.

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
echo -e "${PURPLE}🌐 Nginx 다중 애플리케이션 설정 자동화${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    exit 1
fi

# 기본 경로 설정
NGINX_ROOT="/opt/nginx"
SITES_AVAILABLE="$NGINX_ROOT/sites-available"
SITES_ENABLED="$NGINX_ROOT/sites-enabled"
TEMPLATES="$NGINX_ROOT/templates"

# 사용자 입력받기
read -p "메인 도메인을 입력하세요 (예: yourdomain.com): " MAIN_DOMAIN
if [ -z "$MAIN_DOMAIN" ]; then
    log_error "도메인은 필수입니다."
    exit 1
fi

log_info "설정할 도메인: $MAIN_DOMAIN"
echo ""

# 1단계: 기본 Nginx 설정 복사
log_info "1단계: Nginx 메인 설정 파일 복사 중..."

# 기존 nginx.conf 백업
if [ -f /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# 새 설정 파일 복사
cp nginx.conf /etc/nginx/nginx.conf

log_success "Nginx 메인 설정 복사 완료"

# 2단계: 사이트 설정 파일 생성
log_info "2단계: 애플리케이션별 사이트 설정 생성 중..."

# Teamprime 설정 파일 생성 및 도메인 치환
sed "s/yourdomain.com/$MAIN_DOMAIN/g" sites-available/teamprime.conf > $SITES_AVAILABLE/teamprime.conf

# App2 설정 생성
cat > $SITES_AVAILABLE/app2.conf << EOF
server {
    listen 80;
    server_name app2.$MAIN_DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app2.$MAIN_DOMAIN;
    
    ssl_certificate /opt/ssl/app2.$MAIN_DOMAIN.crt;
    ssl_certificate_key /opt/ssl/app2.$MAIN_DOMAIN.key;
    
    access_log /opt/logs/nginx/app2.access.log detailed;
    error_log /opt/logs/nginx/app2.error.log;
    
    location / {
        limit_req zone=general burst=50 nodelay;
        proxy_pass http://app2_backend;
        include /opt/nginx/templates/proxy_params.conf;
    }
    
    location /health {
        access_log off;
        proxy_pass http://app2_backend/health;
    }
}
EOF

# App3 설정 생성
cat > $SITES_AVAILABLE/app3.conf << EOF
server {
    listen 80;
    server_name app3.$MAIN_DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app3.$MAIN_DOMAIN;
    
    ssl_certificate /opt/ssl/app3.$MAIN_DOMAIN.crt;
    ssl_certificate_key /opt/ssl/app3.$MAIN_DOMAIN.key;
    
    access_log /opt/logs/nginx/app3.access.log detailed;
    error_log /opt/logs/nginx/app3.error.log;
    
    location / {
        limit_req zone=general burst=50 nodelay;
        proxy_pass http://app3_backend;
        include /opt/nginx/templates/proxy_params.conf;
    }
    
    location /health {
        access_log off;
        proxy_pass http://app3_backend/health;
    }
}
EOF

# Admin Panel 설정 생성
cat > $SITES_AVAILABLE/admin.conf << EOF
server {
    listen 80;
    server_name admin.$MAIN_DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name admin.$MAIN_DOMAIN;
    
    ssl_certificate /opt/ssl/admin.$MAIN_DOMAIN.crt;
    ssl_certificate_key /opt/ssl/admin.$MAIN_DOMAIN.key;
    
    access_log /opt/logs/nginx/admin.access.log detailed;
    error_log /opt/logs/nginx/admin.error.log;
    
    # 관리자 패널은 더 강한 보안 적용
    location / {
        limit_req zone=login burst=10 nodelay;
        
        # 특정 IP만 허용 (필요시 설정)
        # allow 192.168.1.0/24;
        # allow 127.0.0.1;
        # deny all;
        
        proxy_pass http://admin_backend;
        include /opt/nginx/templates/proxy_params.conf;
    }
    
    location /health {
        access_log off;
        proxy_pass http://admin_backend/health;
    }
}
EOF

log_success "애플리케이션별 사이트 설정 생성 완료"

# 3단계: 메인 도메인 설정 (선택사항)
log_info "3단계: 메인 도메인 설정 생성 중..."

cat > $SITES_AVAILABLE/main.conf << EOF
server {
    listen 80;
    server_name $MAIN_DOMAIN www.$MAIN_DOMAIN;
    return 301 https://trading.$MAIN_DOMAIN\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $MAIN_DOMAIN www.$MAIN_DOMAIN;
    
    ssl_certificate /opt/ssl/$MAIN_DOMAIN.crt;
    ssl_certificate_key /opt/ssl/$MAIN_DOMAIN.key;
    
    # 메인 도메인은 trading 서브도메인으로 리다이렉트
    return 301 https://trading.$MAIN_DOMAIN\$request_uri;
}
EOF

log_success "메인 도메인 설정 생성 완료"

# 4단계: 사이트 활성화
log_info "4단계: 사이트 설정 활성화 중..."

# 기존 심볼릭 링크 정리
rm -f $SITES_ENABLED/*

# 새 심볼릭 링크 생성
ln -sf $SITES_AVAILABLE/teamprime.conf $SITES_ENABLED/
ln -sf $SITES_AVAILABLE/app2.conf $SITES_ENABLED/
ln -sf $SITES_AVAILABLE/app3.conf $SITES_ENABLED/
ln -sf $SITES_AVAILABLE/admin.conf $SITES_ENABLED/
ln -sf $SITES_AVAILABLE/main.conf $SITES_ENABLED/

log_success "사이트 설정 활성화 완료"

# 5단계: 로그 디렉토리 생성
log_info "5단계: 로그 디렉토리 생성 중..."

mkdir -p /opt/logs/nginx
touch /opt/logs/nginx/teamprime.access.log
touch /opt/logs/nginx/teamprime.error.log
touch /opt/logs/nginx/app2.access.log
touch /opt/logs/nginx/app2.error.log
touch /opt/logs/nginx/app3.access.log
touch /opt/logs/nginx/app3.error.log
touch /opt/logs/nginx/admin.access.log
touch /opt/logs/nginx/admin.error.log
touch /opt/logs/nginx/access.log
touch /opt/logs/nginx/error.log

chown -R www-data:www-data /opt/logs/nginx
chmod -R 644 /opt/logs/nginx/*.log

log_success "로그 디렉토리 생성 완료"

# 6단계: SSL 디렉토리 생성 (임시)
log_info "6단계: SSL 디렉토리 생성 중..."

mkdir -p /opt/ssl
chmod 700 /opt/ssl

# 임시 자체 서명 인증서 생성 (테스트용)
if command -v openssl >/dev/null 2>&1; then
    log_info "임시 자체 서명 SSL 인증서 생성 중..."
    
    for subdomain in "trading" "app2" "app3" "admin" ""; do
        if [ -z "$subdomain" ]; then
            domain="$MAIN_DOMAIN"
        else
            domain="$subdomain.$MAIN_DOMAIN"
        fi
        
        if [ ! -f "/opt/ssl/$domain.crt" ]; then
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout "/opt/ssl/$domain.key" \
                -out "/opt/ssl/$domain.crt" \
                -subj "/C=KR/ST=Seoul/L=Seoul/O=Organization/OU=OrgUnit/CN=$domain" \
                >/dev/null 2>&1
        fi
    done
    
    chmod 600 /opt/ssl/*.key
    chmod 644 /opt/ssl/*.crt
    
    log_warning "임시 자체 서명 인증서가 생성되었습니다. 실제 운영환경에서는 Let's Encrypt를 사용하세요."
fi

log_success "SSL 디렉토리 준비 완료"

# 7단계: Nginx 설정 문법 검사
log_info "7단계: Nginx 설정 문법 검사 중..."

if nginx -t; then
    log_success "Nginx 설정 문법 검사 통과"
else
    log_error "Nginx 설정에 오류가 있습니다."
    exit 1
fi

# 8단계: Nginx 서비스 재시작
log_info "8단계: Nginx 서비스 재시작 중..."

systemctl reload nginx
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    log_success "Nginx 서비스 재시작 완료"
else
    log_error "Nginx 서비스 시작 실패"
    systemctl status nginx
    exit 1
fi

# 9단계: 설정 상태 확인
log_info "9단계: 설정 상태 확인 중..."

echo ""
echo -e "${BLUE}📊 생성된 사이트 설정:${NC}"
ls -la $SITES_ENABLED/

echo ""
echo -e "${BLUE}🌐 설정된 도메인:${NC}"
echo "✅ https://trading.$MAIN_DOMAIN (Teamprime - 포트 8001)"
echo "✅ https://app2.$MAIN_DOMAIN (App2 - 포트 8002)"
echo "✅ https://app3.$MAIN_DOMAIN (App3 - 포트 8003)"
echo "✅ https://admin.$MAIN_DOMAIN (Admin Panel - 포트 8010)"
echo "✅ https://$MAIN_DOMAIN (메인 - trading으로 리다이렉트)"

echo ""
echo -e "${BLUE}🔍 포트 상태 확인:${NC}"
netstat -tlnp | grep nginx | head -5

# 완료 메시지
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🎉 Nginx 다중 애플리케이션 설정 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📋 설정 완료 사항:${NC}"
echo "✅ Nginx 메인 설정 최적화 완료"
echo "✅ 4개 애플리케이션 프록시 설정 완료"
echo "✅ SSL/TLS 설정 준비 완료 (임시 인증서)"
echo "✅ Rate Limiting 및 보안 설정 완료"
echo "✅ 로그 파일 및 모니터링 준비 완료"
echo ""

echo -e "${YELLOW}🚨 다음 단계:${NC}"
echo "1. DNS 설정: 각 서브도메인을 서버 IP로 연결"
echo "2. Let's Encrypt SSL 인증서 설치"
echo "3. 애플리케이션 서버 시작 (포트 8001, 8002, 8003, 8010)"
echo "4. 방화벽에서 HTTP/HTTPS 포트 허용 확인"
echo ""

echo -e "${BLUE}💡 유용한 명령어:${NC}"
echo "- Nginx 상태: systemctl status nginx"
echo "- 설정 테스트: nginx -t"
echo "- 로그 확인: tail -f /opt/logs/nginx/access.log"
echo "- 사이트 활성화: ln -sf /opt/nginx/sites-available/[site] /opt/nginx/sites-enabled/"
echo ""

log_success "Nginx 설정이 성공적으로 완료되었습니다!"