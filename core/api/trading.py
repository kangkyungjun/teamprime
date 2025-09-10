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
from config import MTFA_OPTIMIZED_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trading"])

async def _get_optimized_account_info(upbit_client, batch_tickers=True):
    """최적화된 계좌 정보 조회 - 배치 API 호출로 성능 향상"""
    try:
        accounts = await upbit_client.get_accounts()
        if not accounts:
            return None
            
        # 계좌 정보 정리
        balances = {}
        krw_balance = 0
        coin_markets = []
        
        # 1차: 계좌 데이터 정리 및 코인 마켓 리스트 수집
        for account in accounts:
            currency = account.get("currency", "")
            balance = float(account.get("balance", 0))
            avg_buy_price = float(account.get("avg_buy_price", 0))
            locked = float(account.get("locked", 0))
            
            if currency == "KRW":
                krw_balance = balance
            elif balance > 0:  # 잔고가 있는 코인만
                market = f"KRW-{currency}"
                coin_markets.append(market)
                balances[market] = {
                    "currency": currency,
                    "balance": balance,
                    "locked": locked,
                    "avg_buy_price": avg_buy_price,
                    "current_price": avg_buy_price,  # 기본값
                    "current_value": balance * avg_buy_price,
                    "profit_loss": 0,
                    "profit_rate": 0
                }
        
        # 2차: 배치로 모든 코인의 현재가 조회 (성능 최적화)
        if coin_markets and batch_tickers:
            try:
                # 업비트 API 제한으로 인해 최대 10개씩 배치 처리
                batch_size = 10
                for i in range(0, len(coin_markets), batch_size):
                    batch_markets = coin_markets[i:i + batch_size]
                    ticker_data = await upbit_client.get_ticker(batch_markets)
                    
                    for ticker in ticker_data:
                        market = ticker["market"]
                        if market in balances:
                            current_price = float(ticker.get("trade_price", balances[market]["avg_buy_price"]))
                            balance = balances[market]["balance"]
                            avg_buy_price = balances[market]["avg_buy_price"]
                            
                            balances[market]["current_price"] = current_price
                            balances[market]["current_value"] = balance * current_price
                            balances[market]["profit_loss"] = (balance * current_price) - (avg_buy_price * balance) if avg_buy_price > 0 else 0
                            balances[market]["profit_rate"] = (balances[market]["profit_loss"] / (avg_buy_price * balance) * 100) if avg_buy_price > 0 and balance > 0 else 0
                            
            except Exception as e:
                logger.warning(f"배치 현재가 조회 실패, 개별 조회로 전환: {str(e)}")
                # 배치 실패시 개별 조회로 폴백
                for market in coin_markets:
                    try:
                        ticker_data = await upbit_client.get_single_ticker(market)
                        current_price = float(ticker_data.get("trade_price", balances[market]["avg_buy_price"]))
                        balance = balances[market]["balance"]
                        avg_buy_price = balances[market]["avg_buy_price"]
                        
                        balances[market]["current_price"] = current_price
                        balances[market]["current_value"] = balance * current_price
                        balances[market]["profit_loss"] = (balance * current_price) - (avg_buy_price * balance) if avg_buy_price > 0 else 0
                        balances[market]["profit_rate"] = (balances[market]["profit_loss"] / (avg_buy_price * balance) * 100) if avg_buy_price > 0 and balance > 0 else 0
                    except:
                        continue  # 개별 조회 실패해도 다음으로 진행
        
        return {
            "krw_balance": krw_balance,
            "coin_balances": balances,
            "total_balances": len(balances)
        }
        
    except Exception as e:
        logger.error(f"계좌 정보 조회 오류: {str(e)}")
        return None

