"""시스템 관련 API 라우터"""

from fastapi import APIRouter, Request, Depends
from typing import Dict, Optional
import logging
import time
from datetime import datetime

from ..services.optimizer import auto_scheduler
from ..services.trading_engine import trading_state
from ..auth.middleware import get_current_user, require_auth
from ..session import session_manager
from api_client import UpbitAPI

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])

# 🚨 LEGACY COMPATIBILITY ONLY - 레거시 호환성 전용
# 새로운 세션 시스템에서는 사용자별로 관리됨
login_status = {
    "logged_in": False,
    "account_info": None,
    "login_time": None
}

upbit_api_keys = {
    "access_key": "",
    "secret_key": ""
}

# 인증된 클라이언트 (거래용) - 레거시 호환성
upbit_client = None

# 공개 API 클라이언트 (캔들 데이터 조회용 - 인증 불필요)
class PublicUpbitAPI:
    """인증이 필요 없는 공개 업비트 API 클라이언트 - 레이트 리미터 통합"""
    
    def __init__(self):
        self.base_url = "https://api.upbit.com"
        self.session = None
        # 레이트 리미터 import
        from api_client import rate_limiter
        self.rate_limiter = rate_limiter
        
        # 캔들 데이터 캐시 (1분간 유효)
        self.candle_cache = {}
        self.cache_ttl = 60  # 1분
    
    async def _get_session(self):
        if self.session is None or self.session.closed:
            import aiohttp
            # HTTP 연결 Keep-Alive 강화 설정
            connector = aiohttp.TCPConnector(
                keepalive_timeout=60,      # Keep-Alive 타임아웃 60초
                enable_cleanup_closed=True, # 닫힌 연결 정리
                limit=100,                 # 최대 연결 수
                limit_per_host=30,         # 호스트당 최대 연결 수
                ttl_dns_cache=300,         # DNS 캐시 5분
                use_dns_cache=True         # DNS 캐시 사용
            )
            
            # 기본 헤더에 Keep-Alive 추가
            headers = {
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=60, max=1000",
                "User-Agent": "TradingBot/1.0"
            }
            
            timeout = aiohttp.ClientTimeout(
                total=30,      # 전체 타임아웃 30초
                connect=10,    # 연결 타임아웃 10초
                sock_read=20   # 소켓 읽기 타임아웃 20초
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=headers,
                timeout=timeout
            )
        return self.session
    
    async def get_minute_candles(self, market: str, count: int = 20):
        """1분봉 캔들 데이터 조회 (공개 API) - 레이트 리밋 및 캐싱 적용"""
        import time
        
        # 캐시 확인
        cache_key = f"{market}_{count}"
        current_time = time.time()
        
        if cache_key in self.candle_cache:
            cached_data, cache_time = self.candle_cache[cache_key]
            if current_time - cache_time < self.cache_ttl:
                logger.debug(f"📊 {market} 캔들 데이터 캐시에서 반환 ({len(cached_data)}개)")
                return cached_data
        
        # 레이트 리밋 대기
        await self.rate_limiter.wait_for_rest_slot()
        
        url = f"{self.base_url}/v1/candles/minutes/1"
        params = {
            'market': market,
            'count': count
        }
        
        session = await self._get_session()
        try:
            async with session.get(url, params=params) as response:
                # 요청 기록
                self.rate_limiter.record_rest_request()
                
                if response.status == 200:
                    data = await response.json()
                    # 캐시에 저장
                    self.candle_cache[cache_key] = (data, current_time)
                    logger.debug(f"📊 {market} 캔들 데이터 {len(data)}개 조회 성공 (캐시 저장)")
                    return data
                elif response.status == 429:
                    error_text = await response.text()
                    logger.warning(f"⚠️ {market} API 레이트 리밋 초과 429: {error_text}")
                    # 429 에러시 exponential backoff
                    await self._handle_rate_limit_error(market)
                    return []
                else:
                    error_text = await response.text()
                    logger.error(f"⚠️ {market} 캔들 데이터 조회 실패 {response.status}: {error_text}")
                    return []
        except Exception as e:
            logger.error(f"⚠️ {market} 캔들 데이터 조회 오류: {str(e)}")
            return []
    
    async def _handle_rate_limit_error(self, market: str):
        """429 에러 처리 - exponential backoff"""
        import asyncio
        backoff_time = 2.0  # 2초부터 시작
        max_backoff = 16.0  # 최대 16초
        
        while backoff_time <= max_backoff:
            logger.warning(f"⏳ {market} API 레이트 리밋 대기 중... ({backoff_time}초)")
            await asyncio.sleep(backoff_time)
            
            # 다시 시도 가능한지 확인
            if await self.rate_limiter.can_make_rest_request():
                logger.info(f"✅ {market} API 요청 재개 가능")
                break
                
            backoff_time = min(backoff_time * 2, max_backoff)
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

public_upbit_client = PublicUpbitAPI()

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": time.time()}

