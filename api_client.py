"""
업비트 API 클라이언트 모듈
- UpbitRateLimiter: API 레이트 리밋 관리
- UpbitAPI: 업비트 REST API 클라이언트
"""

import asyncio
import time
import threading
from collections import deque
from typing import Dict, Optional, Any, List
import aiohttp
import hashlib
import hmac
import jwt
import uuid
from urllib.parse import urlencode, unquote
import logging

logger = logging.getLogger(__name__)

class UpbitRateLimiter:
    """업비트 API 레이트 리밋 관리자"""
    
    def __init__(self):
        # REST API 제한: 분당 600회, 초당 10회
        self.rest_per_second = 10
        self.rest_per_minute = 600
        
        # 주문 API 제한: 초당 8회, 분당 200회
        self.order_per_second = 8  
        self.order_per_minute = 200
        
        # 요청 기록 (타임스탬프 저장)
        self.rest_requests = deque()
        self.order_requests = deque()
        
        # 스레드 안전성을 위한 락
        self.rest_lock = threading.Lock()
        self.order_lock = threading.Lock()
        
        # 🏦 계정 단위 통합 요청 카운팅 (2024년 정책)
        self.total_requests = deque()  # 모든 API 요청 통합 추적
        self.total_lock = threading.Lock()
        
        # 우선순위 큐 (긴급한 요청 우선 처리)
        self.high_priority_queue = asyncio.Queue()
        self.normal_priority_queue = asyncio.Queue()
        
    def _clean_old_requests(self, request_queue: deque, time_window: int):
        """오래된 요청 기록 정리"""
        current_time = time.time()
        while request_queue and current_time - request_queue[0] > time_window:
            request_queue.popleft()
    
    async def can_make_rest_request(self) -> bool:
        """REST API 요청 가능 여부 확인"""
        with self.rest_lock:
            current_time = time.time()
            
            # 1분, 1초 윈도우 정리
            self._clean_old_requests(self.rest_requests, 60)  # 1분
            
            # 초당 제한 확인
            recent_requests = [req for req in self.rest_requests if current_time - req <= 1]
            if len(recent_requests) >= self.rest_per_second:
                return False
            
            # 분당 제한 확인
            if len(self.rest_requests) >= self.rest_per_minute:
                return False
                
            return True
    
    async def can_make_order_request(self) -> bool:
        """주문 API 요청 가능 여부 확인"""
        with self.order_lock:
            current_time = time.time()
            
            # 1분, 1초 윈도우 정리
            self._clean_old_requests(self.order_requests, 60)
            
            # 초당 제한 확인
            recent_requests = [req for req in self.order_requests if current_time - req <= 1]
            if len(recent_requests) >= self.order_per_second:
                return False
            
            # 분당 제한 확인
            if len(self.order_requests) >= self.order_per_minute:
                return False
                
            return True
    
    
    async def wait_for_rest_slot(self):
        """REST API 슬롯이 사용 가능할 때까지 대기 - 429 에러 방지 강화"""
        consecutive_waits = 0
        while not await self.can_make_rest_request():
            consecutive_waits += 1
            # 🔧 백오프 전략: 연속 대기 시 점진적 증가
            base_delay = 0.2 if consecutive_waits < 5 else 0.5  # 429 에러 방지
            delay = base_delay * (1.2 ** min(consecutive_waits, 10))  # 최대 약 6초
            await asyncio.sleep(delay)
            
            if consecutive_waits > 20:  # 극한 상황 방지
                print(f"⚠️ REST API 레이트 리밋 대기 중... ({consecutive_waits}회)")
    
    async def wait_for_order_slot(self):
        """주문 API 슬롯이 사용 가능할 때까지 대기 - 429 에러 방지 강화"""
        consecutive_waits = 0
        while not await self.can_make_order_request():
            consecutive_waits += 1
            # 🔧 주문 API는 더 보수적으로 처리
            base_delay = 0.3 if consecutive_waits < 3 else 0.8
            delay = base_delay * (1.5 ** min(consecutive_waits, 8))  # 최대 약 10초
            await asyncio.sleep(delay)
            
            if consecutive_waits > 15:
                print(f"⚠️ 주문 API 레이트 리밋 대기 중... ({consecutive_waits}회)")
    
    
    def record_rest_request(self):
        """REST API 요청 기록"""
        with self.rest_lock:
            self.rest_requests.append(time.time())
            # 통합 요청 기록
            with self.total_lock:
                self.total_requests.append(time.time())
    
    def record_order_request(self):
        """주문 API 요청 기록"""
        with self.order_lock:
            self.order_requests.append(time.time())
            # 통합 요청 기록
            with self.total_lock:
                self.total_requests.append(time.time())
    
    
    async def execute_rest_request(self, request_func, *args, **kwargs):
        """레이트 리밋을 고려한 REST 요청 실행"""
        await self.wait_for_rest_slot()
        self.record_rest_request()
        return await request_func(*args, **kwargs)
    
    async def execute_order_request(self, request_func, *args, **kwargs):
        """레이트 리밋을 고려한 주문 요청 실행"""
        await self.wait_for_order_slot()
        self.record_order_request()
        return await request_func(*args, **kwargs)
    
    def get_remaining_capacity(self) -> Dict:
        """남은 요청 용량 조회"""
        current_time = time.time()
        
        with self.rest_lock:
            self._clean_old_requests(self.rest_requests, 60)
            recent_rest = [req for req in self.rest_requests if current_time - req <= 1]
            
        with self.order_lock:
            self._clean_old_requests(self.order_requests, 60)
            recent_order = [req for req in self.order_requests if current_time - req <= 1]
        
        return {
            "rest_remaining_per_second": self.rest_per_second - len(recent_rest),
            "rest_remaining_per_minute": self.rest_per_minute - len(self.rest_requests),
            "order_remaining_per_second": self.order_per_second - len(recent_order),
            "order_remaining_per_minute": self.order_per_minute - len(self.order_requests)
        }


