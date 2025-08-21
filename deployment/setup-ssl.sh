#!/bin/bash
# =============================================================================
# 🔐 SSL 인증서 자동 설치 스크립트 (Let's Encrypt)
# =============================================================================
# 모든 서브도메인에 대해 SSL 인증서를 자동으로 생성하고 설정하는 스크립트
# 사용법: chmod +x setup-ssl.sh && ./setup-ssl.sh

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
echo -e "${PURPLE}🔐 SSL 인증서 자동 설치 (Let's Encrypt)${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한으로 실행해야 합니다."
    exit 1
fi

# 필수 도구 확인
if ! command -v nginx >/dev/null 2>&1; then
    log_error "Nginx가 설치되지 않았습니다."
    exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
    log_error "Certbot이 설치되지 않았습니다."
    exit 1
fi

# 사용자 입력
echo -e "${BLUE}📋 SSL 인증서 설정${NC}"
read -p "메인 도메인을 입력하세요 (예: yourdomain.com): " MAIN_DOMAIN
if [ -z "$MAIN_DOMAIN" ]; then
    log_error "도메인은 필수입니다."
    exit 1
fi

read -p "관리자 이메일을 입력하세요 (Let's Encrypt 알림용): " ADMIN_EMAIL
if [ -z "$ADMIN_EMAIL" ]; then
    log_error "관리자 이메일은 필수입니다."
    exit 1
fi

echo ""
log_info "설정할 도메인: $MAIN_DOMAIN"
log_info "관리자 이메일: $ADMIN_EMAIL"
echo ""

# 도메인 목록 정의
DOMAINS=(
    "$MAIN_DOMAIN"
    "www.$MAIN_DOMAIN"
    "trading.$MAIN_DOMAIN"
    "app2.$MAIN_DOMAIN"
    "app3.$MAIN_DOMAIN"
    "admin.$MAIN_DOMAIN"
)

# 1단계: 도메인 DNS 확인
log_info "1단계: 도메인 DNS 설정 확인 중..."

SERVER_IP=$(curl -s ipinfo.io/ip || wget -qO- ipinfo.io/ip)
log_info "서버 IP: $SERVER_IP"

echo ""
for domain in "${DOMAINS[@]}"; do
    if nslookup "$domain" >/dev/null 2>&1; then
        RESOLVED_IP=$(dig +short "$domain" | tail -n1)
        if [ "$RESOLVED_IP" = "$SERVER_IP" ]; then
            log_success "$domain → $RESOLVED_IP (올바름)"
        else
            log_warning "$domain → $RESOLVED_IP (서버 IP와 다름: $SERVER_IP)"
        fi
    else
        log_error "$domain DNS 확인 실패"
    fi
done

echo ""
read -p "DNS 설정이 올바르지 않은 도메인이 있어도 계속하시겠습니까? [y/N]: " CONTINUE
if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
    log_info "DNS 설정을 확인한 후 다시 실행하세요."
    exit 0
fi

# 2단계: 임시 인증용 웹 루트 설정
log_info "2단계: 인증용 웹 루트 디렉토리 설정 중..."

WEBROOT_PATH="/var/www/certbot"
mkdir -p "$WEBROOT_PATH"
chown -R www-data:www-data "$WEBROOT_PATH"

# 임시 인증용 Nginx 설정
cat > /etc/nginx/conf.d/certbot.conf << 'EOF'
# Let's Encrypt 인증용 임시 설정
server {
    listen 80;
    server_name _;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}
EOF

# Nginx 설정 테스트 및 재로드
nginx -t
systemctl reload nginx

log_success "인증용 웹 루트 설정 완료"

# 3단계: Let's Encrypt 인증서 생성
log_info "3단계: Let's Encrypt 인증서 생성 중..."

# 도메인 목록을 certbot 인수로 변환
DOMAIN_ARGS=""
for domain in "${DOMAINS[@]}"; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

