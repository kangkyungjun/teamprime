#!/bin/bash
# =============================================================================
# 🛡️ TEAMPRIME 안전 Git Push 스크립트
# =============================================================================
# 대용량 파일을 확인하고 안전하게 Git에 푸시하는 스크립트입니다.
# 사용법: ./git-safe-push.sh [커밋 메시지] [브랜치]

set -e

# 색상 정의
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 기본값 설정
BRANCH=${2:-"master"}
COMMIT_MESSAGE=${1:-""}
MAX_SIZE=104857600  # 100MB in bytes

# 헤더 출력
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${PURPLE}🚀 TEAMPRIME 안전 Git Push 시스템${NC}"
echo -e "${PURPLE}=================================================================${NC}"
echo ""

# 커밋 메시지 확인
if [ -z "$COMMIT_MESSAGE" ]; then
    echo -e "${YELLOW}💬 커밋 메시지를 입력하세요:${NC}"
    read -r COMMIT_MESSAGE
    
    if [ -z "$COMMIT_MESSAGE" ]; then
        echo -e "${RED}❌ 커밋 메시지가 필요합니다.${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}📝 커밋 메시지: ${COMMIT_MESSAGE}${NC}"
echo -e "${BLUE}🌳 대상 브랜치: ${BRANCH}${NC}"
echo ""

# 1단계: Git 상태 확인
echo -e "${BLUE}🔍 1단계: Git 상태 확인${NC}"
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Git 저장소가 아닙니다.${NC}"
    exit 1
fi

# 변경사항 확인
git_status=$(git status --porcelain)
if [ -z "$git_status" ]; then
    echo -e "${YELLOW}⚠️  변경사항이 없습니다.${NC}"
    echo -e "${YELLOW}💡 빈 커밋을 생성하시겠습니까? [y/N]:${NC}"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}📦 빈 커밋 생성 중...${NC}"
        git commit --allow-empty -m "$COMMIT_MESSAGE

🚀 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
        echo -e "${GREEN}✅ 빈 커밋이 생성되었습니다.${NC}"
    else
        echo -e "${YELLOW}📤 푸시만 실행합니다.${NC}"
        git push origin "$BRANCH"
        echo -e "${GREEN}🎉 푸시 완료!${NC}"
        exit 0
    fi
fi

# 2단계: 대용량 파일 검사
echo -e "${BLUE}🔍 2단계: 대용량 파일 검사${NC}"

# 모든 파일 크기 확인
large_files=()
total_size=0
file_count=0

# 추적된 파일들 검사
while IFS= read -r file; do
    if [ -f "$file" ]; then
        file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        total_size=$((total_size + file_size))
        file_count=$((file_count + 1))
        
        if [ "$file_size" -gt "$MAX_SIZE" ]; then
            large_files+=("$file:$file_size")
        fi
        
        # 진행상황 표시
        if [ $((file_count % 50)) -eq 0 ]; then
            echo -e "${BLUE}   📊 ${file_count}개 파일 검사 중...${NC}"
        fi
    fi
done < <(git ls-files)

total_size_mb=$((total_size / 1024 / 1024))
echo -e "${GREEN}✅ 검사 완료: ${file_count}개 파일 (총 ${total_size_mb}MB)${NC}"

# 대용량 파일 발견 시 경고
if [ ${#large_files[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}⚠️  대용량 파일 발견!${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    for item in "${large_files[@]}"; do
        file="${item%:*}"
        size="${item#*:}"
        size_mb=$((size / 1024 / 1024))
        echo -e "${RED}📁 ${file} - ${size_mb}MB${NC}"
    done
    
    echo ""
    echo -e "${YELLOW}🔧 이 파일들은 GitHub 100MB 제한을 초과합니다.${NC}"
    echo -e "${YELLOW}💡 계속 진행하려면 다음 중 하나를 선택하세요:${NC}"
    echo ""
    echo -e "${BLUE}1. [i] .gitignore에 추가하고 계속${NC}"
    echo -e "${BLUE}2. [r] 저장소에서 제거하고 계속${NC}"
    echo -e "${BLUE}3. [a] 무시하고 강제 푸시 (위험!)${NC}"
    echo -e "${BLUE}4. [q] 취소${NC}"
    echo ""
    read -r choice
    
    case $choice in
        [Ii])
            echo -e "${BLUE}📝 .gitignore에 파일 추가 중...${NC}"
            for item in "${large_files[@]}"; do
                file="${item%:*}"
                echo "# Large file auto-added by git-safe-push.sh" >> .gitignore
                echo "$file" >> .gitignore
                git rm --cached "$file" 2>/dev/null || true
            done
            echo -e "${GREEN}✅ 대용량 파일들이 .gitignore에 추가되었습니다.${NC}"
            ;;
        [Rr])
            echo -e "${BLUE}🗑️  저장소에서 파일 제거 중...${NC}"
            for item in "${large_files[@]}"; do
                file="${item%:*}"
                git rm --cached "$file"
            done
            echo -e "${GREEN}✅ 대용량 파일들이 저장소에서 제거되었습니다.${NC}"
            ;;
        [Aa])
            echo -e "${YELLOW}⚠️  강제 푸시를 선택했습니다. 실패할 수 있습니다.${NC}"
            ;;
        *)
            echo -e "${RED}❌ 작업이 취소되었습니다.${NC}"
            exit 1
            ;;
    esac
