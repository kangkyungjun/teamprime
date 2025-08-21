#!/bin/bash
# =============================================================================
# 📊 시스템 모니터링 스크립트
# =============================================================================
# 서버와 애플리케이션의 상태를 종합적으로 모니터링하는 스크립트
# 사용법: chmod +x system-monitor.sh && ./system-monitor.sh

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 설정
LOG_FILE="/opt/logs/system-monitor.log"
ALERT_LOG="/opt/logs/system-alerts.log"
REPORT_FILE="/opt/logs/system-report.html"

# 임계값 설정
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
LOAD_THRESHOLD=4.0
RESPONSE_TIME_THRESHOLD=5000  # 밀리초

# 로그 함수
log_info() {
    echo -e "${BLUE}📋 $1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') INFO: $1" >> "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') SUCCESS: $1" >> "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') WARNING: $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') WARNING: $1" >> "$ALERT_LOG"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR: $1" >> "$ALERT_LOG"
}

# 로그 디렉토리 생성
mkdir -p /opt/logs

# 헤더 출력
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${PURPLE}📊 시스템 종합 모니터링 - $(date)${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# HTML 리포트 시작
cat > "$REPORT_FILE" << 'EOF'
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>시스템 모니터링 리포트</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        .status-ok { color: #28a745; font-weight: bold; }
        .status-warning { color: #ffc107; font-weight: bold; }
        .status-error { color: #dc3545; font-weight: bold; }
        .metric-card { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007acc; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #007acc; color: white; }
        .progress-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; transition: width 0.3s ease; }
        .progress-ok { background: #28a745; }
        .progress-warning { background: #ffc107; }
        .progress-error { background: #dc3545; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ 시스템 모니터링 리포트</h1>
            <p>생성 시간: <span id="timestamp"></span></p>
        </div>
EOF

echo "<script>document.getElementById('timestamp').textContent = new Date().toLocaleString('ko-KR');</script>" >> "$REPORT_FILE"

# 1. 시스템 기본 정보
log_info "1. 시스템 기본 정보 수집 중..."

HOSTNAME=$(hostname)
UPTIME=$(uptime | awk -F'up ' '{print $2}' | awk -F', load' '{print $1}')
KERNEL=$(uname -r)
OS_INFO=$(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')
CPU_INFO=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
TOTAL_MEMORY=$(free -h | awk 'NR==2{print $2}')

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🖥️ 시스템 정보</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>항목</th><th>값</th></tr>" >> "$REPORT_FILE"
echo "<tr><td>호스트명</td><td>$HOSTNAME</td></tr>" >> "$REPORT_FILE"
echo "<tr><td>가동시간</td><td>$UPTIME</td></tr>" >> "$REPORT_FILE"
echo "<tr><td>운영체제</td><td>$OS_INFO</td></tr>" >> "$REPORT_FILE"
echo "<tr><td>커널</td><td>$KERNEL</td></tr>" >> "$REPORT_FILE"
echo "<tr><td>CPU</td><td>$CPU_INFO</td></tr>" >> "$REPORT_FILE"
echo "<tr><td>메모리</td><td>$TOTAL_MEMORY</td></tr>" >> "$REPORT_FILE"
echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

log_success "시스템 기본 정보 수집 완료"

# 2. CPU 사용률 모니터링
log_info "2. CPU 사용률 모니터링 중..."

CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
CPU_USAGE_INT=${CPU_USAGE%.*}  # 소수점 제거

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>💻 CPU 사용률</h3>" >> "$REPORT_FILE"

if [ "$CPU_USAGE_INT" -gt "$CPU_THRESHOLD" ]; then
    log_error "CPU 사용률이 임계값을 초과했습니다: ${CPU_USAGE}% (임계값: ${CPU_THRESHOLD}%)"
    echo "<p class='status-error'>❌ CPU 사용률: ${CPU_USAGE}% (위험)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-error' style='width: ${CPU_USAGE}%'></div></div>" >> "$REPORT_FILE"
elif [ "$CPU_USAGE_INT" -gt $((CPU_THRESHOLD - 10)) ]; then
    log_warning "CPU 사용률이 높습니다: ${CPU_USAGE}%"
    echo "<p class='status-warning'>⚠️ CPU 사용률: ${CPU_USAGE}% (주의)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-warning' style='width: ${CPU_USAGE}%'></div></div>" >> "$REPORT_FILE"
else
    log_success "CPU 사용률 정상: ${CPU_USAGE}%"
    echo "<p class='status-ok'>✅ CPU 사용률: ${CPU_USAGE}% (정상)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-ok' style='width: ${CPU_USAGE}%'></div></div>" >> "$REPORT_FILE"
fi

echo "</div>" >> "$REPORT_FILE"

# 3. 메모리 사용률 모니터링
log_info "3. 메모리 사용률 모니터링 중..."

MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/($3+$4)}')

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🧠 메모리 사용률</h3>" >> "$REPORT_FILE"

if [ "$MEMORY_USAGE" -gt "$MEMORY_THRESHOLD" ]; then
    log_error "메모리 사용률이 임계값을 초과했습니다: ${MEMORY_USAGE}% (임계값: ${MEMORY_THRESHOLD}%)"
    echo "<p class='status-error'>❌ 메모리 사용률: ${MEMORY_USAGE}% (위험)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-error' style='width: ${MEMORY_USAGE}%'></div></div>" >> "$REPORT_FILE"
elif [ "$MEMORY_USAGE" -gt $((MEMORY_THRESHOLD - 10)) ]; then
    log_warning "메모리 사용률이 높습니다: ${MEMORY_USAGE}%"
    echo "<p class='status-warning'>⚠️ 메모리 사용률: ${MEMORY_USAGE}% (주의)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-warning' style='width: ${MEMORY_USAGE}%'></div></div>" >> "$REPORT_FILE"
else
    log_success "메모리 사용률 정상: ${MEMORY_USAGE}%"
    echo "<p class='status-ok'>✅ 메모리 사용률: ${MEMORY_USAGE}% (정상)</p>" >> "$REPORT_FILE"
    echo "<div class='progress-bar'><div class='progress-fill progress-ok' style='width: ${MEMORY_USAGE}%'></div></div>" >> "$REPORT_FILE"
fi

# 메모리 세부 정보
MEMORY_DETAILS=$(free -h)
echo "<pre>$MEMORY_DETAILS</pre>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 4. 디스크 사용률 모니터링
log_info "4. 디스크 사용률 모니터링 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>💾 디스크 사용률</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>파일시스템</th><th>크기</th><th>사용량</th><th>여유공간</th><th>사용률</th><th>마운트</th><th>상태</th></tr>" >> "$REPORT_FILE"

df -h | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{print $1,$2,$3,$4,$5,$6}' | while read output; do
    filesystem=$(echo $output | awk '{print $1}')
    size=$(echo $output | awk '{print $2}')
    used=$(echo $output | awk '{print $3}')
    avail=$(echo $output | awk '{print $4}')
    usage_percent=$(echo $output | awk '{print $5}' | sed 's/%//')
    mount=$(echo $output | awk '{print $6}')
    
    if [ "$usage_percent" -gt "$DISK_THRESHOLD" ]; then
        log_error "디스크 사용률이 임계값을 초과했습니다: $filesystem ${usage_percent}% (임계값: ${DISK_THRESHOLD}%)"
        status="<span class='status-error'>❌ 위험</span>"
    elif [ "$usage_percent" -gt $((DISK_THRESHOLD - 10)) ]; then
        log_warning "디스크 사용률이 높습니다: $filesystem ${usage_percent}%"
        status="<span class='status-warning'>⚠️ 주의</span>"
    else
        status="<span class='status-ok'>✅ 정상</span>"
    fi
    
    echo "<tr><td>$filesystem</td><td>$size</td><td>$used</td><td>$avail</td><td>${usage_percent}%</td><td>$mount</td><td>$status</td></tr>" >> "$REPORT_FILE"
done

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 5. 로드 애버리지 모니터링
log_info "5. 시스템 로드 모니터링 중..."

LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
LOAD_1MIN=$(echo "$LOAD_AVG" | cut -d. -f1)

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>⚡ 시스템 로드</h3>" >> "$REPORT_FILE"

if (( $(echo "$LOAD_1MIN > $LOAD_THRESHOLD" | bc -l) )); then
    log_error "시스템 로드가 임계값을 초과했습니다: $LOAD_AVG (임계값: $LOAD_THRESHOLD)"
    echo "<p class='status-error'>❌ 로드 애버리지: $LOAD_AVG (위험)</p>" >> "$REPORT_FILE"
elif (( $(echo "$LOAD_1MIN > $(echo "$LOAD_THRESHOLD - 1" | bc)" | bc -l) )); then
    log_warning "시스템 로드가 높습니다: $LOAD_AVG"
    echo "<p class='status-warning'>⚠️ 로드 애버리지: $LOAD_AVG (주의)</p>" >> "$REPORT_FILE"
else
    log_success "시스템 로드 정상: $LOAD_AVG"
    echo "<p class='status-ok'>✅ 로드 애버리지: $LOAD_AVG (정상)</p>" >> "$REPORT_FILE"
fi

echo "</div>" >> "$REPORT_FILE"

# 6. 네트워크 연결 모니터링
log_info "6. 네트워크 연결 모니터링 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🌐 네트워크 연결</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>포트</th><th>상태</th><th>프로세스</th></tr>" >> "$REPORT_FILE"

IMPORTANT_PORTS=(80 443 22 3306 6379 8001 8002 8003 8010)

for port in "${IMPORTANT_PORTS[@]}"; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        process=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | head -1)
        echo "<tr><td>$port</td><td class='status-ok'>✅ 열림</td><td>$process</td></tr>" >> "$REPORT_FILE"
    else
        echo "<tr><td>$port</td><td class='status-error'>❌ 닫힘</td><td>-</td></tr>" >> "$REPORT_FILE"
        if [ "$port" -eq 8001 ]; then
            log_warning "Teamprime 애플리케이션 포트 $port가 닫혀있습니다"
        fi
    fi
done

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 7. 서비스 상태 모니터링
log_info "7. 주요 서비스 상태 모니터링 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🔧 서비스 상태</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>서비스</th><th>상태</th><th>활성화</th><th>설명</th></tr>" >> "$REPORT_FILE"

SERVICES=("nginx" "mysql" "redis-server" "teamprime" "ufw" "fail2ban")

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        active_status="<span class='status-ok'>✅ 실행중</span>"
    else
        active_status="<span class='status-error'>❌ 중지됨</span>"
        log_error "서비스 '$service'가 중지되었습니다"
    fi
    
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        enabled_status="<span class='status-ok'>✅ 활성화</span>"
    else
        enabled_status="<span class='status-warning'>⚠️ 비활성화</span>"
    fi
    
    case "$service" in
        "nginx") description="웹 서버" ;;
        "mysql") description="데이터베이스" ;;
        "redis-server") description="캐시 서버" ;;
        "teamprime") description="거래 시스템" ;;
        "ufw") description="방화벽" ;;
        "fail2ban") description="침입 차단" ;;
        *) description="시스템 서비스" ;;
    esac
    
    echo "<tr><td>$service</td><td>$active_status</td><td>$enabled_status</td><td>$description</td></tr>" >> "$REPORT_FILE"
