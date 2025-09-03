#!/bin/bash

# 🚀 Teamprime 수동 배포 스크립트
# Cafe24 서버에서 직접 실행하는 스크립트

set -e

echo "🚀 Teamprime 수동 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 파라미터 설정
DOMAIN=${1:-"teamprime.co.kr"}
GIT_REPO="https://github.com/kangkyungjun/teamprime.git"
JWT_KEY="B5kyV+90hUJE4iq3Nby7WfLpuPtktEej/mq4kKiS0GE="
MYSQL_PASSWORD="nF2VRsxEldWBsdsvYvJaMQ=="

echo -e "${BLUE}🌐 도메인: $DOMAIN${NC}"
echo -e "${BLUE}📦 저장소: $GIT_REPO${NC}"

# 1. 기존 서비스 중지
echo -e "${YELLOW}🛑 기존 서비스 중지...${NC}"
pkill -f "python.*main.py" || echo "기존 서비스가 없습니다."

# 2. 백업 생성
if [ -d "teamprime" ]; then
    echo -e "${YELLOW}📦 기존 배포 백업 생성...${NC}"
    mv teamprime "teamprime_backup_$(date +%Y%m%d_%H%M%S)"
fi

# 3. 소스 코드 클론
echo -e "${YELLOW}📥 소스 코드 다운로드...${NC}"
git clone $GIT_REPO
cd teamprime

# 4. Python 환경 설정
echo -e "${YELLOW}🐍 Python 환경 설정...${NC}"
python3 -m venv venv
source venv/bin/activate

# 5. 의존성 설치
echo -e "${YELLOW}📋 의존성 설치...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 6. 환경 설정
echo -e "${YELLOW}⚙️  환경 설정...${NC}"
cp .env.cafe24 .env

# MySQL 설정 업데이트 (사용자가 수동으로 설정해야 함)
echo -e "${BLUE}📝 .env 파일 설정이 필요합니다:${NC}"
echo -e "${BLUE}   MYSQL_USERNAME: Cafe24에서 제공한 MySQL 사용자명${NC}"
echo -e "${BLUE}   MYSQL_PASSWORD: Cafe24에서 제공한 MySQL 비밀번호${NC}"
echo -e "${BLUE}   (또는 생성된 비밀번호: $MYSQL_PASSWORD 사용)${NC}"

# JWT 키 설정
sed -i "s/CHANGE_THIS_TO_STRONG_RANDOM_SECRET_KEY_FOR_PRODUCTION/$JWT_KEY/" .env

# 7. 데이터베이스 초기화 (선택사항)
echo -e "${YELLOW}🗄️  데이터베이스 설정 (MySQL이 이미 설정되어 있다고 가정)${NC}"

# 8. 서비스 시작
echo -e "${YELLOW}🚀 서비스 시작...${NC}"
nohup python3 main.py > teamprime.log 2>&1 &

# 9. 서비스 시작 확인
sleep 5
if pgrep -f "python.*main.py" > /dev/null; then
    echo -e "${GREEN}✅ Teamprime 서비스가 성공적으로 시작되었습니다!${NC}"
    echo -e "${GREEN}🌐 웹사이트: https://$DOMAIN${NC}"
    echo -e "${GREEN}📊 API 상태: https://$DOMAIN/api/system-status${NC}"
    
    # 프로세스 정보 표시
    echo -e "${BLUE}🔍 실행 중인 프로세스:${NC}"
    pgrep -f "python.*main.py" -l
    
    echo -e "${BLUE}📋 로그 확인:${NC}"
    echo "tail -f teamprime.log"
    
else
    echo -e "${RED}❌ 서비스 시작에 실패했습니다.${NC}"
    echo -e "${RED}📋 로그 확인:${NC}"
    tail -20 teamprime.log
    exit 1
fi

echo -e "${GREEN}🎉 배포 완료!${NC}"

# 추가 설정 안내
echo -e "${BLUE}📌 추가 설정이 필요한 항목:${NC}"
echo -e "${BLUE}   1. Nginx 리버스 프록시 설정 (포트 8001 → 80/443)${NC}"
echo -e "${BLUE}   2. 방화벽에서 포트 8001 오픈${NC}"
echo -e "${BLUE}   3. SSL 인증서 확인/갱신${NC}"
echo -e "${BLUE}   4. MySQL 데이터베이스 연결 테스트${NC}"