fi

# 3단계: 파일 추가 및 커밋
echo ""
echo -e "${BLUE}🔍 3단계: 파일 추가 및 커밋${NC}"

# 변경사항 스테이징
git add .

# Pre-commit 훅이 있는지 확인
if [ -f ".git/hooks/pre-commit" ]; then
    echo -e "${BLUE}🔍 Pre-commit 훅 실행 중...${NC}"
fi

# 커밋 실행
echo -e "${BLUE}📦 커밋 생성 중...${NC}"
git commit -m "$COMMIT_MESSAGE

🚀 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>" || {
    echo -e "${YELLOW}⚠️  새로운 변경사항이 없어 커밋을 건너뜁니다.${NC}"
}

# 4단계: 푸시 전 최종 확인
echo ""
echo -e "${BLUE}🔍 4단계: 푸시 전 최종 확인${NC}"

# 리모트 상태 확인
if ! git remote get-url origin > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  원격 저장소가 설정되어 있지 않습니다.${NC}"
    echo -e "${YELLOW}💡 푸시를 건너뜁니다.${NC}"
    echo -e "${GREEN}✅ 로컬 커밋이 완료되었습니다.${NC}"
    exit 0
fi

# 푸시할 커밋 수 확인
commits_ahead=$(git rev-list --count origin/"$BRANCH"..HEAD 2>/dev/null || echo "0")
echo -e "${BLUE}📊 푸시할 커밋 수: ${commits_ahead}개${NC}"

if [ "$commits_ahead" -eq 0 ]; then
    echo -e "${GREEN}✅ 모든 변경사항이 이미 원격에 반영되어 있습니다.${NC}"
    exit 0
fi

# 최종 확인
echo ""
echo -e "${YELLOW}🚀 ${BRANCH} 브랜치에 ${commits_ahead}개 커밋을 푸시하시겠습니까? [Y/n]:${NC}"
read -r confirm

if [[ ! "$confirm" =~ ^[Nn]$ ]]; then
    echo -e "${BLUE}📤 푸시 실행 중...${NC}"
    
    # 푸시 시도 (실패 시 강제 푸시 옵션 제공)
    if ! git push origin "$BRANCH"; then
        echo ""
        echo -e "${RED}❌ 푸시가 실패했습니다.${NC}"
        echo -e "${YELLOW}💡 강제 푸시를 시도하시겠습니까? (주의: 히스토리가 덮어써집니다) [y/N]:${NC}"
        read -r force_confirm
        
        if [[ "$force_confirm" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}⚠️  강제 푸시 실행 중...${NC}"
            git push --force origin "$BRANCH"
        else
            echo -e "${RED}❌ 푸시가 취소되었습니다.${NC}"
            exit 1
        fi
    fi
    
    echo ""
    echo -e "${GREEN}🎉 성공적으로 푸시되었습니다!${NC}"
    
    # GitHub URL 표시 (가능한 경우)
    remote_url=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ "$remote_url" =~ github\.com ]]; then
        github_url=${remote_url%.git}
        github_url=${github_url#git@github.com:}
        github_url=${github_url#https://github.com/}
        echo -e "${BLUE}🌐 GitHub: https://github.com/${github_url}${NC}"
    fi
    
else
    echo -e "${YELLOW}📤 푸시가 취소되었습니다.${NC}"
    echo -e "${GREEN}✅ 로컬 커밋은 완료되었습니다.${NC}"
fi

echo ""
echo -e "${PURPLE}=================================================================${NC}"
echo -e "${PURPLE}✅ TEAMPRIME 안전 Git Push 완료${NC}"
echo -e "${PURPLE}=================================================================${NC}"