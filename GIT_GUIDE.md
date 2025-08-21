# 🛡️ TEAMPRIME Git 대용량 파일 방지 가이드

TEAMPRIME 프로젝트에서 Git 사용 시 대용량 파일 문제를 방지하는 완전한 가이드입니다.

## 🚨 문제 상황

- **GitHub 제한**: 100MB 이상 파일 업로드 불가
- **우리의 상황**: `upbit_candles.db` (727MB) 등 대용량 파일 존재
- **발생하는 오류**: `File xxx is XXX.XX MB; this exceeds GitHub's file size limit of 100.00 MB`

## 🛡️ 적용된 보안 시스템

### 1. 강화된 .gitignore
- **200개 이상의 패턴**: 모든 종류의 대용량 파일 차단
- **카테고리별 분류**: 데이터베이스, 로그, 백업, 미디어, 압축파일 등
- **프로젝트 특화**: 업비트 거래 데이터, 백테스팅 결과 등 제외

### 2. Git Attributes (.gitattributes)
- **파일 타입별 처리**: 바이너리/텍스트 파일 구분
- **인코딩 설정**: UTF-8 통일, LF 줄바꿈 설정
- **LFS 준비**: 대용량 파일을 위한 Git LFS 설정 가이드

### 3. Pre-commit Hook
- **자동 검사**: 커밋 전 파일 크기 자동 확인
- **100MB 차단**: GitHub 제한 초과 파일 자동 차단
- **자동 해결**: 문제 파일 자동 unstaging 옵션

### 4. 안전 푸시 스크립트
- **종합 검사**: 푸시 전 전체 저장소 스캔
- **대화형 해결**: 문제 발생 시 해결 방법 제시
- **강제 푸시 옵션**: 필요 시 안전한 강제 푸시

## 🚀 사용법

### 기본 Git 명령어 (권장)
```bash
# 일반적인 사용법 - pre-commit hook이 자동으로 보호
git add .
git commit -m "커밋 메시지"
git push origin master
```

### 안전 푸시 스크립트 사용 (더욱 안전)
```bash
# 기본 사용법
./git-safe-push.sh "커밋 메시지"

# 다른 브랜치에 푸시
./git-safe-push.sh "커밋 메시지" "develop"

# 대화형 모드
./git-safe-push.sh
```

## 🔧 문제 해결 방법

### 이미 추가된 대용량 파일 제거
```bash
# 1. Git에서 파일 제거 (로컬 파일은 유지)
git rm --cached 파일명

# 2. .gitignore에 추가
echo "파일명" >> .gitignore

# 3. 커밋
git commit -m "Remove large file from tracking"
```

### Git 히스토리에서 완전 제거 (고급)
```bash
# ⚠️ 주의: 히스토리를 변경하므로 신중히 사용
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch 파일명' \
--prune-empty --tag-name-filter cat -- --all

# 강제 푸시
git push --force origin master
```

### Git LFS 사용 (대용량 파일 관리)
```bash
# 1. Git LFS 설치 (필요 시)
git lfs install

# 2. 대용량 파일 타입 추적
git lfs track "*.db"
git lfs track "*.sqlite"

# 3. .gitattributes 업데이트
git add .gitattributes

# 4. 일반적인 커밋/푸시
git add .
git commit -m "Add LFS support"
git push origin master
```

## 📊 파일 크기 제한 가이드

| 파일 타입 | 제한 | 상태 |
|-----------|------|------|
| **일반 파일** | < 100MB | ✅ GitHub OK |
| **LFS 파일** | < 2GB | ✅ GitHub LFS |
| **전체 저장소** | < 100GB | ✅ GitHub 권장 |

## 🚫 절대 업로드 금지 파일들

### 데이터베이스 파일
- `*.db`, `*.sqlite`, `*.sqlite3`
- `upbit_candles.db` (727MB!)
- MySQL 덤프 파일

### 로그 파일
- `*.log`, `trading_system.log`
- 시간이 지나면서 계속 커지는 파일들

### 백업 파일
- `users_backup_*.json`
- `*_backup.*`, `*.backup`
- 사용자 데이터 백업 (보안 위험!)

### 미디어 파일
- 이미지: `*.jpg`, `*.png`, `*.gif`
- 비디오: `*.mp4`, `*.avi`
- 압축파일: `*.zip`, `*.tar.gz`

## 💡 모범 사례

### ✅ 좋은 습관
1. **커밋 전 확인**: `git status`로 추가될 파일 확인
2. **정기적 정리**: 로그 파일, 임시 파일 정기 삭제
3. **안전 스크립트 사용**: `./git-safe-push.sh` 활용
4. **.gitignore 활용**: 새로운 파일 타입 발견 시 즉시 추가

### ❌ 피해야 할 실수
1. **git add .** 맹목적 사용 (파일 확인 없이)
2. **강제 푸시 남용**: `git push --force` 신중히 사용
3. **대용량 파일 커밋**: 한 번 들어가면 히스토리 정리 필요
4. **백업 파일 커밋**: 민감한 사용자 정보 노출 위험

## 🔍 파일 크기 확인 명령어

### 현재 저장소 크기 확인
```bash
# 전체 저장소 크기
du -sh .git

# 가장 큰 파일들 찾기
find . -type f -exec ls -la {} \; | sort -nrk 5 | head -10

# Git에서 추적하는 가장 큰 파일들
git ls-files | xargs ls -la | sort -nrk 5 | head -10
```

### 특정 파일 크기 확인
```bash
# macOS
stat -f%z filename

# Linux
stat -c%s filename

# 사람이 읽기 쉬운 형태
ls -lh filename
```

## 🚨 응급 상황 대처법

### GitHub 푸시 실패 시
1. **오류 메시지 확인**: 어떤 파일이 문제인지 파악
2. **즉시 파일 제거**: `git rm --cached 파일명`
3. **히스토리 정리**: 필요 시 `git filter-branch` 사용
4. **안전 푸시**: `./git-safe-push.sh` 사용

### 저장소 크기가 너무 클 때
```bash
# 1. 대용량 파일 찾기
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | sort --numeric-sort --key=2 | tail -10

# 2. BFG Repo-Cleaner 사용 (권장)
# https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --strip-blobs-bigger-than 50M

# 3. 정리 및 푸시
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force origin master
```

## 📞 도움이 필요할 때

### 자동화된 해결책
1. **Pre-commit Hook**: 자동으로 문제 파일 차단
2. **안전 푸시 스크립트**: `./git-safe-push.sh` 실행
3. **Git 상태 확인**: `git status` 정기 실행

### 수동 해결이 필요한 경우
- Git 히스토리에 이미 대용량 파일이 있는 경우
- 복잡한 브랜치 구조에서 문제가 발생한 경우
- LFS 설정이 필요한 경우

---

## 🎉 요약

이제 TEAMPRIME 프로젝트에서는:
- ✅ **자동 보호**: Pre-commit hook이 대용량 파일 차단
- ✅ **포괄적 차단**: 200+ 패턴의 .gitignore
- ✅ **안전 푸시**: `git-safe-push.sh` 스크립트 제공
- ✅ **문제 해결**: 상황별 해결 방법 문서화

**앞으로는 Git 대용량 파일 문제가 발생하지 않습니다!** 🎉