done

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 8. 애플리케이션 헬스 체크
log_info "8. 애플리케이션 헬스 체크 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🚀 애플리케이션 상태</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>애플리케이션</th><th>포트</th><th>응답시간</th><th>상태</th></tr>" >> "$REPORT_FILE"

APPS=("teamprime:8001" "app2:8002" "app3:8003" "admin:8010")

for app_port in "${APPS[@]}"; do
    app=$(echo "$app_port" | cut -d: -f1)
    port=$(echo "$app_port" | cut -d: -f2)
    
    # HTTP 응답시간 측정
    start_time=$(date +%s%3N)
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" 2>/dev/null | grep -q "200"; then
        end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))
        
        if [ "$response_time" -gt "$RESPONSE_TIME_THRESHOLD" ]; then
            status="<span class='status-warning'>⚠️ 느림</span>"
            log_warning "$app 애플리케이션 응답이 느립니다: ${response_time}ms"
        else
            status="<span class='status-ok'>✅ 정상</span>"
            log_success "$app 애플리케이션 정상: ${response_time}ms"
        fi
        
        echo "<tr><td>$app</td><td>$port</td><td>${response_time}ms</td><td>$status</td></tr>" >> "$REPORT_FILE"
    else
        echo "<tr><td>$app</td><td>$port</td><td>-</td><td><span class='status-error'>❌ 응답없음</span></td></tr>" >> "$REPORT_FILE"
        if [ "$app" = "teamprime" ]; then
            log_error "Teamprime 애플리케이션이 응답하지 않습니다"
        fi
    fi
