"""
사용자별 세션 상태 관리자
다중 사용자 동시 사용을 위한 세션 격리 시스템
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime
from ..models.trading import TradingState
from ..services.trading_engine import MultiCoinTradingEngine

logger = logging.getLogger(__name__)

class UserSession:
    """개별 사용자 세션 데이터"""
    
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        
        # API 키 정보 (메모리만, DB 저장 안함)
        self.access_key: str = ""
        self.secret_key: str = ""
        
        # 업비트 클라이언트
        self.upbit_client = None
        
        # 로그인 상태
        self.login_status = {
            "logged_in": False,
            "account_info": None,
            "login_time": None
        }
        
        # 거래 상태 (사용자별 독립적인 인스턴스)
        self.trading_state = TradingState()
        
        # 거래 엔진 (사용자별 독립적인 인스턴스) - 세션 참조 전달
        self.trading_engine = MultiCoinTradingEngine(user_session=self)
        
        # 세션 생성 시간
        self.created_at = datetime.now()
        self.last_access = datetime.now()
        
        logger.info(f"✅ 사용자 세션 생성: {username} (ID: {user_id})")
    
    def update_api_keys(self, access_key: str, secret_key: str):
        """API 키 업데이트"""
        self.access_key = access_key
        self.secret_key = secret_key
        self.last_access = datetime.now()
        logger.info(f"🔑 API 키 업데이트: {self.username}")
    
    def set_upbit_client(self, client):
        """업비트 클라이언트 설정"""
        self.upbit_client = client
        self.last_access = datetime.now()
        logger.info(f"🔗 업비트 클라이언트 설정: {self.username}")
    
    def update_login_status(self, logged_in: bool, account_info=None):
        """로그인 상태 업데이트"""
        self.login_status["logged_in"] = logged_in
        self.login_status["account_info"] = account_info
        self.login_status["login_time"] = datetime.now().isoformat() if logged_in else None
        self.last_access = datetime.now()
        logger.info(f"🔐 로그인 상태 업데이트: {self.username} -> {logged_in}")
    
    def cleanup(self):
        """세션 정리 - 동기 버전 (즉시 정리)"""
        logger.info(f"🧹 사용자 세션 정리 시작: {self.username}")
        
        # 거래 엔진 상태 기록 및 강제 정리
        if hasattr(self.trading_engine, 'is_running') and self.trading_engine.is_running:
            logger.warning(f"⚠️ {self.username}의 거래 엔진이 실행 중 - 강제 중지")
            # 강제로 running 상태를 False로 설정하여 추가 작업 방지
            self.trading_engine.is_running = False
            
            # 활성 작업들 취소 플래그 설정 (async task는 다음 주기에서 자동 종료됨)
            if hasattr(self.trading_engine, 'signal_task') and self.trading_engine.signal_task:
                self.trading_engine.signal_task = None
            if hasattr(self.trading_engine, 'monitoring_task') and self.trading_engine.monitoring_task:
                self.trading_engine.monitoring_task = None
        
        # 메모리 정리
        self.access_key = ""
        self.secret_key = ""
        self.upbit_client = None
        self.login_status = {"logged_in": False, "account_info": None, "login_time": None}
        
        logger.info(f"✅ 사용자 세션 정리 완료: {self.username}")
    
    async def async_cleanup(self):
        """세션 정리 - 비동기 버전 (완전한 정리)"""
        logger.info(f"🧹 사용자 세션 비동기 정리 시작: {self.username}")
        
        # 거래 엔진 완전 중지
        if hasattr(self.trading_engine, 'is_running') and self.trading_engine.is_running:
            logger.info(f"🛑 {self.username}의 거래 엔진 비동기 중지")
            try:
                await self.trading_engine.stop_trading(manual_stop=True)
            except Exception as e:
                logger.error(f"⚠️ 거래 엔진 중지 중 오류: {str(e)}")
        
        # 동기 정리 수행
        self.cleanup()
        
        logger.info(f"✅ 사용자 세션 비동기 정리 완료: {self.username}")

class SessionManager:
    """전역 세션 관리자"""
    
    def __init__(self):
        self._sessions: Dict[int, UserSession] = {}
        logger.info("🎯 세션 관리자 초기화 완료 - 모든 이전 세션 삭제됨")
    
    def create_session(self, user_id: int, username: str) -> UserSession:
        """새로운 사용자 세션 생성"""
        # 기존 세션이 있으면 정리
        if user_id in self._sessions:
            logger.info(f"🔄 기존 세션 발견 - 정리 후 재생성: {username}")
            self._sessions[user_id].cleanup()
        
        # 새 세션 생성
        session = UserSession(user_id, username)
        self._sessions[user_id] = session
        
        logger.info(f"✅ 새 세션 생성 완료: {username} (총 {len(self._sessions)}개 활성 세션)")
        return session
    
    def get_session(self, user_id: int) -> Optional[UserSession]:
        """사용자 세션 조회"""
        session = self._sessions.get(user_id)
        if session:
            session.last_access = datetime.now()
        return session
    
    def remove_session(self, user_id: int):
        """사용자 세션 제거 - 동기 버전"""
        if user_id in self._sessions:
            username = self._sessions[user_id].username
            self._sessions[user_id].cleanup()
            del self._sessions[user_id]
            logger.info(f"🗑️ 세션 제거 완료: {username} (총 {len(self._sessions)}개 활성 세션)")
        else:
            logger.warning(f"⚠️ 제거할 세션이 존재하지 않음: user_id={user_id}")
    
    async def async_remove_session(self, user_id: int):
        """사용자 세션 제거 - 비동기 버전 (완전한 정리)"""
        if user_id in self._sessions:
            username = self._sessions[user_id].username
            await self._sessions[user_id].async_cleanup()
            del self._sessions[user_id]
            logger.info(f"🗑️ 세션 비동기 제거 완료: {username} (총 {len(self._sessions)}개 활성 세션)")
        else:
            logger.warning(f"⚠️ 제거할 세션이 존재하지 않음: user_id={user_id}")
    
    def get_active_sessions_count(self) -> int:
        """활성 세션 수 조회"""
        return len(self._sessions)
    
    def get_all_sessions(self) -> Dict[int, UserSession]:
        """모든 세션 조회 (관리자용)"""
        return self._sessions.copy()
    
    def cleanup_expired_sessions(self, max_idle_hours: int = 24):
        """만료된 세션 정리"""
        from datetime import timedelta
        now = datetime.now()
        expired_sessions = []
        
        for user_id, session in self._sessions.items():
            if now - session.last_access > timedelta(hours=max_idle_hours):
                expired_sessions.append(user_id)
        
        for user_id in expired_sessions:
            username = self._sessions[user_id].username
            self.remove_session(user_id)
            logger.info(f"🕐 만료된 세션 정리: {username}")
        
        if expired_sessions:
            logger.info(f"✅ 만료된 세션 {len(expired_sessions)}개 정리 완료")

# 전역 세션 관리자 인스턴스
session_manager = SessionManager()