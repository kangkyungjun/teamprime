"""
거래 내역 및 통계 API 엔드포인트
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from ..models.trading import TradingState
from ..services.trading_engine import trading_state
from ..utils.datetime_utils import utc_now
from ..auth.middleware import require_auth
from config import DEFAULT_MARKETS
from database import get_db

router = APIRouter(tags=["거래내역"])

@router.get("/trading-logs")
async def get_trading_logs(
    days: int = Query(default=7, ge=1, le=365, description="조회 기간 (일)"),
    market: Optional[str] = Query(default=None, description="특정 마켓 필터"),
    status: Optional[str] = Query(default=None, description="거래 상태 필터 (completed, failed, active)"),
    limit: int = Query(default=100, ge=1, le=1000, description="최대 조회 건수"),
    offset: int = Query(default=0, ge=0, description="시작 오프셋"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """거래 내역 조회"""
    try:
        # 기간 설정
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)
        
        # 실제 거래 내역 (현재는 trading_state의 positions 사용)
        positions = trading_state.positions.copy()
        
        # 필터링
        filtered_positions = []
        for position in positions:
            # 마켓 필터
            if market and position.market != market:
                continue
            
            # 상태 필터  
            if status:
                if status == "completed" and not position.is_closed:
                    continue
                elif status == "active" and position.is_closed:
                    continue
            
            filtered_positions.append(position)
        
        # 정렬 (최신순)
        filtered_positions.sort(key=lambda x: x.created_at, reverse=True)
        
        # 페이지네이션
        total_count = len(filtered_positions)
        paginated_positions = filtered_positions[offset:offset + limit]
        
        # 응답 데이터 구성
        trading_logs = []
        for position in paginated_positions:
            log_entry = {
                "id": f"pos_{position.market}_{int(position.created_at.timestamp())}",
                "market": position.market,
                "symbol": position.market.split('-')[1],
                "type": "buy" if position.amount > 0 else "sell",
                "amount": abs(position.amount),
                "buy_price": position.buy_price,
                "current_price": position.current_price,
                "profit_loss": position.profit_loss,
                "profit_loss_rate": position.profit_loss_rate,
                "status": "completed" if position.is_closed else "active",
                "created_at": position.created_at.isoformat(),
                "updated_at": position.updated_at.isoformat() if hasattr(position, 'updated_at') else position.created_at.isoformat(),
                "closed_at": position.closed_at.isoformat() if hasattr(position, 'closed_at') and position.closed_at else None,
                "duration": position.holding_time_minutes if hasattr(position, 'holding_time_minutes') else 0,
                "fees": 0.05,  # 업비트 수수료 (0.05%)
            }
            trading_logs.append(log_entry)
        
        return {
            "success": True,
            "data": {
                "logs": trading_logs,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total_count,
                    "has_prev": offset > 0
                },
                "filters": {
                    "days": days,
                    "market": market,
                    "status": status
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"거래 내역 조회 실패: {str(e)}")

@router.get("/trading-statistics")
async def get_trading_statistics(
    days: int = Query(default=30, ge=1, le=365, description="통계 기간 (일)"),
    market: Optional[str] = Query(default=None, description="특정 마켓 필터"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """거래 통계 조회"""
    try:
        # 기간 설정
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)
        
        # 현재 포지션들에서 통계 계산
        positions = trading_state.positions.copy()
        
        # 필터링
        if market:
            positions = [p for p in positions if p.market == market]
        
        # 기본 통계
        total_trades = len(positions)
        completed_trades = len([p for p in positions if p.is_closed])
        active_trades = total_trades - completed_trades
        
        # 손익 통계
        total_profit_loss = sum(p.profit_loss for p in positions)
        profitable_trades = len([p for p in positions if p.profit_loss > 0])
        loss_trades = len([p for p in positions if p.profit_loss < 0])
        
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 거래량 통계
        total_volume = sum(p.amount * p.buy_price for p in positions)
        avg_position_size = total_volume / total_trades if total_trades > 0 else 0
        
        # 수수료 계산
        total_fees = total_volume * 0.0005  # 업비트 수수료 0.05%
        
        # 마켓별 통계
        market_stats = {}
        for position in positions:
            market_key = position.market
            if market_key not in market_stats:
                market_stats[market_key] = {
                    "symbol": market_key.split('-')[1],
                    "trades": 0,
                    "profit_loss": 0,
                    "volume": 0,
                    "win_rate": 0
                }
            
            market_stats[market_key]["trades"] += 1
            market_stats[market_key]["profit_loss"] += position.profit_loss
            market_stats[market_key]["volume"] += position.amount * position.buy_price
        
        # 마켓별 승률 계산
        for market_key in market_stats:
            market_positions = [p for p in positions if p.market == market_key]
            profitable_count = len([p for p in market_positions if p.profit_loss > 0])
            market_stats[market_key]["win_rate"] = (profitable_count / len(market_positions) * 100) if market_positions else 0
        
        # 시간별 통계 (24시간 구간)
        hourly_stats = {}
        for i in range(24):
            hourly_stats[i] = {
                "hour": i,
                "trades": 0,
                "profit_loss": 0,
                "volume": 0
            }
        
        # 포지션들을 시간대별로 분류
        for position in positions:
            hour = position.created_at.hour
            if hour in hourly_stats:
                hourly_stats[hour]["trades"] += 1
                hourly_stats[hour]["profit_loss"] += position.profit_loss
                hourly_stats[hour]["volume"] += position.amount * position.buy_price
        
        return {
            "success": True,
            "data": {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "market_filter": market
                },
                "summary": {
                    "total_trades": total_trades,
                    "completed_trades": completed_trades,
                    "active_trades": active_trades,
                    "profitable_trades": profitable_trades,
                    "loss_trades": loss_trades,
                    "win_rate": round(win_rate, 2),
                    "total_profit_loss": round(total_profit_loss, 2),
                    "total_volume": round(total_volume, 2),
                    "avg_position_size": round(avg_position_size, 2),
                    "total_fees": round(total_fees, 2),
                    "net_profit": round(total_profit_loss - total_fees, 2)
                },
                "market_breakdown": [
                    {
                        "market": market_key,
                        "symbol": stats["symbol"],
                        "trades": stats["trades"],
                        "profit_loss": round(stats["profit_loss"], 2),
                        "volume": round(stats["volume"], 2),
                        "win_rate": round(stats["win_rate"], 2),
                        "percentage": round((stats["trades"] / total_trades * 100), 2) if total_trades > 0 else 0
                    }
                    for market_key, stats in market_stats.items()
                ],
                "hourly_breakdown": [
                    {
                        "hour": hour,
                        "trades": stats["trades"],
                        "profit_loss": round(stats["profit_loss"], 2),
                        "volume": round(stats["volume"], 2),
                        "avg_profit_per_trade": round(stats["profit_loss"] / stats["trades"], 2) if stats["trades"] > 0 else 0
                    }
                    for hour, stats in hourly_stats.items()
                    if stats["trades"] > 0
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"거래 통계 조회 실패: {str(e)}")

@router.get("/performance-chart")
async def get_performance_chart(
    days: int = Query(default=7, ge=1, le=90, description="차트 기간 (일)"),
    interval: str = Query(default="1h", description="차트 간격 (1h, 4h, 1d)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """성과 차트 데이터 조회"""
    try:
        # 기간 설정
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)
        
        # 간격 설정
        interval_hours = {
            "1h": 1,
            "4h": 4, 
            "1d": 24
        }.get(interval, 1)
        
        # 시간 포인트 생성
        time_points = []
        current_time = start_date
        while current_time <= end_date:
            time_points.append(current_time)
            current_time += timedelta(hours=interval_hours)
        
        # 포지션 데이터로부터 차트 데이터 생성
        positions = trading_state.positions.copy()
        
        chart_data = []
        cumulative_profit = 0
        
        for time_point in time_points:
            # 해당 시점까지의 포지션들 필터링
            positions_until_time = [
                p for p in positions 
                if p.created_at <= time_point
            ]
            
            # 해당 시점의 누적 손익 계산
            period_profit = sum(p.profit_loss for p in positions_until_time)
            cumulative_profit = period_profit
            
            # 해당 시간대의 거래량 계산
            period_volume = sum(
                p.amount * p.buy_price 
                for p in positions_until_time
            )
            
            # 해당 시간대의 거래 건수
            trade_count = len(positions_until_time)
            
            chart_data.append({
                "timestamp": time_point.isoformat(),
                "cumulative_profit": round(cumulative_profit, 2),
                "period_profit": round(period_profit, 2),
                "volume": round(period_volume, 2),
                "trade_count": trade_count,
                "avg_profit_per_trade": round(period_profit / trade_count, 2) if trade_count > 0 else 0
            })
        
        # 성과 지표 계산
        if chart_data:
            max_profit = max(d["cumulative_profit"] for d in chart_data)
            min_profit = min(d["cumulative_profit"] for d in chart_data)
            max_drawdown = max_profit - min_profit
            
            final_profit = chart_data[-1]["cumulative_profit"]
            initial_profit = chart_data[0]["cumulative_profit"]
            total_return = final_profit - initial_profit
        else:
            max_profit = min_profit = max_drawdown = 0
            total_return = 0
        
        return {
            "success": True,
            "data": {
                "period": {
                    "days": days,
                    "interval": interval,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "chart_data": chart_data,
                "performance_metrics": {
                    "total_return": round(total_return, 2),
                    "max_profit": round(max_profit, 2),
                    "min_profit": round(min_profit, 2),
                    "max_drawdown": round(max_drawdown, 2),
                    "total_trades": len(positions),
                    "avg_return_per_trade": round(total_return / len(positions), 2) if positions else 0
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성과 차트 조회 실패: {str(e)}")

@router.get("/market-analysis")
async def get_market_analysis(
    days: int = Query(default=7, ge=1, le=30, description="분석 기간 (일)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """마켓 분석 데이터 조회"""
    try:
        # 기간 설정
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)
        
        positions = trading_state.positions.copy()
        
        # 마켓별 상세 분석
        market_analysis = {}
        
        for position in positions:
            market = position.market
            if market not in market_analysis:
                market_analysis[market] = {
                    "market": market,
                    "symbol": market.split('-')[1],
                    "positions": [],
                    "total_profit_loss": 0,
                    "total_volume": 0,
                    "avg_hold_time": 0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "sharpe_ratio": 0
                }
            
            market_analysis[market]["positions"].append(position)
        
        # 각 마켓별 지표 계산
        analysis_results = []
        for market, data in market_analysis.items():
            positions_list = data["positions"]
            
            if not positions_list:
                continue
            
            # 기본 통계
            total_trades = len(positions_list)
            profitable_trades = len([p for p in positions_list if p.profit_loss > 0])
            win_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0
            
            # 손익 통계
            total_profit_loss = sum(p.profit_loss for p in positions_list)
            total_volume = sum(p.amount * p.buy_price for p in positions_list)
            
            # 수익률 통계
            returns = [p.profit_loss_rate for p in positions_list]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            # 보유 시간 통계
            hold_times = [
                getattr(p, 'holding_time_minutes', 5) 
                for p in positions_list
            ]
            avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
            
            # Profit Factor (총 수익 / 총 손실)
            gross_profit = sum(p.profit_loss for p in positions_list if p.profit_loss > 0)
            gross_loss = abs(sum(p.profit_loss for p in positions_list if p.profit_loss < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # 리스크 지표
            max_loss = min((p.profit_loss for p in positions_list), default=0)
            
            analysis_results.append({
                "market": market,
                "symbol": data["symbol"],
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "total_profit_loss": round(total_profit_loss, 2),
                "avg_return": round(avg_return, 2),
                "total_volume": round(total_volume, 2),
                "avg_hold_time_minutes": round(avg_hold_time, 1),
                "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
                "max_loss": round(max_loss, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "trade_frequency": round(total_trades / days, 2),
                "volatility": round(
                    (max(returns, default=0) - min(returns, default=0)), 2
                ) if returns else 0
            })
        
        # 정렬 (수익률 기준 내림차순)
        analysis_results.sort(key=lambda x: x["total_profit_loss"], reverse=True)
        
        return {
            "success": True,
            "data": {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "market_analysis": analysis_results,
                "summary": {
                    "total_markets": len(analysis_results),
                    "profitable_markets": len([m for m in analysis_results if m["total_profit_loss"] > 0]),
                    "best_performer": analysis_results[0] if analysis_results else None,
                    "worst_performer": analysis_results[-1] if analysis_results else None,
                    "avg_win_rate": round(
                        sum(m["win_rate"] for m in analysis_results) / len(analysis_results), 2
                    ) if analysis_results else 0
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"마켓 분석 조회 실패: {str(e)}")

# 인증 미들웨어 임포트 (실제 프로젝트에 맞게 조정 필요)
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
        return {"user_id": "test_user", "session_id": "test_session"}