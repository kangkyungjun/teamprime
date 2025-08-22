"""
실시간 데이터 및 알림 시스템 API
Server-Sent Events와 WebSocket을 통한 실시간 데이터 스트리밍
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..services.trading_engine import trading_state
from ..services.notification_service import notification_service
from ..utils.datetime_utils import utc_now
from ..auth.middleware import require_auth
from config import DEFAULT_MARKETS

router = APIRouter(tags=["실시간"])

# 활성 SSE 클라이언트 관리
active_connections: Dict[str, Dict] = {}

@router.get("/stream")
async def stream_trading_data(
    request: Request,
    markets: str = Query(default="", description="모니터링할 마켓 (쉼표 구분)"),
    interval: int = Query(default=5, ge=1, le=60, description="업데이트 간격 (초)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """실시간 거래 데이터 스트리밍 (Server-Sent Events)"""
    
    client_id = f"{current_user.get('session_id', 'unknown')}_{datetime.now().timestamp()}"
    
    # 클라이언트 설정
    client_config = {
        "user_id": current_user.get("session_id"),
        "markets": markets.split(",") if markets else DEFAULT_MARKETS,
        "interval": interval,
        "last_update": None,
        "connected_at": utc_now(),
    }
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 이벤트 생성기"""
        try:
            # 클라이언트 등록
            active_connections[client_id] = client_config
            
            # 연결 확인 이벤트
            yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id, 'timestamp': utc_now().isoformat()})}\n\n"
            
            while True:
                # 클라이언트 연결 확인
                if await request.is_disconnected():
                    break
                
                try:
                    # 실시간 데이터 수집
                    trading_data = _get_current_trading_data(client_config["markets"])
                    market_data = _get_current_market_data(client_config["markets"])
                    
                    # 데이터 변화 감지
                    current_time = utc_now()
                    last_update = client_config.get("last_update")
                    
                    # 이벤트 데이터 구성
                    event_data = {
                        "type": "update",
                        "timestamp": current_time.isoformat(),
                        "trading_status": {
                            "status": trading_data["status"],
                            "active_positions": trading_data["active_positions"],
                            "total_profit_loss": trading_data["total_profit_loss"],
                            "available_krw": trading_data["available_krw"],
                        },
                        "positions": trading_data["positions"],
                        "market_prices": market_data,
                        "alerts": _get_recent_alerts(last_update),
                    }
                    
                    # 클라이언트에 데이터 전송
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    
                    # 마지막 업데이트 시간 갱신
                    client_config["last_update"] = current_time
                    
                    # 간격 대기
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    # 오류 이벤트 전송
                    error_event = {
                        "type": "error",
                        "message": str(e),
                        "timestamp": utc_now().isoformat(),
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    break
                    
        except Exception as e:
            # 연결 오류 처리
            error_event = {
                "type": "connection_error",
                "message": str(e),
                "timestamp": utc_now().isoformat(),
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            
        finally:
            # 클라이언트 정리
            if client_id in active_connections:
                del active_connections[client_id]
    
    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )

@router.get("/stream-status")
async def get_stream_status(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """실시간 스트림 상태 조회"""
    try:
        user_id = current_user.get("session_id")
        user_connections = [
            {
                "client_id": client_id,
                "connected_at": config["connected_at"].isoformat(),
                "markets": config["markets"],
                "interval": config["interval"],
                "last_update": config["last_update"].isoformat() if config["last_update"] else None,
            }
            for client_id, config in active_connections.items()
            if config["user_id"] == user_id
        ]
        
        return {
            "success": True,
            "data": {
                "active_connections": len(user_connections),
                "connections": user_connections,
                "total_system_connections": len(active_connections),
                "server_time": utc_now().isoformat(),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트림 상태 조회 실패: {str(e)}")

@router.post("/notifications/register")
async def register_for_notifications(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 등록"""
    try:
        data = await request.json()
        
        user_id = current_user.get("session_id")
        device_token = data.get("device_token")
        platform = data.get("platform", "android")  # android, ios
        notification_settings = data.get("settings", {})
        
        # 알림 설정 기본값
        default_settings = {
            "trade_signals": True,
            "position_alerts": True,
            "profit_loss_alerts": True,
            "system_alerts": True,
            "emergency_alerts": True,
            "profit_threshold": 10000,  # 1만원 이상 수익시 알림
            "loss_threshold": -5000,    # 5천원 이상 손실시 알림
        }
        
        # 설정 병합
        merged_settings = {**default_settings, **notification_settings}
        
        # 알림 서비스에 등록
        await notification_service.register_device(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            settings=merged_settings
        )
        
        return {
            "success": True,
            "message": "알림 등록 완료",
            "data": {
                "user_id": user_id,
                "device_token": device_token[:10] + "..." if device_token else None,
                "settings": merged_settings,
                "registered_at": utc_now().isoformat(),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 등록 실패: {str(e)}")

@router.put("/notifications/settings")
async def update_notification_settings(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 설정 업데이트"""
    try:
        data = await request.json()
        user_id = current_user.get("session_id")
        
        # 알림 설정 업데이트
        await notification_service.update_user_settings(
            user_id=user_id,
            settings=data
        )
        
        return {
            "success": True,
            "message": "알림 설정 업데이트 완료",
            "data": {
                "user_id": user_id,
                "updated_settings": data,
                "updated_at": utc_now().isoformat(),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 설정 업데이트 실패: {str(e)}")

@router.get("/notifications/settings")
async def get_notification_settings(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 설정 조회"""
    try:
        user_id = current_user.get("session_id")
        
        # 사용자 알림 설정 조회
        settings = await notification_service.get_user_settings(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "settings": settings,
                "last_updated": settings.get("updated_at"),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 설정 조회 실패: {str(e)}")

@router.get("/notifications/history")
async def get_notification_history(
    days: int = Query(default=7, ge=1, le=30, description="조회 기간 (일)"),
    limit: int = Query(default=50, ge=1, le=200, description="최대 조회 건수"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """알림 히스토리 조회"""
    try:
        user_id = current_user.get("session_id")
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)
        
        # 알림 히스토리 조회
        notifications = await notification_service.get_notification_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "notifications": notifications,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "total_count": len(notifications),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알림 히스토리 조회 실패: {str(e)}")

@router.post("/notifications/test")
async def send_test_notification(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """테스트 알림 전송"""
    try:
        data = await request.json()
        user_id = current_user.get("session_id")
        message = data.get("message", "테스트 알림입니다.")
        
        # 테스트 알림 전송
        await notification_service.send_notification(
            user_id=user_id,
            title="TeamPrime 테스트 알림",
            message=message,
            notification_type="test",
            data={"test": True, "timestamp": utc_now().isoformat()}
        )
        
        return {
            "success": True,
            "message": "테스트 알림 전송 완료",
            "data": {
                "user_id": user_id,
                "test_message": message,
                "sent_at": utc_now().isoformat(),
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 알림 전송 실패: {str(e)}")

# 헬퍼 함수들

def _get_current_trading_data(markets: List[str]) -> Dict[str, Any]:
    """현재 거래 데이터 조회"""
    try:
        positions = trading_state.positions.copy()
        
        # 마켓 필터링
        if markets and markets != DEFAULT_MARKETS:
            positions = [p for p in positions if p.market in markets]
        
        return {
            "status": trading_state.is_active,
            "active_positions": len([p for p in positions if not p.is_closed]),
            "total_profit_loss": sum(p.profit_loss for p in positions),
            "available_krw": getattr(trading_state, 'available_krw', 0),
            "positions": [
                {
                    "market": p.market,
                    "symbol": p.market.split('-')[1],
                    "amount": p.amount,
                    "buy_price": p.buy_price,
                    "current_price": p.current_price,
                    "profit_loss": p.profit_loss,
                    "profit_loss_rate": p.profit_loss_rate,
                    "is_closed": p.is_closed,
                    "created_at": p.created_at.isoformat(),
                }
                for p in positions
            ]
        }
        
    except Exception as e:
        return {
            "status": False,
            "active_positions": 0,
            "total_profit_loss": 0,
            "available_krw": 0,
            "positions": [],
            "error": str(e),
        }

def _get_current_market_data(markets: List[str]) -> Dict[str, Any]:
    """현재 시장 데이터 조회"""
    try:
        # 실제 구현에서는 업비트 API나 캐시된 가격 데이터를 사용
        market_data = {}
        
        target_markets = markets if markets else DEFAULT_MARKETS
        
        for market in target_markets:
            # 여기서는 trading_state의 현재가 정보를 사용
            # 실제로는 별도의 가격 서비스에서 가져와야 함
            market_data[market] = {
                "market": market,
                "symbol": market.split('-')[1],
                "trade_price": 0,  # 실제 현재가
                "change": "EVEN",
                "change_price": 0,
                "change_rate": 0,
                "timestamp": utc_now().isoformat(),
            }
        
        return market_data
        
    except Exception as e:
        return {"error": str(e)}

def _get_recent_alerts(since: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """최근 알림 조회"""
    try:
        # 최근 알림 조회 (실제로는 알림 서비스나 데이터베이스에서)
        alerts = []
        
        # 예시 알림들
        current_time = utc_now()
        
        # 거래 신호 알림
        if trading_state.positions:
            recent_position = trading_state.positions[-1]
            if recent_position.profit_loss > 10000:  # 1만원 이상 수익
                alerts.append({
                    "type": "profit_alert",
                    "title": "수익 달성",
                    "message": f"{recent_position.market.split('-')[1]} 포지션에서 {recent_position.profit_loss:,.0f}원 수익 달성",
                    "timestamp": current_time.isoformat(),
                    "data": {
                        "market": recent_position.market,
                        "profit_loss": recent_position.profit_loss,
                    }
                })
        
        return alerts
        
    except Exception as e:
        return []

# 인증 미들웨어
try:
    from ..auth.middleware import get_current_user
    
    async def require_auth(request: Request):
        """인증 필수 미들웨어"""
        current_user = await get_current_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return current_user
        
except ImportError:
    # 임시 인증 함수
    def require_auth():
        return {"session_id": "test_session", "user_id": "test_user"}