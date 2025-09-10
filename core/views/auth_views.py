"""
인증 관련 뷰 라우터
- 로그인 페이지
- 회원가입 페이지
- 로그아웃 처리
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)
auth_views_router = APIRouter()

# 이 파일은 인증 관련 뷰만 포함하며, 
# 실제 로그인/회원가입 로직은 core.api.auth에서 처리됩니다.
# 추후 확장 시 이곳에 인증 관련 HTML 페이지들을 추가할 수 있습니다.