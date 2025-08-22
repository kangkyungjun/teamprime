"""분석 관련 API 라우터"""

from fastapi import APIRouter, Query, Depends
from typing import Dict, List, Optional, Any
import logging
import time

from ..auth.middleware import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

@router.get("/volume-surge-analysis")
async def volume_surge_analysis(
    market: str = Query(..., description="마켓 코드 (예: KRW-BTC)"),
    hours: int = Query(24, description="분석 기간 (시간)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """거래량 급증 분석"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "market": market,
            "analysis_period_hours": hours,
            "surge_detected": False,
            "volume_ratio": 1.0,
            "message": "거래량 분석 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"거래량 급증 분석 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/advanced-volume-surge-analysis")
async def advanced_volume_surge_analysis(
    market: str = Query(..., description="마켓 코드"),
    hours: int = Query(24, description="분석 기간"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """고급 거래량 급증 분석"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "market": market,
            "analysis_period_hours": hours,
            "advanced_metrics": {
                "surge_intensity": 0.0,
                "volume_trend": "stable",
                "momentum_score": 0.0
            },
            "message": "고급 거래량 분석 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"고급 거래량 분석 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/backtest-performance")
async def backtest_performance(
    market: str = Query(..., description="마켓 코드"),
    days: int = Query(30, description="백테스트 기간 (일)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """백테스트 성과 분석"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "market": market,
            "backtest_period_days": days,
            "performance": {
                "total_return": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "profit_factor": 0.0
            },
            "message": "백테스트 분석 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"백테스트 성과 분석 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/multi-coin-analysis")
async def multi_coin_analysis(
    hours: int = Query(24, description="분석 기간 (시간)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """멀티 코인 종합 분석"""
    try:
        # 실제 구현 예정 - 현재는 스텁
        return {
            "analysis_period_hours": hours,
            "coins": {},
            "summary": {
                "best_performer": None,
                "worst_performer": None,
                "market_sentiment": "neutral"
            },
            "message": "멀티 코인 분석 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"멀티 코인 분석 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/coin-comparison")
async def coin_comparison(
    markets: str = Query(..., description="비교할 마켓들 (쉼표로 구분)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """코인 비교 분석"""
    try:
        market_list = [m.strip() for m in markets.split(",")]
        
        # 실제 구현 예정 - 현재는 스텁
        return {
            "markets": market_list,
            "comparison": {},
            "ranking": [],
            "message": "코인 비교 분석 기능은 구현 예정입니다"
        }
    except Exception as e:
        logger.error(f"코인 비교 분석 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/real-time-buy-conditions")
async def real_time_buy_conditions(current_user: Dict[str, Any] = Depends(require_auth)):
    """실시간 매수 조건 상태 확인 - 상세 분석 포함 (API 호출 간격 최적화)"""
    import asyncio
    try:
        from ..services.signal_analyzer import signal_analyzer
        from ..session import session_manager
        from config import DEFAULT_MARKETS
        
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 실시간 매수 조건 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        results = []
        
        # 코인별 순차 처리 (간격을 두고 API 호출)
        for i, market in enumerate(DEFAULT_MARKETS):
            coin_symbol = market.split('-')[1]
            params = user_session.trading_engine.optimized_params.get(coin_symbol, user_session.trading_engine.optimized_params["BTC"])
            
            # 상세 분석으로 변경하여 실제 가격과 조건별 상태 확인
            detailed_analysis = await signal_analyzer.analyze_buy_conditions_detailed(market, params)
            
            results.append({
                "market": market,
                "coin": coin_symbol,
                "status": detailed_analysis.get("overall_signal", "조건x"),
                "signal_strength": detailed_analysis.get("signal_strength", 0),
                "current_price": detailed_analysis.get("current_price", 0),
                "conditions": detailed_analysis.get("conditions", {}),
                "data_available": detailed_analysis.get("data_available", False)
            })
            
            # 코인간 API 호출 간격 (마지막 코인 제외)
            if i < len(DEFAULT_MARKETS) - 1:
                await asyncio.sleep(2)  # 2초 간격으로 API 호출 분산
        
        return {"timestamp": int(time.time()), "conditions": results}
    except Exception as e:
        logger.error(f"실시간 매수 조건 확인 오류: {str(e)}")
        return {"error": str(e)}

@router.get("/buy-conditions-summary")
async def buy_conditions_summary(current_user: Dict[str, Any] = Depends(require_auth)):
    """매수 조건 요약 정보 - 세션별"""
    try:
        from ..services.signal_analyzer import signal_analyzer
        from ..session import session_manager
        from config import DEFAULT_MARKETS
        
        user_id = current_user.get("id")
        username = current_user.get("username")
        
        # 사용자 세션 조회
        user_session = session_manager.get_session(user_id)
        if not user_session:
            logger.error(f"⚠️ 매수 조건 요약 조회 - 사용자 {username} 세션이 존재하지 않습니다")
            return {"success": False, "message": "세션이 만료되었습니다. 다시 로그인해주세요."}
        
        results = []
        for market in DEFAULT_MARKETS:
            coin_symbol = market.split('-')[1]
            params = user_session.trading_engine.optimized_params.get(coin_symbol, user_session.trading_engine.optimized_params["BTC"])
            signal = await signal_analyzer.check_buy_signal(market, params)
            
            results.append({
                "market": market,
                "coin": coin_symbol,
                "status": "가능o" if signal else "조건x",
                "signal_strength": signal.get("signal_strength", 0) if signal else 0
            })
        
        return {"timestamp": int(time.time()), "conditions": results}
    except Exception as e:
        logger.error(f"매수 조건 요약 확인 오류: {str(e)}")
        return {"error": str(e)}