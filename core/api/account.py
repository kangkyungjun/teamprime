"""계좌 정보 API 엔드포인트"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..services.account_service import account_service, AccountBalance, PortfolioAsset, PortfolioSummary
from ..auth.middleware import require_auth
from core.session.session_manager import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["account"])

@router.get("/balances")
async def get_account_balances(current_user: Dict[str, Any] = Depends(require_auth)):
    """계좌 잔고 조회"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        secret_key = session_data.get("secret_key")
        
        if not access_key or not secret_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 잔고 조회
        balances = await account_service.get_account_balances(access_key, secret_key)
        
        # 응답 데이터 구성
        balance_data = []
        for balance in balances:
            balance_data.append({
                "currency": balance.currency,
                "balance": balance.balance,
                "locked": balance.locked,
                "available_balance": balance.available_balance,
                "avg_buy_price": balance.avg_buy_price,
                "unit_currency": balance.unit_currency,
                "total_krw_value": balance.total_krw_value
            })
        
        return {
            "success": True,
            "balances": balance_data,
            "total_currencies": len(balance_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계좌 잔고 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/portfolio/summary")
async def get_portfolio_summary(current_user: Dict[str, Any] = Depends(require_auth)):
    """포트폴리오 요약 정보 조회"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        secret_key = session_data.get("secret_key")
        
        if not access_key or not secret_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 포트폴리오 분석
        summary = await account_service.get_portfolio_analysis(access_key, secret_key)
        
        return {
            "success": True,
            "portfolio": {
                "total_krw_balance": summary.total_krw_balance,
                "total_asset_value": summary.total_asset_value,
                "total_balance": summary.total_balance,
                "total_cost": summary.total_cost,
                "total_profit_loss": summary.total_profit_loss,
                "total_profit_loss_rate": round(summary.total_profit_loss_rate, 2),
                "asset_count": summary.asset_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 포트폴리오 요약 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/portfolio/details")
async def get_portfolio_details(current_user: Dict[str, Any] = Depends(require_auth)):
    """상세 포트폴리오 조회"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        secret_key = session_data.get("secret_key")
        
        if not access_key or not secret_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 상세 포트폴리오 조회
        assets = await account_service.get_detailed_portfolio(access_key, secret_key)
        
        # 응답 데이터 구성
        asset_data = []
        for asset in assets:
            asset_data.append({
                "market": asset.market,
                "currency": asset.currency,
                "balance": asset.balance,
                "avg_buy_price": asset.avg_buy_price,
                "current_price": asset.current_price,
                "total_value": asset.total_value,
                "total_cost": asset.total_cost,
                "profit_loss": asset.profit_loss,
                "profit_loss_rate": round(asset.profit_loss_rate, 2)
            })
        
        return {
            "success": True,
            "assets": asset_data,
            "total_assets": len(asset_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 상세 포트폴리오 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/asset/{market}")
async def get_asset_details(
    market: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """특정 자산 상세 정보 조회"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        secret_key = session_data.get("secret_key")
        
        if not access_key or not secret_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 상세 포트폴리오에서 해당 자산 찾기
        assets = await account_service.get_detailed_portfolio(access_key, secret_key)
        
        target_asset = None
        for asset in assets:
            if asset.market == market:
                target_asset = asset
                break
        
        if not target_asset:
            raise HTTPException(status_code=404, detail="해당 자산을 찾을 수 없습니다")
        
        return {
            "success": True,
            "asset": {
                "market": target_asset.market,
                "currency": target_asset.currency,
                "balance": target_asset.balance,
                "avg_buy_price": target_asset.avg_buy_price,
                "current_price": target_asset.current_price,
                "total_value": target_asset.total_value,
                "total_cost": target_asset.total_cost,
                "profit_loss": target_asset.profit_loss,
                "profit_loss_rate": round(target_asset.profit_loss_rate, 2)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 자산 상세 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/refresh-cache")
async def refresh_account_cache(current_user: Dict[str, Any] = Depends(require_auth)):
    """계좌 캐시 갱신"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        
        if not access_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 사용자 캐시 클리어
        account_service.clear_cache(access_key)
        
        return {
            "success": True,
            "message": "계좌 캐시가 갱신되었습니다",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 캐시 갱신 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/cache-status")
async def get_cache_status(current_user: Dict[str, Any] = Depends(require_auth)):
    """캐시 상태 조회"""
    try:
        status = account_service.get_cache_status()
        
        return {
            "success": True,
            "cache_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 캐시 상태 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/stats")
async def get_account_stats(current_user: Dict[str, Any] = Depends(require_auth)):
    """계좌 통계 정보"""
    try:
        # 세션에서 API 키 가져오기
        session_id = current_user.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 정보가 없습니다")
        
        session_data = session_manager.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다")
        
        access_key = session_data.get("access_key")
        secret_key = session_data.get("secret_key")
        
        if not access_key or not secret_key:
            raise HTTPException(status_code=400, detail="API 키가 설정되지 않았습니다")
        
        # 포트폴리오와 잔고 조회
        summary = await account_service.get_portfolio_analysis(access_key, secret_key)
        assets = await account_service.get_detailed_portfolio(access_key, secret_key)
        
        # 통계 계산
        profit_assets = [a for a in assets if a.profit_loss > 0]
        loss_assets = [a for a in assets if a.profit_loss < 0]
        
        best_performer = max(assets, key=lambda x: x.profit_loss_rate) if assets else None
        worst_performer = min(assets, key=lambda x: x.profit_loss_rate) if assets else None
        
        stats = {
            "total_balance": summary.total_balance,
            "total_profit_loss": summary.total_profit_loss,
            "total_profit_loss_rate": round(summary.total_profit_loss_rate, 2),
            "profit_assets_count": len(profit_assets),
            "loss_assets_count": len(loss_assets),
            "best_performer": {
                "market": best_performer.market,
                "profit_loss_rate": round(best_performer.profit_loss_rate, 2)
            } if best_performer else None,
            "worst_performer": {
                "market": worst_performer.market,
                "profit_loss_rate": round(worst_performer.profit_loss_rate, 2)
            } if worst_performer else None
        }
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 계좌 통계 조회 오류: {str(e)}")
        return {"success": False, "error": str(e)}