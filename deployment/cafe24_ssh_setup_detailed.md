# 🔐 Cafe24 SSH 사용자 설정 상세 가이드

## SSH 사용자 설정이란?

**SSH 사용자**는 서버에 원격 접속할 수 있는 계정입니다. 현재 teamprime.co.kr 서버는 SSH 포트는 열려있지만, 접속할 수 있는 사용자 계정이 설정되어 있지 않은 상태입니다.

## 현재 상황 분석

### 연결 테스트 결과
```bash
# SSH 포트 상태
ssh -v root@teamprime.co.kr
# 결과: "Connection established" - 포트는 열려있음
# 하지만: "Permission denied (publickey,password)" - 인증 실패

# 시도한 사용자명들
root@teamprime.co.kr ❌
teamprime@teamprime.co.kr ❌  
ubuntu@teamprime.co.kr ❌
admin@teamprime.co.kr ❌
```

**결론**: 서버에 SSH 접속이 가능한 사용자 계정이 없음

## Cafe24 호스팅에서 SSH 사용자 생성 방법

### 방법 1: Cafe24 웹 콘솔 (권장)

#### 1단계: Cafe24 호스팅 콘솔 접속
```
1. https://hosting.cafe24.com 접속
2. 계정으로 로그인
3. "내 서비스 관리" 클릭
4. "호스팅 관리" 선택
5. teamprime.co.kr 도메인 클릭
```

#### 2단계: SSH 설정 메뉴 찾기
Cafe24 콘솔에서 다음 메뉴들을 찾아보세요:

```
가능한 메뉴 이름들:
- "SSH 관리" 또는 "SSH 설정"
- "터미널 액세스" 또는 "원격 접속"
- "서버 관리" → "SSH 계정"
- "보안 설정" → "SSH 액세스"
- "고급 설정" → "SSH/SFTP"
```

#### 3단계: SSH 사용자 생성
일반적인 설정 과정:

```
1. "SSH 사용자 추가" 또는 "새 SSH 계정" 버튼 클릭
2. 사용자명 입력 (예: teamprime, admin, 또는 본인 이름)
3. 비밀번호 설정 (강력한 비밀번호 권장)
4. 권한 설정 (관리자 권한 또는 일반 사용자)
5. 홈 디렉토리 설정 (기본값 사용 권장)
6. "생성" 또는 "저장" 버튼 클릭
```

### 방법 2: Cafe24 고객센터 문의

SSH 설정 메뉴를 찾을 수 없는 경우:

```
📞 Cafe24 고객센터: 1588-3284
📧 온라인 상담: Cafe24 웹사이트 → 고객지원 → 1:1 문의

요청 내용:
"teamprime.co.kr 도메인에 SSH 접속용 사용자 계정을 생성해 주세요.
사용자명: teamprime
용도: Python 웹 애플리케이션 배포"
```

## SSH 사용자 생성 후 확인 방법

### 로컬에서 SSH 연결 테스트
```bash
# 생성한 사용자명으로 접속 시도
ssh 사용자명@teamprime.co.kr

# 예시
ssh teamprime@teamprime.co.kr
# 비밀번호 입력 프롬프트가 나와야 성공

# 또는 IP로 직접 접속
ssh teamprime@172.233.87.201
```

### 성공적인 SSH 연결의 모습
```bash
$ ssh teamprime@teamprime.co.kr
Password: [비밀번호 입력]
Welcome to Ubuntu 20.04.x LTS (GNU/Linux)
...
teamprime@server:~$ whoami
teamprime
teamprime@server:~$ pwd
/home/teamprime
```

## SSH 사용자 정보 GitHub Secrets에 추가

### GitHub Repository 설정
```
1. https://github.com/kangkyungjun/teamprime 접속
2. Settings 탭 클릭
3. 좌측 메뉴에서 "Secrets and variables" → "Actions" 클릭
4. "New repository secret" 버튼 클릭
```

### 추가해야 할 Secrets
```
Name: CAFE24_HOST
Value: 172.233.87.201

Name: CAFE24_USER  
Value: [생성한 SSH 사용자명] (예: teamprime)

Name: CAFE24_PASSWORD
Value: [설정한 SSH 비밀번호]

Name: MYSQL_USERNAME
Value: [Cafe24 MySQL 사용자명]

Name: MYSQL_PASSWORD  
Value: nF2VRsxEldWBsdsvYvJaMQ==

Name: JWT_SECRET_KEY
Value: B5kyV+90hUJE4iq3Nby7WfLpuPtktEej/mq4kKiS0GE=
```

## SSH 키 기반 인증 설정 (선택사항, 더 안전함)

### 1. SSH 공개키를 서버에 등록
```bash
# 로컬에서 생성한 공개키 내용 확인
cat teamprime_deploy_key.pub
```

