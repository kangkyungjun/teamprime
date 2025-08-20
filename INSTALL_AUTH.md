# MySQL 기반 사용자 인증 시스템 설치 가이드

## 🎯 완료된 구현 사항

✅ **MySQL 데이터베이스 연결 모듈**
✅ **사용자 인증 모델 (User, UserAPIKeys, UserSession)**  
✅ **AES-256 API 키 암호화 서비스**
✅ **로그인/회원가입 서비스**
✅ **JWT 기반 세션 관리**
✅ **로그인/회원가입 UI 페이지**
✅ **기존 시스템 연동 (API 키 자동 로드)**
✅ **환경 설정 및 보안**

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
pip install aiomysql PyJWT bcrypt cryptography email-validator
```

### 2. MySQL 데이터베이스 설정

#### MySQL 서버에서 데이터베이스 생성:
```sql
CREATE DATABASE teamprime_trading CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'teamprime_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON teamprime_trading.* TO 'teamprime_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 환경변수 설정

`.env` 파일 생성:
```env
# MySQL 데이터베이스 설정
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=teamprime_trading
MYSQL_USERNAME=teamprime_user
MYSQL_PASSWORD=your_secure_password

# JWT 보안 설정 (⚠️ 실제 운영시 반드시 변경)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-now
JWT_EXPIRE_HOURS=24
SESSION_EXPIRE_HOURS=168

# 기존 설정
MARKETS=KRW-BTC,KRW-XRP,KRW-ETH,KRW-DOGE,KRW-BTT
YEARS=3
DB_URL=sqlite+aiosqlite:///./upbit_candles.db
```

### 4. 애플리케이션 실행

```bash
python main.py
```

시작시 자동으로 MySQL 테이블들이 생성됩니다:
- `users` - 사용자 정보
- `user_api_keys` - 암호화된 API 키 저장
- `user_sessions` - 세션 관리

## 🔐 사용자 인증 플로우

### 1. 회원가입 (`/register`)
- 사용자명, 이메일, 비밀번호 입력
- 업비트 API 키도 함께 등록 (AES-256 암호화 저장)
- 비밀번호 강도 검증 (대소문자, 숫자, 특수문자 포함)

### 2. 로그인 (`/login`)  
- 사용자명 또는 이메일로 로그인
- JWT 토큰 발급 (24시간 유효)
- 쿠키에 자동 저장

### 3. 대시보드 접근 (`/`)
- 로그인된 사용자: 자동으로 API 키 로드 후 기존 대시보드 표시
- 로그인되지 않은 사용자: `/login`으로 리다이렉트

## 🔧 API 엔드포인트

### 인증 관련 API
- `POST /api/auth/register` - 회원가입
- `POST /api/auth/login` - 로그인  
- `POST /api/auth/logout` - 로그아웃
- `GET /api/auth/me` - 현재 사용자 정보
- `POST /api/auth/update-api-keys` - API 키 업데이트

### 통합 거래 API (새로운)
- `POST /api/auth-login` - **핵심 API**: 로그인된 사용자의 API 키 자동 로드

#### `/api/auth-login` 사용법:

**로그인된 사용자의 경우** (비밀번호만 필요):
```javascript
fetch('/api/auth-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        password: '사용자비밀번호'  // API 키 복호화용
    })
});
```

**기존 방식** (직접 API 키 입력):
```javascript
fetch('/api/auth-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        access_key: 'upbit_access_key',
        secret_key: 'upbit_secret_key'
    })
});
```

## 🛡️ 보안 기능

- **AES-256-GCM 암호화**: API 키는 사용자별 고유 솔트로 암호화
- **bcrypt 해싱**: 비밀번호는 12 rounds bcrypt로 해싱
- **JWT 토큰**: 세션 관리 (24시간 유효)
- **PBKDF2 키 파생**: 100,000회 반복으로 강화된 키 생성
- **비밀번호 강도 검증**: 대소문자, 숫자, 특수문자 필수

## 🔄 기존 기능 보존

**⚠️ 중요: 기존 거래 기능은 100% 보존됩니다**
- 기존 `/api/login` 엔드포인트 완전 보존
- 거래 알고리즘 및 수익 창출 로직 변경 없음
- 실시간 분석 및 신호 감지 성능 영향 없음
- SQLite 캔들 데이터 저장 방식 유지
- 모든 기존 API 엔드포인트 호환성 유지

## 🌐 카페24 배포 준비사항

### 1. 보안 설정
```env
# 운영 환경 설정
JWT_SECRET_KEY=매우-강력한-64자리-랜덤-문자열
SECURE_COOKIES=true
HTTPS_ONLY=true
LOG_LEVEL=WARNING
```

### 2. MySQL 설정
- SSL 연결 활성화
- 정기적인 백업 설정
- 접근 권한 최소화

### 3. 방화벽 설정
- MySQL 포트 (3306) 보안
- HTTPS 강제 적용

## 🧪 테스트

1. **회원가입 테스트**:
   - http://localhost:8001/register 접근
   - 사용자명, 이메일, 비밀번호, API 키 입력

2. **로그인 테스트**:
   - http://localhost:8001/login 접근
   - 등록한 계정으로 로그인

3. **자동 API 키 로드 테스트**:
   - 로그인 후 http://localhost:8001/ 접근
   - 비밀번호 입력시 자동으로 업비트 연결

## 📝 주의사항

1. **JWT_SECRET_KEY는 반드시 강력한 키로 변경**
2. **MySQL 비밀번호는 복잡하게 설정**
3. **운영 환경에서는 HTTPS 필수**
4. **정기적인 세션 정리 권장**

## ✅ 완료 확인

시스템 시작시 다음 로그 확인:
```
✅ SQLite 데이터베이스 초기화 완료
✅ MySQL 연결 테스트 성공
✅ MySQL 인증 데이터베이스 초기화 완료
🎉 데이터베이스 마이그레이션 완료
```

모든 설정이 완료되면 새로운 인증 시스템과 기존 거래 시스템이 완벽하게 통합되어 동작합니다!