done

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 9. SSL 인증서 상태 체크
log_info "9. SSL 인증서 상태 체크 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🔐 SSL 인증서 상태</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>도메인</th><th>만료일</th><th>남은 일수</th><th>상태</th></tr>" >> "$REPORT_FILE"

if [ -d "/opt/ssl" ]; then
    for cert_file in /opt/ssl/*.crt; do
        if [ -f "$cert_file" ]; then
            domain=$(basename "$cert_file" .crt)
            
            if [ -L "$cert_file" ] && [ ! -e "$cert_file" ]; then
                # 심볼릭 링크가 깨진 경우
                echo "<tr><td>$domain</td><td>-</td><td>-</td><td><span class='status-error'>❌ 링크 오류</span></td></tr>" >> "$REPORT_FILE"
                log_error "SSL 인증서 링크가 깨졌습니다: $domain"
                continue
            fi
            
            expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
            if [ -n "$expiry_date" ]; then
                expiry_epoch=$(date -d "$expiry_date" +%s)
                current_epoch=$(date +%s)
                days_left=$(( (expiry_epoch - current_epoch) / 86400 ))
                
                if [ "$days_left" -le 7 ]; then
                    status="<span class='status-error'>❌ 만료 임박</span>"
                    log_error "SSL 인증서가 곧 만료됩니다: $domain (${days_left}일 남음)"
                elif [ "$days_left" -le 30 ]; then
                    status="<span class='status-warning'>⚠️ 갱신 필요</span>"
                    log_warning "SSL 인증서 갱신이 필요합니다: $domain (${days_left}일 남음)"
                else
                    status="<span class='status-ok'>✅ 정상</span>"
                fi
                
                formatted_date=$(date -d "$expiry_date" "+%Y-%m-%d")
                echo "<tr><td>$domain</td><td>$formatted_date</td><td>${days_left}일</td><td>$status</td></tr>" >> "$REPORT_FILE"
            else
                echo "<tr><td>$domain</td><td>-</td><td>-</td><td><span class='status-error'>❌ 읽기 오류</span></td></tr>" >> "$REPORT_FILE"
                log_error "SSL 인증서를 읽을 수 없습니다: $domain"
            fi
        fi
    done
else
    echo "<tr><td colspan='4'>SSL 인증서가 설치되지 않았습니다</td></tr>" >> "$REPORT_FILE"
fi

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# 10. 보안 상태 체크
log_info "10. 보안 상태 체크 중..."

echo "<div class='metric-card'>" >> "$REPORT_FILE"
echo "<h3>🛡️ 보안 상태</h3>" >> "$REPORT_FILE"
echo "<table>" >> "$REPORT_FILE"
echo "<tr><th>보안 항목</th><th>상태</th><th>설명</th></tr>" >> "$REPORT_FILE"

# UFW 방화벽 상태
if ufw status | grep -q "Status: active"; then
    echo "<tr><td>방화벽</td><td class='status-ok'>✅ 활성화</td><td>UFW 방화벽이 실행 중입니다</td></tr>" >> "$REPORT_FILE"
else
    echo "<tr><td>방화벽</td><td class='status-error'>❌ 비활성화</td><td>UFW 방화벽이 비활성화되었습니다</td></tr>" >> "$REPORT_FILE"
    log_error "방화벽이 비활성화되어 있습니다"
fi

# Fail2ban 상태
if systemctl is-active --quiet fail2ban; then
    banned_ips=$(fail2ban-client status sshd 2>/dev/null | grep "Banned IP list" | wc -l)
    echo "<tr><td>침입 차단</td><td class='status-ok'>✅ 활성화</td><td>Fail2ban이 실행 중입니다</td></tr>" >> "$REPORT_FILE"
else
    echo "<tr><td>침입 차단</td><td class='status-error'>❌ 비활성화</td><td>Fail2ban이 비활성화되었습니다</td></tr>" >> "$REPORT_FILE"
    log_error "Fail2ban이 비활성화되어 있습니다"
fi

# 시스템 업데이트 상태
if command -v apt >/dev/null 2>&1; then
    updates=$(apt list --upgradable 2>/dev/null | wc -l)
    if [ "$updates" -gt 10 ]; then
        echo "<tr><td>시스템 업데이트</td><td class='status-warning'>⚠️ 필요</td><td>${updates}개의 업데이트가 있습니다</td></tr>" >> "$REPORT_FILE"
        log_warning "시스템 업데이트가 필요합니다: ${updates}개 패키지"
    else
        echo "<tr><td>시스템 업데이트</td><td class='status-ok'>✅ 최신</td><td>시스템이 최신 상태입니다</td></tr>" >> "$REPORT_FILE"
    fi
fi

echo "</table>" >> "$REPORT_FILE"
echo "</div>" >> "$REPORT_FILE"

# HTML 리포트 마무리
cat >> "$REPORT_FILE" << 'EOF'
        <div class="metric-card">
            <h3>📋 요약</h3>
            <p>이 리포트는 시스템의 현재 상태를 종합적으로 분석한 결과입니다.</p>
            <p>⚠️ 표시된 경고나 ❌ 표시된 오류 항목은 즉시 확인하여 조치하시기 바랍니다.</p>
            <p><strong>다음 모니터링 시간:</strong> <span id="next-check"></span></p>
        </div>
    </div>
    
    <script>
        // 다음 체크 시간 (1시간 후)
        var nextCheck = new Date();
        nextCheck.setHours(nextCheck.getHours() + 1);
        document.getElementById('next-check').textContent = nextCheck.toLocaleString('ko-KR');
    </script>
</body>
</html>
EOF

log_success "HTML 모니터링 리포트 생성 완료: $REPORT_FILE"

# 11. 알림 요약
log_info "11. 모니터링 결과 요약 중..."

ALERT_COUNT=$(grep -c "ERROR\|WARNING" "$ALERT_LOG" 2>/dev/null || echo 0)

echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${BLUE}📊 모니터링 결과 요약${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

if [ "$ALERT_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 시스템이 정상적으로 작동하고 있습니다!${NC}"
else
    echo -e "${YELLOW}⚠️ $ALERT_COUNT개의 경고 또는 오류가 발견되었습니다.${NC}"
    echo -e "${YELLOW}자세한 내용은 다음 로그를 확인하세요:${NC}"
    echo -e "${BLUE}- 시스템 로그: $LOG_FILE${NC}"
    echo -e "${BLUE}- 알림 로그: $ALERT_LOG${NC}"
    echo -e "${BLUE}- HTML 리포트: $REPORT_FILE${NC}"
fi

echo ""
echo -e "${BLUE}📋 리포트 파일:${NC}"
echo "- 시스템 로그: $LOG_FILE"
echo "- 알림 로그: $ALERT_LOG"
echo "- HTML 리포트: $REPORT_FILE"
echo ""
echo -e "${BLUE}💡 유용한 명령어:${NC}"
echo "- 실시간 리소스 확인: htop"
echo "- 서비스 상태 확인: systemctl status [service-name]"
echo "- 디스크 사용량 확인: df -h"
echo "- 네트워크 연결 확인: netstat -tlnp"
echo "- 로그 실시간 보기: tail -f $LOG_FILE"

log_success "시스템 모니터링 완료"