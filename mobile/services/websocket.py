"""
🔌 모바일용 WebSocket 실시간 데이터 스트리밍

⚠️ 기존 시스템 안전성:
- 기존 시스템의 데이터를 읽기 전용으로만 접근합니다.
- 독립적인 WebSocket 연결로 기존 시스템에 영향을 주지 않습니다.
- Flutter 앱에 최적화된 실시간 데이터 스트리밍을 제공합니다.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

from .data_adapter import ReadOnlyDataAdapter
from ..models.mobile_response import MobileWebSocketMessage

logger = logging.getLogger(__name__)

class MobileWebSocketManager:
    """모바일용 WebSocket 연결 관리자"""
    
    def __init__(self):
        # WebSocket 연결 관리
        self.connections: Dict[str, Dict[str, Any]] = {}  # user_id -> connection_info
        self.channels: Dict[str, Set[str]] = {}  # channel -> user_ids
        
        # 데이터 어댑터
        self.data_adapter = ReadOnlyDataAdapter()
        
        # 서비스 상태
        self.is_running = False
        self.broadcast_tasks: Dict[str, asyncio.Task] = {}
        
        # 설정
        self.heartbeat_interval = 30  # 30초마다 heartbeat
        self.data_update_interval = 5  # 5초마다 데이터 업데이트
        
        logger.info("📱 모바일 WebSocket 매니저 초기화")
    
    async def start(self):
        """WebSocket 매니저 시작"""
        if self.is_running:
            logger.warning("⚠️ WebSocket 매니저가 이미 실행 중입니다")
            return
        
        self.is_running = True
        
        # 브로드캐스트 태스크 시작
        self.broadcast_tasks["heartbeat"] = asyncio.create_task(self._heartbeat_loop())
        self.broadcast_tasks["trading_status"] = asyncio.create_task(self._trading_status_loop())
        self.broadcast_tasks["portfolio_update"] = asyncio.create_task(self._portfolio_update_loop())
        
        logger.info("✅ 모바일 WebSocket 매니저 시작 완료")
    
    async def stop(self):
        """WebSocket 매니저 정지"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 모든 연결 종료
        for user_id in list(self.connections.keys()):
            await self.disconnect_user(user_id)
        
        # 브로드캐스트 태스크 정리
        for task_name, task in self.broadcast_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"🛑 브로드캐스트 태스크 정리: {task_name}")
        
        self.broadcast_tasks.clear()
        logger.info("✅ 모바일 WebSocket 매니저 정지 완료")
    
    async def connect_user(self, websocket: WebSocket, user_id: str, device_id: str = None):
        """사용자 WebSocket 연결"""
        try:
            await websocket.accept()
            
            # 기존 연결이 있다면 종료
            if user_id in self.connections:
                await self.disconnect_user(user_id)
            
            # 새 연결 등록
            self.connections[user_id] = {
                "websocket": websocket,
                "device_id": device_id,
                "connected_at": datetime.utcnow(),
                "last_heartbeat": datetime.utcnow(),
                "subscribed_channels": set()
            }
            
            logger.info(f"📱 사용자 연결: {user_id} ({device_id})")\n            \n            # 환영 메시지 전송\n            await self.send_to_user(user_id, {\n                "type": "welcome",\n                "channel": "system",\n                "data": {\n                    "message": "모바일 WebSocket 연결 성공",\n                    "user_id": user_id,\n                    "server_time": datetime.utcnow().isoformat()\n                }\n            })\n            \n            return True\n            \n        except Exception as e:\n            logger.error(f"❌ 사용자 연결 실패 {user_id}: {e}")\n            return False\n    \n    async def disconnect_user(self, user_id: str):\n        """사용자 WebSocket 연결 해제"""\n        if user_id not in self.connections:\n            return\n        \n        try:\n            connection_info = self.connections[user_id]\n            websocket = connection_info["websocket"]\n            \n            # 구독 채널에서 제거\n            for channel in connection_info["subscribed_channels"]:\n                if channel in self.channels and user_id in self.channels[channel]:\n                    self.channels[channel].remove(user_id)\n            \n            # WebSocket 연결 종료\n            try:\n                await websocket.close()\n            except:\n                pass\n            \n            # 연결 정보 제거\n            del self.connections[user_id]\n            \n            logger.info(f"📱 사용자 연결 해제: {user_id}")\n            \n        except Exception as e:\n            logger.error(f"❌ 사용자 연결 해제 실패 {user_id}: {e}")\n    \n    async def subscribe_channel(self, user_id: str, channel: str):\n        """채널 구독"""\n        if user_id not in self.connections:\n            return False\n        \n        # 채널이 없으면 생성\n        if channel not in self.channels:\n            self.channels[channel] = set()\n        \n        # 사용자를 채널에 추가\n        self.channels[channel].add(user_id)\n        self.connections[user_id]["subscribed_channels"].add(channel)\n        \n        logger.info(f"📡 채널 구독: {user_id} -> {channel}")\n        return True\n    \n    async def unsubscribe_channel(self, user_id: str, channel: str):\n        """채널 구독 해제"""\n        if user_id not in self.connections:\n            return False\n        \n        # 채널에서 사용자 제거\n        if channel in self.channels and user_id in self.channels[channel]:\n            self.channels[channel].remove(user_id)\n        \n        # 사용자 구독 목록에서 제거\n        if channel in self.connections[user_id]["subscribed_channels"]:\n            self.connections[user_id]["subscribed_channels"].remove(channel)\n        \n        logger.info(f"📡 채널 구독 해제: {user_id} -> {channel}")\n        return True\n    \n    async def send_to_user(self, user_id: str, data: Dict[str, Any]):\n        """특정 사용자에게 메시지 전송"""\n        if user_id not in self.connections:\n            return False\n        \n        try:\n            websocket = self.connections[user_id]["websocket"]\n            message = MobileWebSocketMessage(**data)\n            \n            await websocket.send_text(json.dumps(message.dict()))\n            return True\n            \n        except WebSocketDisconnect:\n            await self.disconnect_user(user_id)\n            return False\n        except Exception as e:\n            logger.error(f"❌ 메시지 전송 실패 {user_id}: {e}")\n            await self.disconnect_user(user_id)\n            return False\n    \n    async def broadcast_to_channel(self, channel: str, data: Dict[str, Any]):\n        """채널의 모든 사용자에게 브로드캐스트"""\n        if channel not in self.channels:\n            return 0\n        \n        success_count = 0\n        failed_users = []\n        \n        for user_id in list(self.channels[channel]):\n            if await self.send_to_user(user_id, data):\n                success_count += 1\n            else:\n                failed_users.append(user_id)\n        \n        # 실패한 사용자들 정리\n        for user_id in failed_users:\n            if channel in self.channels:\n                self.channels[channel].discard(user_id)\n        \n        return success_count\n    \n    async def handle_connection(self, websocket: WebSocket, user_id: str, device_id: str = None):\n        """WebSocket 연결 처리 (FastAPI 라우터에서 사용)"""\n        # 사용자 연결\n        if not await self.connect_user(websocket, user_id, device_id):\n            return\n        \n        try:\n            while self.is_running:\n                try:\n                    # 클라이언트 메시지 수신 (타임아웃 설정)\n                    message = await asyncio.wait_for(\n                        websocket.receive_text(),\n                        timeout=60.0\n                    )\n                    \n                    # 메시지 처리\n                    await self._handle_client_message(user_id, message)\n                    \n                except asyncio.TimeoutError:\n                    # 타임아웃 시 heartbeat 전송\n                    await self.send_to_user(user_id, {\n                        "type": "heartbeat",\n                        "channel": "system",\n                        "data": {"timestamp": datetime.utcnow().isoformat()}\n                    })\n                    \n                except WebSocketDisconnect:\n                    logger.info(f"📱 클라이언트 연결 해제: {user_id}")\n                    break\n                    \n        except Exception as e:\n            logger.error(f"❌ WebSocket 연결 처리 오류 {user_id}: {e}")\n        \n        finally:\n            await self.disconnect_user(user_id)\n    \n    async def _handle_client_message(self, user_id: str, message: str):\n        """클라이언트 메시지 처리"""\n        try:\n            data = json.loads(message)\n            msg_type = data.get("type")\n            \n            if msg_type == "subscribe":\n                channel = data.get("channel")\n                if channel:\n                    await self.subscribe_channel(user_id, channel)\n                    \n            elif msg_type == "unsubscribe":\n                channel = data.get("channel")\n                if channel:\n                    await self.unsubscribe_channel(user_id, channel)\n                    \n            elif msg_type == "ping":\n                await self.send_to_user(user_id, {\n                    "type": "pong",\n                    "channel": "system",\n                    "data": {"timestamp": datetime.utcnow().isoformat()}\n                })\n                \n            elif msg_type == "heartbeat":\n                self.connections[user_id]["last_heartbeat"] = datetime.utcnow()\n                \n            else:\n                logger.warning(f"⚠️ 알 수 없는 메시지 타입: {msg_type}")\n                \n        except json.JSONDecodeError:\n            logger.error(f"❌ 잘못된 JSON 메시지: {user_id}")\n        except Exception as e:\n            logger.error(f"❌ 클라이언트 메시지 처리 오류: {e}")\n    \n    async def _heartbeat_loop(self):\n        """주기적 heartbeat 브로드캐스트"""\n        while self.is_running:\n            try:\n                await asyncio.sleep(self.heartbeat_interval)\n                \n                if not self.connections:\n                    continue\n                \n                # 모든 연결된 사용자에게 heartbeat 전송\n                heartbeat_data = {\n                    "type": "heartbeat",\n                    "channel": "system",\n                    "data": {\n                        "timestamp": datetime.utcnow().isoformat(),\n                        "active_connections": len(self.connections)\n                    }\n                }\n                \n                for user_id in list(self.connections.keys()):\n                    await self.send_to_user(user_id, heartbeat_data)\n                \n                logger.debug(f"💓 Heartbeat 전송: {len(self.connections)}명")\n                \n            except asyncio.CancelledError:\n                break\n            except Exception as e:\n                logger.error(f"❌ Heartbeat 루프 오류: {e}")\n    \n    async def _trading_status_loop(self):\n        """거래 상태 실시간 브로드캐스트"""\n        while self.is_running:\n            try:\n                await asyncio.sleep(self.data_update_interval)\n                \n                if "trading_status" not in self.channels or not self.channels["trading_status"]:\n                    continue\n                \n                # 기존 시스템에서 거래 상태 조회 (읽기 전용)\n                trading_data = self.data_adapter.get_trading_state()\n                positions_data = self.data_adapter.get_current_positions()\n                \n                broadcast_data = {\n                    "type": "data",\n                    "channel": "trading_status",\n                    "data": {\n                        "trading_status": trading_data,\n                        "positions": positions_data,\n                        "timestamp": datetime.utcnow().isoformat()\n                    }\n                }\n                \n                sent_count = await self.broadcast_to_channel("trading_status", broadcast_data)\n                logger.debug(f"📊 거래 상태 브로드캐스트: {sent_count}명")\n                \n            except asyncio.CancelledError:\n                break\n            except Exception as e:\n                logger.error(f"❌ 거래 상태 루프 오류: {e}")\n    \n    async def _portfolio_update_loop(self):\n        """포트폴리오 실시간 업데이트 브로드캐스트"""\n        while self.is_running:\n            try:\n                await asyncio.sleep(self.data_update_interval)\n                \n                if "portfolio_update" not in self.channels or not self.channels["portfolio_update"]:\n                    continue\n                \n                # 기존 시스템에서 포트폴리오 데이터 조회 (읽기 전용)\n                portfolio_data = self.data_adapter.get_portfolio_summary()\n                \n                broadcast_data = {\n                    "type": "data",\n                    "channel": "portfolio_update",\n                    "data": {\n                        "portfolio": portfolio_data,\n                        "timestamp": datetime.utcnow().isoformat()\n                    }\n                }\n                \n                sent_count = await self.broadcast_to_channel("portfolio_update", broadcast_data)\n                logger.debug(f"💼 포트폴리오 브로드캐스트: {sent_count}명")\n                \n            except asyncio.CancelledError:\n                break\n            except Exception as e:\n                logger.error(f"❌ 포트폴리오 루프 오류: {e}")\n    \n    def get_connection_count(self) -> int:\n        """현재 연결 수 반환"""\n        return len(self.connections)\n    \n    def get_channel_stats(self) -> Dict[str, int]:\n        """채널별 구독자 수 통계"""\n        return {channel: len(users) for channel, users in self.channels.items()}\n    \n    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:\n        """사용자 연결 정보 조회"""\n        if user_id not in self.connections:\n            return None\n        \n        conn_info = self.connections[user_id]\n        return {\n            "user_id": user_id,\n            "device_id": conn_info.get("device_id"),\n            "connected_at": conn_info["connected_at"].isoformat(),\n            "last_heartbeat": conn_info["last_heartbeat"].isoformat(),\n            "subscribed_channels": list(conn_info["subscribed_channels"])\n        }