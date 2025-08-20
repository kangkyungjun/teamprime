# 🚀 Cafe24 서버 배포 가이드

업비트 자동거래 시스템을 Cafe24 서버에 배포하는 완전한 가이드입니다.

## 📋 배포 전 준비사항

### 1. Cafe24 서버 요구사항
- **Python 3.8 이상** (권장: 3.9+)
- **MySQL 데이터베이스** (5.7 이상)
- **최소 메모리**: 1GB RAM
- **최소 디스크**: 2GB 여유 공간

### 2. 필요한 Cafe24 정보 수집
- FTP/SSH 접속 정보
- MySQL 데이터베이스 정보:
  - 호스트 주소
  - 포트 (기본: 3306)
  - 데이터베이스명
  - 사용자명/비밀번호

## 🛠️ 단계별 배포 과정

### 1단계: 파일 업로드

#### 방법 A: Git 사용 (추천)
```bash
# 1. Cafe24 서버에 SSH 접속
ssh your_account@your_server.cafe24.com

# 2. 적절한 디렉토리로 이동 (예: public_html/teamprime)
cd public_html
mkdir teamprime
cd teamprime

# 3. 저장소 클론
git clone https://github.com/your_username/teamprime.git .

# 4. 불필요한 파일들이 자동으로 제외됨 (.gitignore에 의해)
```

#### 방법 B: FTP 업로드
```bash
# 로컬에서 필요한 파일만 업로드:
# - 모든 .py 파일
# - core/ 폴더 전체
# - requirements.txt
# - .env.cafe24 (나중에 .env로 이름 변경)
# - setup_mysql.sql
```

### 2단계: MySQL 데이터베이스 설정

#### phpMyAdmin 사용:
1. Cafe24 관리자 페이지 → phpMyAdmin 접속
2. `setup_mysql.sql` 파일 내용을 복사하여 실행
3. 테이블이 정상 생성되었는지 확인

#### SSH 명령어 사용:
```bash
# MySQL 접속 후 스크립트 실행
mysql -u your_username -p your_database < setup_mysql.sql
```

### 3단계: 환경 설정

#### .env 파일 생성:
```bash
# .env.cafe24를 .env로 복사
cp .env.cafe24 .env

# 실제 값으로 수정
nano .env
```

#### 필수 수정 항목:
```env
# MySQL 정보 (Cafe24에서 제공받은 정보로 수정)
MYSQL_HOST=localhost
MYSQL_DATABASE=your_actual_database_name
MYSQL_USERNAME=your_actual_username
MYSQL_PASSWORD=your_actual_password

# JWT 보안키 (반드시 변경!)
JWT_SECRET_KEY=super_strong_random_key_here_1234567890abcdef

# 포트 (Cafe24에서 허용하는 포트로 변경)
PORT=8001
```

### 4단계: Python 패키지 설치

```bash
# 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate

# 필수 패키지 설치
pip install -r requirements.txt

# 설치 확인
pip list | grep fastapi
```

### 5단계: 시스템 테스트

```bash
# 1. 데이터베이스 연결 테스트
python -c "
import asyncio
from core.database.mysql_connection import test_mysql_connection
print('테스트 결과:', asyncio.run(test_mysql_connection()))
"

# 2. 시스템 시작 테스트
python main.py
```

### 6단계: 서비스 등록 (선택사항)

#### systemd 서비스 파일 생성:
```bash
sudo nano /etc/systemd/system/teamprime.service
```

```ini
[Unit]
Description=Teamprime Trading System
After=network.target mysql.service

[Service]
Type=simple
User=your_cafe24_account
WorkingDirectory=/home/your_account/public_html/teamprime
Environment=PATH=/home/your_account/public_html/teamprime/venv/bin
ExecStart=/home/your_account/public_html/teamprime/venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### 서비스 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable teamprime
sudo systemctl start teamprime
sudo systemctl status teamprime
```

## 🌐 접속 및 확인

### 웹 브라우저 접속:
```
http://your_domain.cafe24.com:8001
```

### 기본 확인 사항:
- [ ] 로그인 페이지 정상 표시
- [ ] 회원가입 기능 작동
- [ ] 시스템 상태 API 응답: `http://your_domain.cafe24.com:8001/api/system-status`

## 🔧 문제 해결

### 자주 발생하는 문제들:

#### 1. MySQL 연결 오류
```
해결방법:
1. .env 파일의 MySQL 설정 확인
2. 방화벽에서 MySQL 포트(3306) 허용 확인
3. MySQL 서비스 실행 상태 확인: systemctl status mysql
```

#### 2. 패키지 설치 오류
```
해결방법:
1. Python 버전 확인: python3 --version
2. pip 업그레이드: pip install --upgrade pip
3. 개별 패키지 설치: pip install fastapi uvicorn
```

#### 3. 포트 접근 불가
```
해결방법:
1. Cafe24 방화벽에서 8001 포트 허용
2. 다른 포트 사용: .env에서 PORT 변경
3. nginx 프록시 설정 (필요시)
```

#### 4. 권한 오류
```
해결방법:
1. 파일 권한 확인: chmod 755 main.py
2. 디렉토리 권한 확인: chmod 755 -R core/
3. 실행 권한 부여: chmod +x main.py
```

## 📊 모니터링 및 유지보수

### 로그 확인:
```bash
# 시스템 로그
tail -f trading_system.log

# 시스템 서비스 로그
sudo journalctl -f -u teamprime
```

### 성능 모니터링:
```bash
# CPU/메모리 사용량
htop

# 디스크 사용량
df -h

# 네트워크 연결
netstat -tulpn | grep 8001
```

### 정기 점검 체크리스트:
- [ ] 디스크 용량 확인 (80% 이하 유지)
- [ ] 메모리 사용량 확인
- [ ] 데이터베이스 연결 상태
- [ ] API 응답 속도 확인
- [ ] 로그 파일 크기 관리

## 🚨 보안 고려사항

### 필수 보안 설정:
1. **강력한 JWT 시크릿 키 사용**
2. **MySQL 비밀번호 복잡성 확보**
3. **불필요한 포트 차단**
4. **정기적인 보안 업데이트**
5. **로그 모니터링**

### 권장 추가 보안:
```bash
# 1. fail2ban 설치 (무차별 공격 차단)
sudo apt install fail2ban

# 2. 방화벽 설정
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 8001/tcp

# 3. SSL 인증서 설정 (Let's Encrypt)
sudo certbot --nginx
```

## ✅ 배포 완료 체크리스트

배포가 완료되면 다음 항목들을 확인하세요:

- [ ] 웹 페이지 정상 접속 (http://도메인:8001)
- [ ] 회원가입/로그인 정상 작동
- [ ] 시스템 상태 API 정상 응답
- [ ] MySQL 데이터베이스 연결 정상
- [ ] 실시간 시세 데이터 수신 확인
- [ ] 로그 파일 생성 및 기록 확인
- [ ] SSL 인증서 설정 (HTTPS 사용시)
- [ ] 자동 재시작 서비스 등록
- [ ] 백업 정책 수립

## 📞 지원 및 문의

배포 중 문제가 발생하면:

1. **로그 파일 확인**: `trading_system.log`
2. **시스템 상태 확인**: `http://도메인:8001/api/system-status`
3. **MySQL 연결 테스트**: `python -c "from core.database.mysql_connection import test_mysql_connection; import asyncio; print(asyncio.run(test_mysql_connection()))"`

---

🎉 **배포 완료!** 이제 안전하고 안정적인 업비트 자동거래 시스템을 Cafe24에서 운영할 수 있습니다.