@router.get("/api/system-status")
async def get_system_status():
    """시스템 상태 조회"""
    try:
        return {
            "status": "running",
            "timestamp": time.time(),
            "components": {
                "database": "connected",
                "api": "running", 
                "scheduler": "running" if auto_scheduler.is_running else "stopped"
            },
            "message": "시스템이 정상 작동 중입니다"
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/api/data-quality")
async def get_data_quality():
    """데이터 품질 조회"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "overall_quality": 0.95,
            "markets": {},
            "freshness": "good",
            "completeness": "good",
            "message": "데이터 품질 조회 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"데이터 품질 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/api/cache-status")
async def get_cache_status():
    """캐시 상태 조회"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "cache_size": 0,
            "hit_rate": 0.0,
            "memory_usage": "0MB",
            "status": "healthy",
            "message": "캐시 상태 조회 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"캐시 상태 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.post("/api/run-manual-optimization")
async def run_manual_optimization():
    """수동 최적화 실행"""
    try:
        result = await auto_scheduler.run_manual_optimization()
        return result
    except Exception as e:
        logger.error(f"수동 최적화 실행 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/api/optimization-status")
async def get_optimization_status():
    """최적화 상태 조회"""
    try:
        return {
            "scheduler_running": auto_scheduler.is_running,
            "next_run_time": auto_scheduler.get_next_run_time(),
            "last_optimization": "구현 예정",
            "optimization_history": []
        }
    except Exception as e:
        logger.error(f"최적화 상태 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.post("/api/login")
async def login_with_upbit(request: dict, current_user: Dict = Depends(require_auth)):
    """업비트 API 로그인 - 세션별 사용자 격리"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회 또는 생성
        user_session = session_manager.get_session(user_id)
        if not user_session:
            user_session = session_manager.create_session(user_id, username)
            logger.info(f"🔐 {username} 새 세션 생성")
        
        access_key = request.get("access_key")
        secret_key = request.get("secret_key")
        
        if not access_key or not secret_key:
            return {"success": False, "message": "API 키가 필요합니다."}
        
        # 실제 업비트 API로 연결 테스트
        test_client = UpbitAPI(access_key, secret_key)
        
        try:
            accounts = await test_client.get_accounts()
            
            # 연결 성공 - 계좌 정보에서 KRW 잔고 찾기
            krw_account = next((acc for acc in accounts if acc['currency'] == 'KRW'), None)
            balance = float(krw_account['balance']) if krw_account else 0
            
            # 사용자별 세션에 API 키와 로그인 정보 저장
            user_session.update_api_keys(access_key, secret_key)
            user_session.set_upbit_client(test_client)
            user_session.update_login_status(True, {
                "balance": balance,
                "accounts": accounts
            })
            
            # 실제 계좌 잔고로 거래 예산 업데이트 (사용자별)
            user_session.trading_state.available_budget = balance
            
            # 🚨 레거시 호환성을 위해 전역 변수도 업데이트 (임시)
            global login_status, upbit_api_keys, upbit_client
            login_status["logged_in"] = True
            login_status["account_info"] = {"balance": balance, "accounts": accounts}
            login_status["login_time"] = datetime.now().isoformat()
            upbit_api_keys["access_key"] = access_key
            upbit_api_keys["secret_key"] = secret_key
            upbit_client = test_client
            trading_state.available_budget = balance
            
            logger.info(f"💰 {username} 업비트 로그인 성공: {balance:,.0f} KRW")
            
            return {
                "success": True,
                "message": "업비트 로그인 성공",
                "account_info": {
                    "currency": "KRW",
                    "balance": f"{balance:,.0f}"
                },
                "username": username
            }
            
        except Exception as api_error:
            error_msg = str(api_error)
            if "Invalid access key" in error_msg or "access_key" in error_msg.lower():
                return {"success": False, "message": "Access Key가 올바르지 않습니다."}
            elif "Invalid secret key" in error_msg or "secret_key" in error_msg.lower():
                return {"success": False, "message": "Secret Key가 올바르지 않습니다."}
            elif "401" in error_msg:
                return {"success": False, "message": "API 키 인증에 실패했습니다. 키를 확인해주세요."}
            else:
                return {"success": False, "message": f"업비트 API 오류: {error_msg}"}
        
    except Exception as e:
        logger.error(f"로그인 오류: {str(e)}")
        return {"success": False, "message": f"로그인 중 오류 발생: {str(e)}"}

@router.post("/api/logout")
async def logout():
    """로그아웃"""
    try:
        global login_status, upbit_api_keys, upbit_client
        
        # 로그인 상태 초기화
        login_status["logged_in"] = False
        login_status["account_info"] = None
        login_status["login_time"] = None
        
        # API 키 초기화
        upbit_api_keys["access_key"] = ""
        upbit_api_keys["secret_key"] = ""
        upbit_client = None
        
        # 거래 예산을 0으로 초기화 (로그인 시에만 실제 잔고 설정)
        trading_state.available_budget = 0.0
        logger.info("💰 거래 예산 초기화: 0 KRW (로그인 필요)")
        
        return {"success": True, "message": "로그아웃되었습니다."}
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {str(e)}")
        return {"success": False, "message": str(e)}

# 중복 /api/auth-login 엔드포인트 제거됨 - main.py의 새로운 보안 강화 방식 사용

def get_upbit_client():
    """현재 로그인된 업비트 클라이언트 반환 - 레거시 호환성"""
    global upbit_client
    return upbit_client

def get_user_upbit_client(user_id: int):
    """사용자별 업비트 클라이언트 반환"""
    user_session = session_manager.get_session(user_id)
    if user_session:
        return user_session.upbit_client
    return None