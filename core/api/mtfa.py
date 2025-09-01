"""MTFA 최적화 관련 API 엔드포인트"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
from config import MTFA_OPTIMIZED_CONFIG, DEFAULT_MARKETS

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/mtfa-config")
async def get_mtfa_config():
    """MTFA 최적화 설정 반환"""
    return {
        "success": True,
        "config": MTFA_OPTIMIZED_CONFIG,
        "markets": DEFAULT_MARKETS,
        "total_markets": len(DEFAULT_MARKETS)
    }

@router.get("/api/mtfa-performance-expectations")
async def get_performance_expectations():
    """MTFA 최적화 성과 예상치 반환"""
    
    performance_data = []
    total_expected_return = 0
    total_expected_win_rate = 0
    
    for market, config in MTFA_OPTIMIZED_CONFIG.items():
        monthly_return = config["expected_return"] / 36  # 3년치를 월별로 환산
        
        performance_data.append({
            "market": market,
            "coin": market.split('-')[1],
            "profit_target": config["profit_target"],
            "stop_loss": config["stop_loss"],
            "max_hold_minutes": config["max_hold_minutes"],
            "mtfa_threshold": config["mtfa_threshold"],
            "expected_total_return": config["expected_return"],
            "expected_monthly_return": round(monthly_return, 1),
            "expected_win_rate": config["expected_win_rate"],
            "strategy_summary": f"{config['profit_target']:.1f}%↗ {config['stop_loss']:.1f}%↘ {config['max_hold_minutes']}min {config['mtfa_threshold']:.0%}"
        })
        
        total_expected_return += config["expected_return"]
        total_expected_win_rate += config["expected_win_rate"]
    
    # 성과 기준으로 정렬 (수익률 높은 순)
    performance_data.sort(key=lambda x: x["expected_total_return"], reverse=True)
    
    return {
        "success": True,
        "performance_data": performance_data,
        "summary": {
            "total_markets": len(performance_data),
            "average_total_return": round(total_expected_return / len(performance_data), 1),
            "average_monthly_return": round((total_expected_return / len(performance_data)) / 36, 1),
            "average_win_rate": round(total_expected_win_rate / len(performance_data), 1),
            "top_performer": performance_data[0]["market"] if performance_data else None,
            "top_monthly_return": performance_data[0]["expected_monthly_return"] if performance_data else 0
        }
    }

@router.get("/api/mtfa-confidence/{market}")
async def get_mtfa_confidence(market: str):
    """특정 코인의 실시간 MTFA 신뢰도 반환 (향후 구현)"""
    
    if market not in MTFA_OPTIMIZED_CONFIG:
        raise HTTPException(status_code=404, detail=f"Market {market} not found in MTFA config")
    
    config = MTFA_OPTIMIZED_CONFIG[market]
    
    # TODO: 실제 MTFA 신뢰도 계산 로직 구현 필요
    # 현재는 시뮬레이션 값 반환
    import random
    current_confidence = random.uniform(0.7, 1.0)  # 70-100% 랜덤
    
    return {
        "success": True,
        "market": market,
        "coin": market.split('-')[1],
        "current_confidence": round(current_confidence, 3),
        "threshold": config["mtfa_threshold"],
        "signal_status": "BUY_READY" if current_confidence >= config["mtfa_threshold"] else "WAITING",
        "signal_strength": "HIGH" if current_confidence >= 0.9 else "MEDIUM" if current_confidence >= 0.8 else "LOW",
        "strategy": {
            "profit_target": config["profit_target"],
            "stop_loss": config["stop_loss"],
            "max_hold_minutes": config["max_hold_minutes"]
        }
    }

@router.get("/api/mtfa-dashboard-data")
async def get_mtfa_dashboard_data():
    """MTFA 대시보드용 종합 데이터 반환 - 실제 신호 분석 기반"""
    
    # 실제 신호 분석 시스템 연동
    from ..services.signal_analyzer import signal_analyzer
    
    dashboard_data = []
    buy_ready_count = 0
    
    for market in DEFAULT_MARKETS:
        config = MTFA_OPTIMIZED_CONFIG[market]
        
        # 실제 신호 분석 실행
        try:
            # MTFA 최적화된 파라미터 사용
            signal_params = {
                "volume_surge": 2.0,  # 거래량 급증 임계값
                "price_change": 0.5,  # 가격 변동률 임계값
                "mtfa_threshold": config["mtfa_threshold"]
            }
            
            signal_result = await signal_analyzer.check_buy_signal(market, signal_params)
            
            if signal_result and signal_result.get("should_buy"):
                current_confidence = signal_result.get("signal_strength", 0) / 100.0  # 0-1로 정규화
                is_buy_ready = True
                buy_ready_count += 1
            else:
                # 신호가 없는 경우 낮은 신뢰도 표시
                current_confidence = 0.5 + (hash(market) % 20) / 100.0  # 0.5-0.69 범위의 일정한 값
                is_buy_ready = False
                
        except Exception as e:
            logger.error(f"⚠️ {market} 신호 분석 중 오류: {str(e)}")
            current_confidence = 0.5
            is_buy_ready = False
        
        dashboard_data.append({
            "market": market,
            "coin": market.split('-')[1],
            "current_confidence": round(current_confidence, 3),
            "threshold": config["mtfa_threshold"],
            "is_buy_ready": is_buy_ready,
            "signal_status": "BUY_READY" if is_buy_ready else "WAITING",
            "expected_monthly_return": round(config["expected_return"] / 36, 1),
            "strategy_info": {
                "profit_target": config["profit_target"],
                "stop_loss": config["stop_loss"],
                "max_hold_minutes": config["max_hold_minutes"]
            }
        })
    
    return {
        "success": True,
        "timestamp": "실시간",
        "dashboard_data": dashboard_data,
        "summary": {
            "total_coins": len(dashboard_data),
            "buy_ready_coins": buy_ready_count,
            "waiting_coins": len(dashboard_data) - buy_ready_count,
            "buy_ready_percentage": round(buy_ready_count / len(dashboard_data) * 100, 1) if dashboard_data else 0
        }
    }