def _get_user_session_or_error(current_user: Dict[str, Any]):
    """사용자 세션 조회 및 에러 응답 생성 - 코드 중복 제거용 헬퍼"""
    user_id = current_user.get("id")
    username = current_user.get("username")
    
    user_session = session_manager.get_session(user_id)
    if not user_session:
        error_msg = f"⚠️ 사용자 {username} 세션이 존재하지 않습니다"
        logger.error(error_msg)
        return None, {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
    
    return user_session, None

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
        # 헬퍼 함수를 사용한 세션 조회 (코드 중복 제거)
        user_session, error_response = _get_user_session_or_error(current_user)
        if error_response:
            return {"error": error_response["message"]}
        
        # 사용자 정보 추출
        user_id = current_user.get("id")
        username = current_user.get("username")
        
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
        
        # 비상정지 또는 일반 중지 선택
        if emergency:
            logger.critical(f"🚨 비상정지 API 호출 - 사용자: {username} (stop-trading endpoint)")
            result = await user_session.trading_engine.emergency_stop()
            
            if not result.get("success", False):
                logger.error(f"❌ {username} 비상정지 실패: {result.get('message', '알 수 없는 오류')}")
                return {
                    "success": False,
                    "message": f"비상정지 실패: {result.get('message', '알 수 없는 오류')}",
                    "details": {"user": username}
                }
            
            message = "긴급 자동거래 중지(비상정지)"
        else:
            # 일반 중지
            await user_session.trading_engine.stop_trading(manual_stop=True)
            message = "자동거래 중지"
        
        logger.info(f"✅ {username} {message} 완료")
        
        return {
            "success": True,
            "message": f"{message}되었습니다",
            "final_status": user_session.trading_engine.get_status()
        }
    except Exception as e:
        logger.error(f"자동거래 중지 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/emergency-stop")
async def emergency_stop_trading(current_user: Dict[str, Any] = Depends(require_auth)):
    """비상정지 - 모든 포지션 즉시 청산 및 시스템 완전 중지"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.critical(f"🚨 비상정지 요청 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 비상정지 실행
        logger.critical(f"🚨 비상정지 API 호출 - 사용자: {username}")
        result = await user_session.trading_engine.emergency_stop()
        
        if result.get("success", False):
            logger.critical(f"✅ {username} 비상정지 성공")
            return {
                "success": True,
                "message": "비상정지가 성공적으로 실행되었습니다",
                "details": {
                    "positions_closed": 0,  # 비상정지로 이미 positions가 cleared 되었으므로
                    "emergency_time": datetime.now().isoformat(),
                    "user": username
                },
                "final_status": user_session.trading_engine.get_status()
            }
        else:
            logger.error(f"❌ {username} 비상정지 실패: {result.get('message', '알 수 없는 오류')}")
            return {
                "success": False,
                "message": result.get("message", "비상정지 중 오류가 발생했습니다"),
                "details": {"user": username}
            }
            
    except Exception as e:
        logger.critical(f"❌ 비상정지 API 오류: {str(e)}")
        return {
            "success": False,
            "message": f"비상정지 API 오류: {str(e)}",
            "details": {"error_type": "api_exception"}
        }

@router.get("/positions")
async def get_positions(current_user: Dict[str, Any] = Depends(require_auth)):
    """현재 보유 포지션 조회 - 고급 분석 정보 포함"""
    try:
        # 헬퍼 함수를 사용한 세션 조회 (코드 중복 제거)
        user_session, error_response = _get_user_session_or_error(current_user)
        if error_response:
            return error_response
        
        positions_data = []
        session_trading_state = user_session.trading_state
        
        for coin, position in session_trading_state.positions.items():
            profit_percent = ((position.current_price - position.buy_price) / position.buy_price) * 100
            holding_time = (datetime.now() - position.timestamp).total_seconds()
            
            position_info = {
                "coin": coin,
                "market": f"KRW-{coin}",
                "buy_price": position.buy_price,
                "current_price": position.current_price,
                "amount": position.amount,
                "unrealized_pnl": position.unrealized_pnl,
                "profit_percent": profit_percent,
                "holding_time_seconds": holding_time,
                "profit_target": position.profit_target,
                "stop_loss": position.stop_loss,
                "timestamp": position.timestamp.isoformat(),
                
                # 고급 분석 정보
                "trailing_stop_enabled": position.trailing_stop_enabled,
                "trailing_stop_percent": position.trailing_stop_percent,
                "highest_price_seen": position.highest_price_seen,
                "partial_profit_taken": position.partial_profit_taken,
                "profit_stages": position.profit_stages,
                "trend_direction": position.trend_direction,
                "risk_assessment": position.get_risk_assessment(),
                "recommended_action": position.get_recommended_action(),
                "trailing_stop_price": position.get_trailing_stop_price()
            }
            
            positions_data.append(position_info)
        
        return {
            "success": True,
            "positions": positions_data,
            "positions_count": len(positions_data),
            "total_unrealized_pnl": sum(pos.unrealized_pnl for pos in session_trading_state.positions.values())
        }
        
    except Exception as e:
        logger.error(f"포지션 조회 API 오류: {str(e)}")
        return {"success": False, "message": f"포지션 조회 중 오류: {str(e)}"}

@router.post("/positions/{coin}/close")
async def close_position(coin: str, current_user: Dict[str, Any] = Depends(require_auth)):
    """수동 포지션 청산"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 포지션 청산 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 포지션 존재 확인
        if coin not in user_session.trading_state.positions:
            return {"success": False, "message": f"{coin} 포지션이 존재하지 않습니다"}
        
        logger.info(f"👤 {username}이 {coin} 포지션 수동 청산 요청")
        
        # 수동 청산 실행
        await user_session.trading_engine._close_position(coin, "manual")
        
        return {"success": True, "message": f"{coin} 포지션이 청산되었습니다"}
        
    except Exception as e:
        logger.error(f"포지션 청산 API 오류: {str(e)}")
        return {"success": False, "message": f"포지션 청산 중 오류: {str(e)}"}

@router.post("/positions/{coin}/partial-sell")
async def partial_sell_position(
    coin: str, 
    sell_ratio: float = 0.5,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """부분 익절 실행"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 부분 익절 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 포지션 존재 확인
        if coin not in user_session.trading_state.positions:
            return {"success": False, "message": f"{coin} 포지션이 존재하지 않습니다"}
        
        # 매도 비율 검증
        if not 0.1 <= sell_ratio <= 0.9:
            return {"success": False, "message": "매도 비율은 10%~90% 사이여야 합니다"}
        
        logger.info(f"👤 {username}이 {coin} 포지션 {sell_ratio*100:.0f}% 부분 익절 요청")
        
        # 부분 익절 실행
        await user_session.trading_engine._execute_partial_sale(coin, sell_ratio)
        
        return {"success": True, "message": f"{coin} 포지션의 {sell_ratio*100:.0f}%가 익절되었습니다"}
        
    except Exception as e:
        logger.error(f"부분 익절 API 오류: {str(e)}")
        return {"success": False, "message": f"부분 익절 중 오류: {str(e)}"}

@router.post("/positions/{coin}/enable-trailing-stop")
async def enable_trailing_stop(
    coin: str,
    trailing_percent: float = 0.1,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """트레일링 스탑 활성화"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 트레일링 스탑 설정 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 포지션 존재 확인
        if coin not in user_session.trading_state.positions:
            return {"success": False, "message": f"{coin} 포지션이 존재하지 않습니다"}
        
        # 트레일링 비율 검증
        if not 0.05 <= trailing_percent <= 1.0:
            return {"success": False, "message": "트레일링 비율은 0.05%~1.0% 사이여야 합니다"}
        
        position = user_session.trading_state.positions[coin]
        position.trailing_stop_enabled = True
        position.trailing_stop_percent = trailing_percent
        
        logger.info(f"👤 {username}이 {coin} 포지션 트레일링 스탑 활성화 ({trailing_percent:.2f}%)")
        
        return {
            "success": True, 
            "message": f"{coin} 포지션의 트레일링 스탑이 {trailing_percent:.2f}%로 설정되었습니다"
        }
        
    except Exception as e:
        logger.error(f"트레일링 스탑 설정 API 오류: {str(e)}")
        return {"success": False, "message": f"트레일링 스탑 설정 중 오류: {str(e)}"}

@router.get("/positions/{coin}/analysis")
async def get_position_analysis(coin: str, current_user: Dict[str, Any] = Depends(require_auth)):
    """개별 포지션 상세 분석"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 포지션 분석 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 포지션 존재 확인
        if coin not in user_session.trading_state.positions:
            return {"success": False, "message": f"{coin} 포지션이 존재하지 않습니다"}
        
        position = user_session.trading_state.positions[coin]
        profit_percent = ((position.current_price - position.buy_price) / position.buy_price) * 100
        holding_time = (datetime.now() - position.timestamp).total_seconds()
        
        # 상세 분석 정보
        analysis = {
            "basic_info": {
                "coin": coin,
                "buy_price": position.buy_price,
                "current_price": position.current_price,
                "amount": position.amount,
                "unrealized_pnl": position.unrealized_pnl,
                "profit_percent": profit_percent,
                "holding_time_seconds": holding_time
            },
            "risk_analysis": {
                "risk_level": position.get_risk_assessment(),
                "recommended_action": position.get_recommended_action(),
                "profit_stage_action": position.get_profit_stage_action()
            },
            "trailing_stop": {
                "enabled": position.trailing_stop_enabled,
                "percent": position.trailing_stop_percent,
                "current_trailing_price": position.get_trailing_stop_price(),
                "highest_price_seen": position.highest_price_seen
            },
            "trading_signals": {
                "trend_direction": position.trend_direction,
                "consecutive_up_ticks": position.consecutive_up_ticks,
                "consecutive_down_ticks": position.consecutive_down_ticks,
                "price_volatility": position.price_volatility
            },
            "profit_management": {
                "partial_profit_taken": position.partial_profit_taken,
                "profit_stages": position.profit_stages,
                "should_take_partial_profit": position.should_take_partial_profit(),
                "should_execute_trailing_stop": position.should_execute_trailing_stop()
            },
            "price_targets": {
                "profit_target": position.profit_target,
                "stop_loss": position.stop_loss,
                "quick_profit_alert": position.price_alerts.get("quick_profit", 0),
                "warning_loss_alert": position.price_alerts.get("warning_loss", 0)
            }
        }
        
        return {"success": True, "analysis": analysis}
        
    except Exception as e:
        logger.error(f"포지션 분석 API 오류: {str(e)}")
        return {"success": False, "message": f"포지션 분석 중 오류: {str(e)}"}

@router.get("/trading-verification/metrics")
async def get_trading_verification_metrics(current_user: Dict[str, Any] = Depends(require_auth)):
    """거래 검증 지표 조회"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 거래 검증 지표 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 거래 검증 지표 조회
        from ..services.trade_verifier import trade_verifier
        metrics = trade_verifier.get_trading_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"거래 검증 지표 API 오류: {str(e)}")
        return {"success": False, "message": f"거래 검증 지표 조회 중 오류: {str(e)}"}

@router.get("/trading-verification/recent")
async def get_recent_verifications(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """최근 거래 검증 결과 조회"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 거래 검증 기록 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 최근 검증 결과 조회
        from ..services.trade_verifier import trade_verifier
        recent_verifications = trade_verifier.get_recent_verifications(limit)
        
        return {
            "success": True,
            "verifications": recent_verifications,
            "count": len(recent_verifications),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"거래 검증 기록 API 오류: {str(e)}")
        return {"success": False, "message": f"거래 검증 기록 조회 중 오류: {str(e)}"}

@router.get("/trading-verification/order/{order_id}")
async def get_order_verification_status(order_id: str, current_user: Dict[str, Any] = Depends(require_auth)):
    """개별 주문 검증 상태 조회"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 주문 검증 상태 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 주문 검증 상태 조회
        from ..services.trade_verifier import trade_verifier
        verification_status = trade_verifier.get_verification_status(order_id)
        
        if not verification_status:
            return {"success": False, "message": f"주문 ID {order_id}에 대한 검증 정보를 찾을 수 없습니다"}
        
        return {
            "success": True,
            "verification": verification_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"주문 검증 상태 API 오류: {str(e)}")
        return {"success": False, "message": f"주문 검증 상태 조회 중 오류: {str(e)}"}

@router.post("/trading-verification/manual-verify/{order_id}")
async def manual_verify_order(order_id: str, current_user: Dict[str, Any] = Depends(require_auth)):
    """수동 주문 검증 실행"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 수동 주문 검증 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        # 업비트 클라이언트 확인
        upbit_client = user_session.upbit_client
        if not upbit_client:
            return {"success": False, "message": "업비트 API 연결이 필요합니다"}
        
        logger.info(f"👤 {username}이 수동 주문 검증 요청: {order_id}")
        
        # 수동 검증 실행
        from ..services.trade_verifier import trade_verifier
        success = await trade_verifier.verify_order_with_client(order_id, upbit_client)
        
        if success:
            return {"success": True, "message": f"주문 {order_id} 검증이 완료되었습니다"}
        else:
            return {"success": False, "message": f"주문 {order_id} 검증에 실패했습니다"}
        
    except Exception as e:
        logger.error(f"수동 주문 검증 API 오류: {str(e)}")
        return {"success": False, "message": f"수동 주문 검증 중 오류: {str(e)}"}


@router.get("/coin-trading-criteria")
async def get_coin_trading_criteria(current_user: Dict[str, Any] = Depends(require_auth)):
    """코인별 거래 기준 조회 - 세션별"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 거래 기준 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        criteria = {}
        from config import MTFA_OPTIMIZED_CONFIG, DEFAULT_MARKETS
        
        for market in DEFAULT_MARKETS:
            coin_symbol = market.split('-')[1]
            config = MTFA_OPTIMIZED_CONFIG.get(market, {})
            criteria[coin_symbol] = {
                "volume_multiplier": 2.0,  # 기본값
                "price_change_threshold": 0.5,  # 기본값
                "candle_position": 50,  # 기본값
                "profit_target": config.get("profit_target", 2.5),
                "stop_loss": config.get("stop_loss", -1.0),
                "max_hold_minutes": config.get("max_hold_minutes", 60),
                "mtfa_threshold": config.get("mtfa_threshold", 0.80)
            }
        
        return {
            "criteria": criteria,
            "scalping_params": user_session.trading_engine.scalping_params,
            "api_call_intervals": user_session.trading_engine.api_call_scheduler["call_intervals"]
        }
    except Exception as e:
        logger.error(f"거래 기준 조회 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/coin-api-status")
async def get_coin_api_status(current_user: Dict[str, Any] = Depends(require_auth)):
    """실시간 API 호출 상태 조회 - 세션별"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ API 상태 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        status = user_session.trading_engine.get_coin_api_status()
        
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


@router.get("/account-balances")
async def get_account_balances(current_user: Dict[str, Any] = Depends(require_auth)):
    """실제 업비트 계좌 잔고 조회 - 사용자별 세션"""
    try:
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 계좌 잔고 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        upbit_client = user_session.upbit_client if user_session.upbit_client else get_upbit_client()
        if not upbit_client:
            return {"success": False, "message": "업비트 로그인이 필요합니다"}
        
        # 최적화된 계좌 정보 조회 사용
        account_info = await _get_optimized_account_info(upbit_client, batch_tickers=True)
        if not account_info:
            return {"success": False, "message": "계좌 정보 조회에 실패했습니다"}
        
        return {
            "success": True,
            **account_info
        }
        
    except Exception as e:
        logger.error(f"계좌 잔고 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/dashboard-data")
async def get_dashboard_data(current_user: Dict[str, Any] = Depends(require_auth)):
    """대시보드용 통합 데이터 조회 - 세션별 사용자 데이터 제공"""
    try:
        from config import DEFAULT_MARKETS
        
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 대시보드 데이터 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        dashboard_data = {
            "success": True,
            "timestamp": time.time(),
            "user": {"username": username, "user_id": user_id},
            "account_info": {"success": False},
            "trading_status": {},
            "current_prices": {},
            "buy_conditions": [],
            "system_status": "running"
        }
        
        # 1. 계좌 정보 조회 (최적화된 헬퍼 메서드 사용)
        try:
            upbit_client = user_session.upbit_client if user_session.upbit_client else get_upbit_client()
            if upbit_client:
                account_info = await _get_optimized_account_info(upbit_client, batch_tickers=True)
                if account_info:
                    dashboard_data["account_info"] = {
                        "success": True,
                        **account_info
                    }
                else:
                    dashboard_data["account_info"] = {"success": False, "message": "계좌 정보 조회에 실패했습니다"}
            else:
                dashboard_data["account_info"] = {"success": False, "message": "업비트 로그인이 필요합니다"}
        except Exception as e:
            logger.warning(f"계좌 정보 조회 실패: {str(e)}")
            dashboard_data["account_info"] = {"success": False, "error": str(e)}
        
        # 2. 거래 상태 조회 (사용자별 세션 데이터)
        try:
            dashboard_data["trading_status"] = {
                "is_running": user_session.trading_engine.is_running,
                "positions_count": len(user_session.trading_state.positions),
                "available_budget": user_session.trading_state.available_budget,
                "daily_trades": user_session.trading_state.daily_trades,
                "daily_loss": user_session.trading_state.daily_loss,
                "uptime_seconds": time.time() - user_session.trading_engine.session_start_time if user_session.trading_engine.session_start_time else 0,
                "positions": {}
            }
            
            # 포지션 정보 추가 (사용자별)
            for coin, position in user_session.trading_state.positions.items():
                dashboard_data["trading_status"]["positions"][coin] = {
                    "buy_price": position.buy_price,
                    "amount": position.amount,
                    "current_price": position.current_price,
                    "unrealized_pnl": position.unrealized_pnl,
                    "profit_target": position.profit_target,
                    "stop_loss": position.stop_loss,
                    "timestamp": position.timestamp.isoformat()
                }
                
        except Exception as e:
            logger.warning(f"거래 상태 조회 실패: {str(e)}")
            dashboard_data["trading_status"] = {"error": str(e)}
        
        # 3. 주요 코인 현재가 조회 (사용자별 클라이언트 사용)
        try:
            upbit_client = user_session.upbit_client if user_session.upbit_client else get_upbit_client()
            if upbit_client:
                market_list = list(DEFAULT_MARKETS)[:5]  # 처음 5개만
                ticker_data = await upbit_client.get_ticker(market_list)
                
                prices = {}
                for ticker in ticker_data:
                    market = ticker["market"]
                    prices[market] = {
                        "trade_price": float(ticker["trade_price"]),
                        "change_rate": float(ticker["change_rate"]) * 100,
                        "coin_symbol": market.split('-')[1]
                    }
                
                dashboard_data["current_prices"] = prices
                
        except Exception as e:
            logger.warning(f"현재가 조회 실패: {str(e)}")
            dashboard_data["current_prices"] = {}
        
        # 4. 매수 조건 간단 요약 (처음 3개 코인만)
        try:
            from ..services.signal_analyzer import signal_analyzer
            
            conditions = []
            for market in list(DEFAULT_MARKETS)[:3]:  # 처음 3개만
                coin_symbol = market.split('-')[1]
                config = MTFA_OPTIMIZED_CONFIG.get(market, MTFA_OPTIMIZED_CONFIG.get("KRW-BTC", {}))
                
                # MTFA 최적화된 파라미터 사용
                params = {
                    "volume_surge": 2.0,
                    "price_change": 0.5,
                    "mtfa_threshold": config.get("mtfa_threshold", 0.80),
                    "rsi_period": 14,
                    "ema_periods": [5, 20],
                    "volume_window": 24
                }
                signal = await signal_analyzer.check_buy_signal(market, params)
                
                conditions.append({
                    "market": market,
                    "coin": coin_symbol,
                    "status": "가능o" if signal else "조건x",
                    "signal_strength": signal.get("signal_strength", 0) if signal else 0
                })
                
                # API 과부하 방지를 위해 짧은 대기
                await asyncio.sleep(0.5)
            
            dashboard_data["buy_conditions"] = conditions
            
        except Exception as e:
            logger.warning(f"매수 조건 조회 실패: {str(e)}")
            dashboard_data["buy_conditions"] = []
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}