### 2. Cafe24에서 공개키 등록
```
일부 호스팅 서비스에서는 SSH 키 등록 기능 제공:
1. SSH 설정 메뉴에서 "공개키 등록" 또는 "SSH Keys" 메뉴 찾기
2. teamprime_deploy_key.pub 파일 내용 복사해서 붙여넣기
3. 키 이름 설정 (예: teamprime-deploy-key)
4. 저장
```

### 3. SSH 키로 연결 테스트
```bash
# 개인키로 연결 시도
ssh -i teamprime_deploy_key teamprime@teamprime.co.kr
# 비밀번호 없이 바로 접속되면 성공
```

## 일반적인 Cafe24 SSH 계정 유형

### 1. 관리자 계정
```
특징:
- sudo 권한 있음
- 모든 디렉토리 접근 가능
- 시스템 설정 변경 가능

사용 예:
sudo apt install python3
sudo systemctl restart nginx
```

### 2. 일반 사용자 계정  
```
특징:
- 홈 디렉토리만 접근 가능
- 시스템 설정 변경 불가
- 웹 애플리케이션 배포에 충분

사용 예:
cd /home/teamprime
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## SSH 접속 후 배포 진행

SSH 사용자 생성이 완료되면:

### 1. 직접 SSH로 배포
```bash
# SSH 접속
ssh teamprime@teamprime.co.kr

# 배포 스크립트 다운로드 및 실행
curl -o manual_deploy.sh https://raw.githubusercontent.com/kangkyungjun/teamprime/master/deployment/manual_deploy.sh
chmod +x manual_deploy.sh
./manual_deploy.sh teamprime.co.kr
```

### 2. GitHub Actions 자동 배포
```
1. GitHub Secrets에 SSH 정보 추가 (위에서 설명한 대로)
2. GitHub → Actions → "Deploy to Cafe24" 워크플로우
3. "Run workflow" 버튼 클릭
4. 배포 진행 상황을 실시간으로 모니터링
```

## 트러블슈팅

### SSH 접속 시 일반적인 오류들

#### "Connection refused"
```bash
원인: SSH 서비스가 꺼져있음
해결: Cafe24 콘솔에서 SSH 서비스 활성화
```

#### "Permission denied (publickey)"  
```bash
원인: 공개키 인증만 허용하는데 키가 등록되지 않음
해결: 비밀번호 인증 활성화 또는 공개키 등록
```

#### "Permission denied (password)"
```bash
원인: 비밀번호가 틀리거나 사용자가 존재하지 않음  
해결: 사용자명과 비밀번호 재확인
```

#### "Host key verification failed"
```bash
원인: 서버의 SSH 키가 변경됨
해결: ssh-keygen -R teamprime.co.kr
```

### Cafe24 특화 문제들

#### SSH 메뉴가 보이지 않는 경우
```
가능한 원인:
1. 호스팅 플랜에서 SSH 지원하지 않음
2. 메뉴 이름이 다름 ("터미널", "콘솔", "셸" 등)
3. 별도 신청이 필요한 옵션 서비스

해결책:
- 호스팅 플랜 확인
- 고객센터 문의 (1588-3284)
```

#### FTP만 지원하는 경우
```
일부 저가형 호스팅은 SSH 미지원
대안:
1. FTP로 파일 업로드 후 웹 콘솔에서 실행
2. Cafe24 웹 파일관리자 사용
3. 상위 플랜으로 업그레이드
```

## 보안 권장사항

### SSH 비밀번호
```
✅ 권장: 대문자+소문자+숫자+특수문자, 12자 이상
❌ 피할것: admin, 123456, password, teamprime
```

### SSH 키 관리
```
✅ 개인키 파일 권한: chmod 600 teamprime_deploy_key
✅ 개인키는 절대 공유하지 않음
✅ 공개키만 서버에 등록
```

### 추가 보안 설정
```bash
# SSH 설정에서 가능한 경우
- 비밀번호 인증 비활성화 (키 인증만 사용)
- Root 로그인 금지
- SSH 포트 변경 (22 → 다른 포트)
- 실패 횟수 제한
```

---

## 요약 체크리스트

SSH 사용자 설정을 위한 단계별 체크리스트:

- [ ] 1. Cafe24 콘솔 접속 (https://hosting.cafe24.com)
- [ ] 2. SSH 관리 메뉴 찾기 
- [ ] 3. 새 SSH 사용자 생성 (사용자명: teamprime 권장)
- [ ] 4. 강력한 비밀번호 설정
- [ ] 5. 사용자 생성 완료 확인
- [ ] 6. 로컬에서 SSH 연결 테스트
- [ ] 7. GitHub Secrets에 접속 정보 추가
- [ ] 8. GitHub Actions 배포 실행 또는 수동 배포 진행

**SSH 사용자 설정만 완료되면, 준비된 모든 배포 스크립트들이 자동으로 작동합니다!**