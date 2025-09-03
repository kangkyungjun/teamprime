# 🚀 Cafe24 서버 배포 지침

## 준비된 자격 증명
- **JWT Secret Key**: `B5kyV+90hUJE4iq3Nby7WfLpuPtktEej/mq4kKiS0GE=`
- **MySQL Password**: `nF2VRsxEldWBsdsvYvJaMQ==`
- **SSH 공개키**: `teamprime_deploy_key.pub` (준비 완료)
- **SSH 개인키**: `teamprime_deploy_key` (준비 완료)

## 배포 단계

### 1. Cafe24 서버 SSH 접속
Cafe24 콘솔에서 SSH 계정 생성 후:
```bash
ssh username@teamprime.co.kr
# 또는
ssh username@서버IP주소
```

### 2. 서버에서 배포 실행
```bash
# root 권한으로 전환
sudo su -

# 배포 스크립트 다운로드 및 실행
curl -o deploy.sh https://raw.githubusercontent.com/kangkyungjun/teamprime/master/deployment/deploy.sh
chmod +x deploy.sh

# 자동 배포 실행
./deploy.sh \
  --domain teamprime.co.kr \
  --git-repo https://github.com/kangkyungjun/teamprime.git \
  --jwt-key "B5kyV+90hUJE4iq3Nby7WfLpuPtktEej/mq4kKiS0GE=" \
  --mysql-password "nF2VRsxEldWBsdsvYvJaMQ==" \
  --admin-email admin@teamprime.co.kr
```

### 3. 배포 완료 후 확인
- **웹 대시보드**: https://teamprime.co.kr
- **API 상태**: https://teamprime.co.kr/api/system-status
- **SSL 인증서**: 자동 구성됨 (Let's Encrypt)

## 필요한 Cafe24 설정

### MySQL 데이터베이스
- 데이터베이스명: `teamprime_trading`
- 사용자명: Cafe24 콘솔에서 확인
- 비밀번호: 위에서 생성된 값 또는 Cafe24에서 설정

### 도메인 설정
- 도메인: `teamprime.co.kr` (이미 SSL 설정 완료)
- A 레코드가 서버 IP를 가리키고 있는지 확인

## 수동 배포 (필요시)

서버에서 수동으로 배포하려면:

```bash
# 1. Python 3.9+ 설치 확인
python3 --version

# 2. 프로젝트 클론
git clone https://github.com/kangkyungjun/teamprime.git
cd teamprime

# 3. 의존성 설치
pip3 install -r requirements.txt

# 4. 환경 설정
cp .env.cafe24 .env
# .env 파일에서 MySQL 설정 수정

# 5. 서비스 시작
python3 main.py
```

## 문제 해결

### 배포 실패시
1. 서버 로그 확인: `journalctl -u teamprime -f`
2. 포트 확인: `netstat -tlnp | grep 8001`
3. 방화벽 확인: `ufw status`

### 데이터베이스 연결 오류
1. MySQL 서비스 상태: `systemctl status mysql`
2. 데이터베이스 존재 확인
3. 사용자 권한 확인

### SSL 인증서 문제
```bash
# 인증서 갱신
certbot renew --nginx
```