"""업비트 API 호출 관리자 - 동시성 제어 및 60초 규정 준수"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any
from enum import IntEnum

logger = logging.getLogger(__name__)

class APIPriority(IntEnum):
    """API 호출 우선순위"""
    TRADING_ORDERS = 1      # 매수/매도 주문 (최우선)
    POSITION_MONITORING = 2  # 포지션 모니터링
    SIGNAL_ANALYSIS = 3     # 신호 분석
    ACCOUNT_SYNC = 4        # 계좌 동기화 (최후순위)

class UpbitAPIManager:
    """업비트 API 호출 중앙 관리자"""
    
    def __init__(self):
        self._call_queue = asyncio.PriorityQueue()
        self._last_call_times: Dict[str, float] = {}
        self._processing_lock = asyncio.Lock()
        self._is_processing = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # 60초 규정 준수
        self.MIN_INTERVAL = 60  # 초
        
        # 우선순위별 타임아웃
        self.TIMEOUTS = {
            APIPriority.TRADING_ORDERS: 30,
            APIPriority.POSITION_MONITORING: 20,
            APIPriority.SIGNAL_ANALYSIS: 20,
            APIPriority.ACCOUNT_SYNC: 30
        }
    
    async def start_worker(self):
        """API 호출 워커 시작"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("🚀 API 매니저 워커 시작됨")
    
    async def stop_worker(self):
        """API 호출 워커 중지"""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("⏹️ API 매니저 워커 중지됨")
    
    async def safe_api_call(
        self, 
        client, 
        method_name: str, 
        *args, 
        priority: APIPriority = APIPriority.ACCOUNT_SYNC,
        **kwargs
    ) -> Any:
        """안전한 API 호출 (60초 규정 준수)"""
        
        # 호출 요청을 큐에 추가
        future = asyncio.Future()
        call_info = {
            'client': client,
            'method_name': method_name,
            'args': args,
            'kwargs': kwargs,
            'future': future,
            'timestamp': time.time()
        }
        
        await self._call_queue.put((priority.value, call_info))
        
        # 워커가 실행 중이 아니면 시작
        if not self._is_processing:
            await self.start_worker()
        
        # 결과 대기 (타임아웃 적용)
        timeout = self.TIMEOUTS.get(priority, 30)
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"⏰ API 호출 타임아웃: {method_name} (우선순위: {priority.name})")
            raise
    
    async def _process_queue(self):
        """API 호출 큐 처리 워커"""
        self._is_processing = True
        
        try:
            while True:
                try:
                    # 큐에서 요청 가져오기 (1초 타임아웃)
                    priority, call_info = await asyncio.wait_for(
                        self._call_queue.get(), 
                        timeout=1.0
                    )
                    
                    await self._execute_call(call_info)
                    
                except asyncio.TimeoutError:
                    # 큐가 비어있으면 1초 대기 후 재시도
                    await asyncio.sleep(1)
                    continue
                    
                except Exception as e:
                    logger.error(f"⚠️ API 호출 처리 오류: {str(e)}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("🔄 API 호출 워커 취소됨")
        finally:
            self._is_processing = False
    
    async def _execute_call(self, call_info: Dict[str, Any]):
        """실제 API 호출 실행"""
        client = call_info['client']
        method_name = call_info['method_name']
        args = call_info['args']
        kwargs = call_info['kwargs']
        future = call_info['future']
        
        try:
            # 60초 규정 준수 체크
            endpoint_key = f"{method_name}_{str(args)}"
            current_time = time.time()
            last_call = self._last_call_times.get(endpoint_key, 0)
            
            if current_time - last_call < self.MIN_INTERVAL:
                wait_time = self.MIN_INTERVAL - (current_time - last_call)
                logger.info(f"⏳ 60초 규정 준수 대기: {wait_time:.1f}초 ({method_name})")
                await asyncio.sleep(wait_time)
            
            # API 호출 실행
            method = getattr(client, method_name)
            result = await method(*args, **kwargs)
            
            # 호출 시간 기록
            self._last_call_times[endpoint_key] = time.time()
            
            # 결과 반환
            if not future.done():
                future.set_result(result)
                
        except Exception as e:
            # 에러 반환
            if not future.done():
                future.set_exception(e)

# 전역 API 매니저 인스턴스
api_manager = UpbitAPIManager()