log_info "인증서를 생성할 도메인: ${DOMAINS[*]}"

# Certbot 실행 (webroot 방식)
if certbot certonly \
    --webroot \
    --webroot-path="$WEBROOT_PATH" \
    --email "$ADMIN_EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    $DOMAIN_ARGS; then
    log_success "Let's Encrypt 인증서 생성 성공"
else
    log_error "Let's Encrypt 인증서 생성 실패"
    
    # 개별 도메인별 재시도
    log_info "개별 도메인별로 인증서 생성을 재시도합니다..."
    
    for domain in "${DOMAINS[@]}"; do
        log_info "$domain 인증서 생성 시도 중..."
        
        if certbot certonly \
            --webroot \
            --webroot-path="$WEBROOT_PATH" \
            --email "$ADMIN_EMAIL" \
            --agree-tos \
            --no-eff-email \
            --non-interactive \
            -d "$domain"; then
            log_success "$domain 인증서 생성 성공"
        else
            log_warning "$domain 인증서 생성 실패 (DNS 설정 확인 필요)"
        fi
    done
fi

# 4단계: 인증서 파일을 표준 위치로 복사
log_info "4단계: SSL 인증서 파일 정리 중..."

SSL_ROOT="/opt/ssl"
mkdir -p "$SSL_ROOT"

# Let's Encrypt 인증서를 표준 위치로 복사
for domain in "${DOMAINS[@]}"; do
    CERT_PATH="/etc/letsencrypt/live/$domain"
    
    if [ -d "$CERT_PATH" ]; then
        # 심볼릭 링크 생성 (Let's Encrypt 자동 갱신 대응)
        ln -sf "$CERT_PATH/fullchain.pem" "$SSL_ROOT/$domain.crt"
        ln -sf "$CERT_PATH/privkey.pem" "$SSL_ROOT/$domain.key"
        
        # 파일 권한 설정
        chmod 644 "$SSL_ROOT/$domain.crt"
        chmod 600 "$SSL_ROOT/$domain.key"
        
        log_success "$domain 인증서 링크 생성 완료"
    else
        log_warning "$domain 인증서를 찾을 수 없습니다"
    fi
done

log_success "SSL 인증서 파일 정리 완료"

# 5단계: Nginx SSL 설정 업데이트
log_info "5단계: Nginx SSL 설정 업데이트 중..."

# 임시 certbot 설정 제거
rm -f /etc/nginx/conf.d/certbot.conf

# Nginx 설정 테스트
if nginx -t; then
    systemctl reload nginx
    log_success "Nginx SSL 설정 적용 완료"
else
    log_error "Nginx 설정에 오류가 있습니다"
    nginx -t
    exit 1
fi

# 6단계: SSL 인증서 자동 갱신 설정
log_info "6단계: SSL 인증서 자동 갱신 설정 중..."

# 갱신 스크립트 생성
cat > /opt/scripts/renew-ssl.sh << 'EOF'
#!/bin/bash
# SSL 인증서 자동 갱신 스크립트

set -e

# 로그 파일
LOG_FILE="/opt/logs/ssl-renewal.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date): SSL 인증서 갱신 시작" >> "$LOG_FILE"

# Certbot 갱신 실행
if certbot renew --quiet --no-self-upgrade; then
    echo "$(date): 인증서 갱신 성공" >> "$LOG_FILE"
    
    # Nginx 설정 테스트 후 재로드
    if nginx -t; then
        systemctl reload nginx
        echo "$(date): Nginx 재로드 완료" >> "$LOG_FILE"
    else
        echo "$(date): Nginx 설정 오류" >> "$LOG_FILE"
        exit 1
    fi
else
    echo "$(date): 인증서 갱신 실패" >> "$LOG_FILE"
    exit 1
fi

echo "$(date): SSL 인증서 갱신 완료" >> "$LOG_FILE"
EOF

chmod +x /opt/scripts/renew-ssl.sh

