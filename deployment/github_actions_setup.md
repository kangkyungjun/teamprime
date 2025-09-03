# 🚀 GitHub Actions 자동 배포 설정

SSH 직접 접속이 불안정한 상황에서 GitHub Actions을 통한 자동 배포를 설정할 수 있습니다.

## 현재 상황
- SSH 포트 22가 간헐적으로 열려있음 (connection established 확인)
- 인증 문제로 직접 접속 불가
- 웹서비스 포트들(80, 443)은 여전히 닫혀있음

## GitHub Actions 설정 방법

### 1. GitHub Repository Settings에서 Secrets 추가

다음 정보를 GitHub Repository → Settings → Secrets and variables → Actions에 추가:

```
CAFE24_HOST: 172.233.87.201
CAFE24_USER: (Cafe24에서 제공한 SSH 사용자명)
CAFE24_PASSWORD: (Cafe24에서 설정한 SSH 비밀번호)
MYSQL_USERNAME: (Cafe24 MySQL 사용자명)
MYSQL_PASSWORD: nF2VRsxEldWBsdsvYvJaMQ==
JWT_SECRET_KEY: B5kyV+90hUJE4iq3Nby7WfLpuPtktEej/mq4kKiS0GE=
```

### 2. 배포 트리거

GitHub Actions은 다음과 같이 트리거됩니다:

#### 자동 배포 (Push시)
```bash
# 코드를 수정하고 푸시하면 자동으로 배포
git add .
git commit -m "Update application"
git push origin master
```

#### 수동 배포
1. GitHub Repository 페이지 접속
2. Actions 탭 클릭
3. "Deploy to Cafe24" 워크플로우 선택
4. "Run workflow" 버튼 클릭

### 3. 배포 과정 모니터링

GitHub Actions에서 실시간으로 배포 과정을 확인할 수 있습니다:

1. **Setup Phase**: Python 환경 설정
2. **Build Phase**: 의존성 설치 및 패키징
3. **Upload Phase**: 서버로 파일 업로드 (SCP)
4. **Deploy Phase**: 서버에서 배포 실행
5. **Service Start**: Teamprime 서비스 시작
6. **Health Check**: 서비스 정상 작동 확인

## 배포 성공 조건

GitHub Actions 배포가 성공하려면:

✅ **SSH 접속 가능**: 포트 22 열려있음 (현재 간헐적으로 가능)  
✅ **사용자 인증**: SSH 사용자명/비밀번호 설정 필요  
⏳ **방화벽 설정**: 포트 8001 오픈 필요 (앱 실행용)  
⏳ **MySQL 설정**: 데이터베이스 생성 및 사용자 권한 설정  

## 현재 진행 상황

1. ✅ **GitHub Actions 워크플로우 생성 완료** (.github/workflows/deploy.yml)
2. ✅ **배포 스크립트 준비 완료** (deployment/manual_deploy.sh)
3. ✅ **환경 설정 파일 준비 완료** (.env.cafe24)
4. ✅ **보안 자격증명 생성 완료** (JWT 키, MySQL 패스워드)

## 필요한 Cafe24 설정

### SSH 사용자 생성
```
1. Cafe24 콘솔 → SSH 관리
2. 새 SSH 사용자 생성
3. 사용자명과 비밀번호 기록
4. GitHub Secrets에 추가
```

### MySQL 설정
```
1. Cafe24 콘솔 → 데이터베이스 관리
2. teamprime_trading 데이터베이스 생성
3. 사용자명/비밀번호 확인
4. 외부 접속 허용 (필요시)
```

### 포트 8001 오픈
```
1. Cafe24 콘솔 → 보안 설정
2. 방화벽 관리
3. 포트 8001 추가 (Teamprime 앱용)
4. 포트 80, 443도 확인
```

## 배포 후 확인

배포 완료 후 다음을 확인:

```bash
# 서비스 상태 (GitHub Actions 로그에서 확인)
ps aux | grep python3
netstat -tlnp | grep 8001

# 웹사이트 접속
http://teamprime.co.kr:8001  # 직접 접속
http://teamprime.co.kr       # Nginx 프록시 (설정시)
```

## 트러블슈팅

### GitHub Actions 배포 실패시

**SSH 연결 실패**
```
- Cafe24에서 SSH 사용자 계정 확인
- 비밀번호가 올바른지 확인
- GitHub Secrets 설정 재확인
```

**파일 업로드 실패**
```
- 서버 디스크 공간 확인
- 권한 설정 확인
- 대상 디렉토리 존재 여부 확인
```

**서비스 시작 실패**
```
- Python 버전 확인 (3.9+ 필요)
- MySQL 연결 확인
- 포트 8001 사용 가능 여부 확인
```

---

## 즉시 실행 가능한 대안

서버 직접 접속이 어려운 현 상황에서는 **GitHub Actions 자동 배포**가 가장 현실적인 해결책입니다.

### 다음 단계:
1. Cafe24 콘솔에서 SSH 사용자 생성
2. GitHub Secrets에 접속 정보 추가  
3. GitHub Actions로 배포 실행
4. 성공시 teamprime.co.kr에서 서비스 확인