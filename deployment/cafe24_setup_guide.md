# 🏗️ Cafe24 서버 초기 설정 가이드

## 서버 연결 문제 해결 후 진행사항

현재 teamprime.co.kr (172.233.87.201) 서버에 접근할 수 없는 상태입니다.
Cafe24 콘솔에서 다음 설정을 완료해야 합니다.

## 1단계: Cafe24 콘솔 기본 설정

### 서버 상태 확인 및 시작
```
1. Cafe24 호스팅 콘솔 (https://hosting.cafe24.com) 로그인
2. "내 서비스 관리" → "호스팅 관리" 이동
3. teamprime.co.kr 도메인 선택
4. 서버 상태 확인 (전원 ON/OFF)
5. 서버가 꺼져있다면 "시작" 버튼 클릭
```

### 방화벽/보안그룹 설정
```
필수 포트 오픈:
- 포트 22: SSH 접속용
- 포트 80: HTTP 웹서비스  
- 포트 443: HTTPS 웹서비스
- 포트 8001: Teamprime 애플리케이션

설정 위치:
"보안설정" → "방화벽 설정" → "포트 관리"
```

## 2단계: SSH 접속 설정

### SSH 계정 생성
```
1. Cafe24 콘솔에서 "SSH 관리" 메뉴 찾기
2. SSH 사용자 계정 생성
3. 공개키 등록 (teamprime_deploy_key.pub 내용)
4. 또는 비밀번호 방식으로 설정
```

### SSH 접속 테스트
```bash
# 공개키 방식
ssh -i teamprime_deploy_key root@172.233.87.201

# 또는 사용자명으로
ssh -i teamprime_deploy_key username@172.233.87.201

# 비밀번호 방식
ssh username@172.233.87.201
```

## 3단계: 서버 기본 환경 설정

### 필수 패키지 설치
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 3.9+ 설치
sudo apt install python3 python3-pip python3-venv -y

# Git 설치
sudo apt install git -y

# 개발 도구 설치
sudo apt install build-essential python3-dev -y

# Nginx 설치 (리버스 프록시용)
sudo apt install nginx -y
```

### MySQL 설정
```bash
# MySQL 설치 (Cafe24에서 제공하는 경우 생략)
sudo apt install mysql-server -y

# 데이터베이스 생성
mysql -u root -p
```

```sql
CREATE DATABASE teamprime_trading;
CREATE USER 'teamprime'@'localhost' IDENTIFIED BY 'nF2VRsxEldWBsdsvYvJaMQ==';
GRANT ALL PRIVILEGES ON teamprime_trading.* TO 'teamprime'@'localhost';
FLUSH PRIVILEGES;
exit;
```

## 4단계: Teamprime 배포

### 자동 배포 스크립트 실행
```bash
# root 권한으로 전환
sudo su -

# 배포 스크립트 다운로드
curl -o manual_deploy.sh https://raw.githubusercontent.com/kangkyungjun/teamprime/master/deployment/manual_deploy.sh

# 실행 권한 부여
chmod +x manual_deploy.sh

# 배포 실행
./manual_deploy.sh teamprime.co.kr
```

### 수동 배포 (스크립트 실패시)
```bash
# 프로젝트 클론
git clone https://github.com/kangkyungjun/teamprime.git
cd teamprime

# Python 가상환경
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp .env.cafe24 .env

# .env 파일 편집 (MySQL 정보)
nano .env
```

## 5단계: Nginx 리버스 프록시 설정

### Nginx 설정 파일 생성
```bash
sudo nano /etc/nginx/sites-available/teamprime
```

```nginx
server {
    listen 80;
    server_name teamprime.co.kr www.teamprime.co.kr;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Nginx 활성화
```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/teamprime /etc/nginx/sites-enabled/

# 기본 사이트 비활성화
sudo rm /etc/nginx/sites-enabled/default

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

## 6단계: SSL 인증서 설정

### Let's Encrypt 인증서 발급
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# SSL 인증서 발급 및 자동 설정
sudo certbot --nginx -d teamprime.co.kr -d www.teamprime.co.kr
```

## 7단계: 서비스 시작 및 자동 시작 설정

### Teamprime 서비스 시작
```bash
cd /home/username/teamprime  # 또는 설치한 경로
source venv/bin/activate
nohup python3 main.py > teamprime.log 2>&1 &
```

### systemd 서비스 등록 (선택사항)
```bash
sudo nano /etc/systemd/system/teamprime.service
```

```ini
[Unit]
Description=Teamprime Trading System
After=network.target mysql.service

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/teamprime
Environment=PATH=/home/username/teamprime/venv/bin
ExecStart=/home/username/teamprime/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable teamprime
sudo systemctl start teamprime
```

## 8단계: 배포 확인

### 서비스 상태 확인
```bash
# 프로세스 확인
ps aux | grep python3

# 포트 확인
netstat -tlnp | grep 8001

# 로그 확인
tail -f teamprime.log
```

### 웹사이트 접속 테스트
- http://teamprime.co.kr (HTTP)
- https://teamprime.co.kr (HTTPS)
- https://teamprime.co.kr/api/system-status (API)

## 문제 해결

### 일반적인 문제들

**포트 8001 접근 불가**
```bash
# 방화벽 확인
sudo ufw status
sudo ufw allow 8001
```

**MySQL 연결 오류**
```bash
# MySQL 서비스 상태
sudo systemctl status mysql

# 연결 테스트
mysql -u teamprime -p teamprime_trading
```

**Python 의존성 오류**
```bash
# 시스템 패키지 설치
sudo apt install python3-dev libmysqlclient-dev
```

---

## 체크리스트 ✅

배포 완료 후 다음 항목들을 확인하세요:

- [ ] 서버 ping 응답 성공
- [ ] HTTP (포트 80) 접근 가능  
- [ ] HTTPS (포트 443) 접근 가능
- [ ] SSH (포트 22) 접근 가능
- [ ] Teamprime 애플리케이션 (포트 8001) 실행 중
- [ ] MySQL 데이터베이스 연결 성공
- [ ] Nginx 리버스 프록시 정상 작동
- [ ] SSL 인증서 정상 발급
- [ ] 웹사이트 접속 가능
- [ ] API 엔드포인트 응답 정상