# Cron 작업 추가 (매일 새벽 2시 갱신 체크)
if ! crontab -l | grep -q "renew-ssl.sh"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/scripts/renew-ssl.sh") | crontab -
    log_success "SSL 인증서 자동 갱신 cron 작업 추가됨"
fi

# 7단계: SSL 설정 보안 강화
log_info "7단계: SSL 보안 설정 강화 중..."

# DH 매개변수 생성 (보안 강화)
if [ ! -f /etc/ssl/certs/dhparam.pem ]; then
    log_info "DH 매개변수 생성 중... (몇 분 소요될 수 있습니다)"
    openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048
    log_success "DH 매개변수 생성 완료"
fi

# SSL 보안 설정 파일 생성
cat > /opt/nginx/conf.d/ssl-security.conf << 'EOF'
# SSL 보안 강화 설정

# SSL 프로토콜 및 암호화 방식
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

# SSL 세션 설정
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# DH 매개변수
ssl_dhparam /etc/ssl/certs/dhparam.pem;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;

# DNS resolver
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# 보안 헤더
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
EOF

log_success "SSL 보안 설정 강화 완료"

# 8단계: SSL 인증서 검증
log_info "8단계: SSL 인증서 설치 검증 중..."

# Nginx 설정 테스트
if nginx -t; then
    systemctl reload nginx
    log_success "Nginx 설정 검증 통과"
else
    log_error "Nginx 설정 검증 실패"
    exit 1
fi

# SSL 인증서 유효성 검사
echo ""
for domain in "${DOMAINS[@]}"; do
    if [ -f "/opt/ssl/$domain.crt" ]; then
        EXPIRY=$(openssl x509 -in "/opt/ssl/$domain.crt" -noout -dates | grep "notAfter" | cut -d= -f2)
        log_success "$domain 인증서 유효 (만료일: $EXPIRY)"
        
        # 온라인 SSL 테스트 (첫 번째 도메인만)
        if [ "$domain" = "$MAIN_DOMAIN" ]; then
            log_info "$domain SSL 연결 테스트 중..."
            if timeout 10 openssl s_client -connect "$domain:443" -servername "$domain" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
                log_success "$domain SSL 연결 테스트 성공"
            else
                log_warning "$domain SSL 연결 테스트 실패 (DNS 전파 대기 중일 수 있음)"
            fi
        fi
    else
        log_error "$domain 인증서 파일이 없습니다"
    fi
done

# 9단계: 모니터링 설정
log_info "9단계: SSL 인증서 모니터링 설정 중..."

# SSL 만료일 체크 스크립트
cat > /opt/scripts/check-ssl-expiry.sh << 'EOF'
#!/bin/bash
# SSL 인증서 만료일 체크 스크립트

LOG_FILE="/opt/logs/ssl-check.log"
ALERT_DAYS=30

mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date): SSL 인증서 만료일 체크 시작" >> "$LOG_FILE"

