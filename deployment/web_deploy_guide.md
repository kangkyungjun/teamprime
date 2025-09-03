# 🌐 Cafe24 웹 배포 가이드

## SSH 접속 제한 문제 해결

Cafe24 서버 SSH 직접 접속이 제한되어 있을 수 있습니다. 다음 방법들로 배포를 진행할 수 있습니다:

## 방법 1: Cafe24 웹 콘솔 사용

1. **Cafe24 호스팅 콘솔** (https://hosting.cafe24.com) 접속
2. **파일관리자** 또는 **SSH 터미널** 메뉴 찾기
3. 웹 기반 터미널에서 다음 명령어 실행:

```bash
# 프로젝트 클론
cd /home/teamprime  # 또는 웹루트 디렉토리
git clone https://github.com/kangkyungjun/teamprime.git
cd teamprime

# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치  
pip install -r requirements.txt

# 환경 설정
cp .env.cafe24 .env
# .env 파일 편집 (MySQL 정보 입력)

# 서비스 시작 (백그라운드)
nohup python3 main.py > teamprime.log 2>&1 &
```

## 방법 2: FTP를 통한 파일 업로드

1. **파일 준비** (로컬에서):
```bash
# 압축 파일 생성
tar -czf teamprime_deploy.tar.gz --exclude='.git' --exclude='__pycache__' .
```

2. **FTP 업로드**:
   - FTP 클라이언트 (FileZilla 등) 사용
   - 또는 Cafe24 웹 파일관리자 사용

3. **서버에서 압축 해제**:
```bash
cd /home/teamprime
tar -xzf teamprime_deploy.tar.gz
```

## 방법 3: GitHub Actions 자동 배포 설정

GitHub Actions을 통한 자동 배포 파이프라인을 설정할 수 있습니다.

## 필수 서버 설정

### 1. MySQL 데이터베이스 생성
```sql
CREATE DATABASE teamprime_trading;
CREATE USER 'teamprime'@'localhost' IDENTIFIED BY 'nF2VRsxEldWBsdsvYvJaMQ==';
GRANT ALL PRIVILEGES ON teamprime_trading.* TO 'teamprime'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Nginx 설정 (리버스 프록시)
```nginx
server {
    listen 80;
    server_name teamprime.co.kr;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL 인증서 (Let's Encrypt)
```bash
certbot --nginx -d teamprime.co.kr
```

## 배포 후 확인사항

1. **서비스 상태 확인**:
```bash
ps aux | grep python3
netstat -tlnp | grep 8001
```

2. **웹사이트 접속**:
   - https://teamprime.co.kr
   - https://teamprime.co.kr/api/system-status

3. **로그 확인**:
```bash
tail -f teamprime.log
```

## 트러블슈팅

### 포트 8001이 차단된 경우
```bash
# 방화벽 설정
sudo ufw allow 8001
# 또는 Cafe24 보안그룹에서 8001 포트 오픈
```

### Python 버전 문제
```bash
# Python 3.9+ 설치 확인
python3 --version
# 필요시 업데이트
```

### 의존성 설치 오류
```bash
# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade
# 개발 도구 설치
sudo apt install python3-dev python3-pip build-essential
```