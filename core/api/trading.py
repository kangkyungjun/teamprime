"""거래 관련 API 라우터"""

from fastapi import APIRouter, Query, Depends
from typing import Dict, List, Any
import logging
import asyncio
import time
from datetime import datetime

from ..services.trading_engine import trading_engine, trading_state
from ..services.optimizer import auto_scheduler
from core.api.system import get_upbit_client
from ..auth.middleware import require_auth
from ..session import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trading"])

@router.post("/start-trading")
async def start_auto_trading(current_user: Dict[str, Any] = Depends(require_auth)):
    """자동거래 시작 - 세션별 사용자 격리"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 사용자별 거래 엔진 실행 상태 확인
        if user_session.trading_engine.is_running:
            return {"success": False, "message": "이미 거래가 실행 중입니다"}
        
        # API 키 설정 확인
        if not user_session.access_key or not user_session.secret_key:
            logger.warning(f"⚠️ {username} API 키가 설정되지 않았습니다")
            return {"success": False, "message": "API 키를 먼저 입력하고 업비트에 연결하세요."}
        
        # 로그인 상태 확인
        if not user_session.login_status["logged_in"] or user_session.trading_state.available_budget <= 0:
            logger.warning(f"⚠️ {username} 업비트 로그인 상태가 아닙니다")
            return {"success": False, "message": "업비트 연결이 필요합니다. API 키로 연결을 완료하세요."}
        
        # 사용자별 거래 엔진 시작
        await user_session.trading_engine.start_trading()
        
        logger.info(f"✅ {username} 자동거래 시작")
        return {
            "success": True, 
            "message": "자동거래가 시작되었습니다",
            "status": user_session.trading_engine.get_status()
        }
    except Exception as e:
        logger.error(f"자동거래 시작 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/trading-status")
async def get_trading_status(current_user: Dict[str, Any] = Depends(require_auth)):
    """거래 상태 조회 - 사용자별 세션 데이터"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 사용자 {username} 세션이 존재하지 않습니다")
            return {"error": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 사용자별 거래 엔진 상태 조회
        status = user_session.trading_engine.get_status()
        
        # 포지션 정보 추가 (사용자별)
        positions = {}
        for coin, position in user_session.trading_state.positions.items():
            positions[coin] = {
                "buy_price": position.buy_price,
                "amount": position.amount,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "profit_target": position.profit_target,
                "stop_loss": position.stop_loss,
                "timestamp": position.timestamp.isoformat()
            }
        
        status.update({
            "user": {"username": username, "user_id": user_id},
            "positions": positions,
            "available_budget": user_session.trading_state.available_budget,
            "daily_trades": user_session.trading_state.daily_trades,
            "daily_loss": user_session.trading_state.daily_loss,
            "scheduler_status": {
                "is_running": auto_scheduler.is_running,
                "next_run_time": auto_scheduler.get_next_run_time()
            }
        })
        
        return status
    except Exception as e:
        logger.error(f"거래 상태 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.post("/stop-trading")
async def stop_auto_trading(
    current_user: Dict[str, Any] = Depends(require_auth),
    emergency: bool = Query(False, description="긴급 중지 여부")
):
    """자동거래 중지 - 사용자별 세션 거래 엔진 중지"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 사용자별 거래 엔진 실행 상태 확인
        if not user_session.trading_engine.is_running:
            return {"success": False, "message": "거래가 실행 중이 아닙니다"}
        
        # 사용자별 거래 엔진 중지
        await user_session.trading_engine.stop_trading(manual_stop=True)
        
        message = "긴급 자동거래 중지" if emergency else "자동거래 중지"
        logger.info(f"✅ {username} {message} 완료")
        
        return {
            "success": True,
            "message": f"{message}되었습니다",
            "final_status": user_session.trading_engine.get_status()
        }
    except Exception as e:
        logger.error(f"자동거래 중지 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/coin-trading-criteria")
async def get_coin_trading_criteria():
    """코인별 거래 기준 조회"""
    try:
        criteria = {}
        for coin, params in trading_engine.optimized_params.items():
            criteria[coin] = {
                "volume_multiplier": params["volume_mult"],
                "price_change_threshold": params["price_change"],
                "candle_position": params["candle_pos"],
                "profit_target": params["profit_target"],
                "stop_loss": params["stop_loss"]
            }
        
        return {
            "criteria": criteria,
            "scalping_params": trading_engine.scalping_params,
            "api_call_intervals": trading_engine.api_call_scheduler["call_intervals"]
        }
    except Exception as e:
        logger.error(f"거래 기준 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/coin-api-status")
async def get_coin_api_status():
    """실시간 API 호출 상태 조회"""
    try:
        status = trading_engine.get_coin_api_status()
        
        # recent_completed에서 오래된 항목 정리 (30초 이상 된 것들)
        current_time = time.time()
        recent_completed = {}
        for coin, data in status["recent_completed"].items():
            if current_time - data["completion_time"] <= 30:  # 30초 내 완료된 것만 유지
                recent_completed[coin] = data
        
        status["recent_completed"] = recent_completed
        
        return {
            "success": True,
            "timestamp": current_time,
            **status
        }
    except Exception as e:
        logger.error(f"API 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/current-prices")
async def get_current_prices(request: dict):
    """여러 마켓의 현재가 한번에 조회"""
    try:
        markets = request.get("markets", [])
        if not markets:
            return {"success": True, "prices": {}}
        
        # 로그인 상태 확인
        upbit_client = get_upbit_client()
        if not upbit_client:
            return {"success": False, "message": "업비트 로그인이 필요합니다"}
        
        # 여러 마켓의 현재가 한번에 조회
        ticker_data = await upbit_client.get_ticker(markets)
        
        prices = {}
        for ticker in ticker_data:
            market = ticker["market"]
            prices[market] = {
                "trade_price": float(ticker["trade_price"]),
                "change_rate": float(ticker["change_rate"]) * 100,
                "timestamp": ticker["timestamp"]
            }
            
        
        return {"success": True, "prices": prices}
        
    except Exception as e:
        logger.error(f"현재가 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/account-balances")
async def get_account_balances():
    """실제 업비트 계좌 잔고 조회"""
    try:
        upbit_client = get_upbit_client()
        if not upbit_client:
            return {"success": False, "message": "업비트 로그인이 필요합니다"}
        
        accounts = await upbit_client.get_accounts()
        if not accounts:
            return {"success": False, "message": "계좌 정보 조회에 실패했습니다"}
        
        # 계좌 정보 정리
        balances = {}
        krw_balance = 0
        
        for account in accounts:
            currency = account.get("currency", "")
            balance = float(account.get("balance", 0))
            avg_buy_price = float(account.get("avg_buy_price", 0))
            locked = float(account.get("locked", 0))
            
            if currency == "KRW":
                krw_balance = balance
            elif balance > 0:  # 잔고가 있는 코인만
                market = f"KRW-{currency}"
                
                # 현재가 조회
                try:
                    ticker_data = await upbit_client.get_single_ticker(market)
                    current_price = float(ticker_data.get("trade_price", avg_buy_price))
                    current_value = balance * current_price
                    profit_loss = current_value - (avg_buy_price * balance) if avg_buy_price > 0 else 0
                except:
                    current_price = avg_buy_price
                    current_value = balance * current_price
                    profit_loss = 0
                
                balances[market] = {
                    "currency": currency,
                    "balance": balance,
                    "locked": locked,
                    "avg_buy_price": avg_buy_price,
                    "current_price": current_price,
                    "current_value": current_value,
                    "profit_loss": profit_loss,
                    "profit_rate": (profit_loss / (avg_buy_price * balance) * 100) if avg_buy_price > 0 and balance > 0 else 0
                }
        
        return {
            "success": True,
            "krw_balance": krw_balance,
            "coin_balances": balances,
            "total_balances": len(balances)
        }
        
    except Exception as e:
        logger.error(f"계좌 잔고 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}