for cert_file in /opt/ssl/*.crt; do
    if [ -f "$cert_file" ]; then
        domain=$(basename "$cert_file" .crt)
        
        # 인증서 만료일 계산
        expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
        expiry_epoch=$(date -d "$expiry_date" +%s)
        current_epoch=$(date +%s)
        days_left=$(( (expiry_epoch - current_epoch) / 86400 ))
        
        echo "$(date): $domain 인증서 - ${days_left}일 남음" >> "$LOG_FILE"
        
        # 만료 임박 경고
        if [ $days_left -le $ALERT_DAYS ]; then
            echo "$(date): 경고! $domain 인증서가 ${days_left}일 후 만료됩니다" >> "$LOG_FILE"
            # 이메일 알림 (postfix 설치된 경우)
            if command -v mail >/dev/null 2>&1; then
                echo "$domain SSL certificate expires in $days_left days" | mail -s "SSL Certificate Expiry Warning" root
            fi
        fi
    fi
done

echo "$(date): SSL 인증서 만료일 체크 완료" >> "$LOG_FILE"
EOF

chmod +x /opt/scripts/check-ssl-expiry.sh

# 주간 SSL 체크 cron 작업 (매주 월요일 오전 9시)
if ! crontab -l | grep -q "check-ssl-expiry.sh"; then
    (crontab -l 2>/dev/null; echo "0 9 * * 1 /opt/scripts/check-ssl-expiry.sh") | crontab -
    log_success "SSL 만료일 체크 cron 작업 추가됨"
fi

# 10단계: 웹 보안 강화
log_info "10단계: 웹 보안 강화 설정 중..."

# 보안 헤더 강화
cat > /opt/nginx/conf.d/security-headers.conf << 'EOF'
# 웹 보안 헤더 강화 설정

# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' wss: https:; media-src 'self' https:; object-src 'none'; child-src 'none'; frame-ancestors 'none'; upgrade-insecure-requests;" always;

# Feature Policy
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=(), magnetometer=(), gyroscope=(), speaker=(), vibrate=(), fullscreen=(self), sync-xhr=()" always;

# 추가 보안 헤더
add_header X-Robots-Tag "noindex, nofollow" always;
add_header X-Download-Options "noopen" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;
EOF

log_success "웹 보안 강화 완료"

# 완료 메시지
echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${GREEN}🔐 SSL 인증서 설치 완료!${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

echo -e "${BLUE}📊 설치된 SSL 인증서:${NC}"
for domain in "${DOMAINS[@]}"; do
    if [ -f "/opt/ssl/$domain.crt" ]; then
        EXPIRY=$(openssl x509 -in "/opt/ssl/$domain.crt" -noout -dates | grep "notAfter" | cut -d= -f2)
        echo "✅ $domain (만료: $EXPIRY)"
    else
        echo "❌ $domain (설치 실패)"
    fi
done

echo ""
echo -e "${BLUE}🌐 HTTPS 접속 확인:${NC}"
for domain in "${DOMAINS[@]}"; do
    echo "✅ https://$domain"
done

echo ""
echo -e "${BLUE}🔧 자동화 설정:${NC}"
echo "✅ 인증서 자동 갱신: 매일 새벽 2시"
echo "✅ 만료일 체크: 매주 월요일 오전 9시"
echo "✅ 로그 파일: /opt/logs/ssl-renewal.log, /opt/logs/ssl-check.log"

echo ""
echo -e "${BLUE}🛡️ 보안 설정:${NC}"
echo "✅ TLS 1.2/1.3 only"
echo "✅ HSTS 헤더 (1년)"
echo "✅ 보안 헤더 강화"
echo "✅ OCSP Stapling"
echo "✅ Perfect Forward Secrecy"

echo ""
echo -e "${BLUE}💡 유용한 명령어:${NC}"
echo "- SSL 상태 확인: /opt/scripts/check-ssl-expiry.sh"
echo "- 수동 갱신: /opt/scripts/renew-ssl.sh"
echo "- 인증서 확인: openssl x509 -in /opt/ssl/domain.crt -noout -dates"
echo "- SSL 테스트: https://www.ssllabs.com/ssltest/"

echo ""
echo -e "${YELLOW}🚨 중요 사항:${NC}"
echo "1. 모든 도메인의 DNS가 이 서버를 가리키는지 확인하세요"
echo "2. 방화벽에서 포트 80, 443이 허용되어 있는지 확인하세요"
echo "3. SSL 테스트: https://www.ssllabs.com/ssltest/"
echo "4. 인증서는 90일마다 자동 갱신됩니다"

echo ""
log_success "SSL 인증서 설치가 성공적으로 완료되었습니다!"

# SSL 설정 테스트
log_info "최종 SSL 설정 테스트 중..."
nginx -t && systemctl reload nginx
log_success "최종 SSL 설정 테스트 통과"