class UpbitAPI:
    """업비트 REST API 클라이언트"""
    
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = "https://api.upbit.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """aiohttp 세션 생성 또는 반환 - Keep-Alive 강화"""
        if self.session is None or self.session.closed:
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
                "User-Agent": "UpbitTradingBot/2.0"
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
    
    def _generate_jwt_token(self, query_string: str = None) -> str:
        """JWT 토큰 생성"""
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query_string:
            query_hash = hashlib.sha512(query_string.encode()).hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    async def get_accounts(self) -> List[Dict]:
        """계좌 정보 조회"""
        url = f"{self.base_url}/v1/accounts"
        headers = {
            'Authorization': f'Bearer {self._generate_jwt_token()}'
        }
        
        session = await self._get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"계좌 조회 실패 {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"계좌 조회 오류: {str(e)}")
    
    async def get_ticker(self, markets: List[str]) -> List[Dict]:
        """현재가 정보 조회"""
        markets_param = ','.join(markets)
        url = f"{self.base_url}/v1/ticker"
        params = {'markets': markets_param}
        
        session = await self._get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"현재가 조회 실패 {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"현재가 조회 오류: {str(e)}")
    
    async def buy_market_order(self, market: str, price: float) -> Dict:
        """시장가 매수 주문"""
        query = {
            'market': market,
            'side': 'bid',
            'ord_type': 'price',
            'price': str(price)
        }
        
        query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
        
        url = f"{self.base_url}/v1/orders"
        headers = {
            'Authorization': f'Bearer {self._generate_jwt_token(query_string.decode())}',
            'Content-Type': 'application/json'
        }
        
        session = await self._get_session()
        try:
            async with session.post(url, json=query, headers=headers) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"매수 주문 실패 {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"매수 주문 오류: {str(e)}")
    
    async def sell_market_order(self, market: str, volume: float) -> Dict:
        """시장가 매도 주문"""
        query = {
            'market': market,
            'side': 'ask',
            'ord_type': 'market',
            'volume': str(volume)
        }
        
        query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
        
        url = f"{self.base_url}/v1/orders"
        headers = {
            'Authorization': f'Bearer {self._generate_jwt_token(query_string.decode())}',
            'Content-Type': 'application/json'
        }
        
        session = await self._get_session()
        try:
            async with session.post(url, json=query, headers=headers) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"매도 주문 실패 {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"매도 주문 오류: {str(e)}")
    
    async def get_order(self, uuid: str) -> Dict:
        """주문 조회"""
        query = {'uuid': uuid}
        query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
        
        url = f"{self.base_url}/v1/order"
        headers = {
            'Authorization': f'Bearer {self._generate_jwt_token(query_string.decode())}'
        }
        
        session = await self._get_session()
        try:
            async with session.get(url, params=query, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"주문 조회 실패 {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"주문 조회 오류: {str(e)}")
    
    async def place_market_buy_order(self, market: str, price: float) -> Dict:
        """시장가 매수 주문 (거래 엔진용 래퍼)"""
        try:
            result = await self.buy_market_order(market, price)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def place_market_sell_order(self, market: str, volume: float) -> Dict:
        """시장가 매도 주문 (거래 엔진용 래퍼)"""
        try:
            result = await self.sell_market_order(market, volume)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_single_ticker(self, market: str) -> Dict:
        """단일 마켓 현재가 조회 (거래 엔진용 래퍼)"""
        try:
            result = await self.get_ticker([market])
            if result and len(result) > 0:
                return result[0]
            else:
                return {"error": "데이터 없음"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_minute_candles(self, market: str, count: int = 20) -> List[Dict]:
        """1분봉 캔들 데이터 조회"""
        url = f"{self.base_url}/v1/candles/minutes/1"
        params = {
            'market': market,
            'count': count
        }
        
        session = await self._get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"📊 {market} 캔들 데이터 {len(data)}개 조회 성공")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"⚠️ {market} 캔들 데이터 조회 실패 {response.status}: {error_text}")
                    return []
        except Exception as e:
            logger.error(f"⚠️ {market} 캔들 데이터 조회 오류: {str(e)}")
            return []
    
    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 글로벌 레이트 리미터 인스턴스
rate_limiter = UpbitRateLimiter()