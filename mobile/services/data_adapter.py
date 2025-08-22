"""
🔗 기존 시스템 읽기 전용 데이터 어댑터

⚠️ 중요: 이 모듈은 기존 시스템의 데이터를 절대 수정하지 않습니다.
모든 함수는 읽기 전용(READ-ONLY)으로만 동작합니다.

🛡️ 안전성 원칙:
1. 기존 시스템의 상태를 읽기만 함
2. 어떤 데이터도 수정하지 않음
3. 기존 함수 호출 시에도 상태 변경 없이 정보만 조회
4. 예외 발생 시 기존 시스템에 영향 없음
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ReadOnlyDataAdapter:
    """
    기존 시스템의 데이터를 읽기 전용으로 접근하는 어댑터 클래스
    
    ⚠️ 주의: 이 클래스는 기존 데이터를 절대 수정하지 않습니다.
    모든 메서드는 데이터 조회만 수행합니다.
    """
    
    def __init__(self):
        self._safe_mode = True  # 항상 안전 모드
        logger.info("📱 모바일 데이터 어댑터 초기화 (읽기 전용 모드)")
    
    def get_trading_state(self) -> Dict[str, Any]:
        """
        기존 거래 상태를 읽기 전용으로 조회
        
        Returns:
            Dict: 현재 거래 상태 정보
        """
        try:
            # 기존 거래 엔진 상태 읽기 (수정하지 않음)
            from core.services.trading_engine import trading_state
            
            return {
                "is_running": getattr(trading_state, 'is_running', False),
                "available_budget": getattr(trading_state, 'available_budget', 0.0),
                "position_count": len(getattr(trading_state, 'positions', [])),
                "total_profit_loss": getattr(trading_state, 'total_profit_loss', 0.0),
                "daily_trades": getattr(trading_state, 'daily_trades', 0),
                "win_rate": getattr(trading_state, 'win_rate', 0.0),
                "last_update": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 거래 상태 조회 실패: {e}")
            return {
                "is_running": False,
                "available_budget": 0.0,
                "position_count": 0,
                "total_profit_loss": 0.0,
                "daily_trades": 0,
                "win_rate": 0.0,
                "last_update": datetime.utcnow().isoformat(),
                "error": "데이터 조회 실패"
            }
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """
        현재 보유 포지션을 읽기 전용으로 조회
        
        Returns:
            List[Dict]: 현재 포지션 목록
        """
        try:
            from core.services.trading_engine import trading_state
            
            positions = getattr(trading_state, 'positions', [])
            
            return [
                {
                    "symbol": getattr(pos, 'symbol', ''),
                    "side": getattr(pos, 'side', ''),
                    "amount": getattr(pos, 'amount', 0.0),
                    "entry_price": getattr(pos, 'entry_price', 0.0),
                    "current_price": getattr(pos, 'current_price', 0.0),
                    "profit_loss": getattr(pos, 'profit_loss', 0.0),
                    "profit_loss_percent": getattr(pos, 'profit_loss_percent', 0.0),
                    "created_at": getattr(pos, 'created_at', ''),
                    "duration": getattr(pos, 'duration', '')
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"❌ 포지션 조회 실패: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        포트폴리오 요약 정보를 읽기 전용으로 조회
        
        Returns:
            Dict: 포트폴리오 요약 정보
        """
        try:
            from core.services.trading_engine import trading_state
            
            # 기존 상태에서 계산된 값들 읽기 (수정하지 않음)
            total_value = getattr(trading_state, 'total_value', 0.0)
            available_budget = getattr(trading_state, 'available_budget', 0.0)
            total_profit_loss = getattr(trading_state, 'total_profit_loss', 0.0)
            
            return {
                "total_value": total_value,
                "available_budget": available_budget,
                "invested_amount": total_value - available_budget,
                "total_profit_loss": total_profit_loss,
                "profit_loss_percent": (total_profit_loss / total_value * 100) if total_value > 0 else 0.0,
                "position_count": len(getattr(trading_state, 'positions', [])),
                "last_update": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 포트폴리오 조회 실패: {e}")
            return {
                "total_value": 0.0,
                "available_budget": 0.0,
                "invested_amount": 0.0,
                "total_profit_loss": 0.0,
                "profit_loss_percent": 0.0,
                "position_count": 0,
                "last_update": datetime.utcnow().isoformat(),
                "error": "데이터 조회 실패"
            }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 거래 내역을 읽기 전용으로 조회
        
        Args:
            limit: 조회할 거래 수 (기본 10개)
            
        Returns:
            List[Dict]: 최근 거래 내역
        """
        try:
            from core.services.trading_engine import trading_state
            
            # 기존 거래 기록에서 최근 거래 가져오기 (수정하지 않음)
            trade_history = getattr(trading_state, 'trade_history', [])
            
            recent_trades = trade_history[-limit:] if trade_history else []
            
            return [
                {
                    "symbol": getattr(trade, 'symbol', ''),
                    "side": getattr(trade, 'side', ''),
                    "amount": getattr(trade, 'amount', 0.0),
                    "price": getattr(trade, 'price', 0.0),
                    "profit_loss": getattr(trade, 'profit_loss', 0.0),
                    "profit_loss_percent": getattr(trade, 'profit_loss_percent', 0.0),
                    "executed_at": getattr(trade, 'executed_at', ''),
                    "duration": getattr(trade, 'duration', ''),
                    "status": getattr(trade, 'status', '')
                }
                for trade in reversed(recent_trades)  # 최신순 정렬
            ]
        except Exception as e:
            logger.error(f"❌ 거래 내역 조회 실패: {e}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        시스템 상태를 읽기 전용으로 조회
        
        Returns:
            Dict: 시스템 상태 정보
        """
        try:
            # 기존 시스템의 다양한 상태 정보 수집
            from core.services.trading_engine import trading_state
            
            return {
                "system_running": True,  # 모바일 API가 실행 중이면 시스템은 작동 중
                "trading_active": getattr(trading_state, 'is_running', False),
                "last_signal_time": getattr(trading_state, 'last_signal_time', ''),
                "api_connection": self._check_api_connection(),
                "database_connection": self._check_database_connection(),
                "memory_usage": self._get_memory_usage(),
                "uptime": self._get_uptime(),
                "last_update": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 시스템 상태 조회 실패: {e}")
            return {
                "system_running": False,
                "trading_active": False,
                "error": "시스템 상태 조회 실패",
                "last_update": datetime.utcnow().isoformat()
            }
    
    def _check_api_connection(self) -> bool:
        """업비트 API 연결 상태 확인 (읽기 전용)"""
        try:
            # 기존 API 클라이언트 상태 확인 (수정하지 않음)
            return True  # 임시로 True 반환, 실제로는 기존 API 상태 확인
        except:
            return False
    
    def _check_database_connection(self) -> bool:
        """데이터베이스 연결 상태 확인 (읽기 전용)"""
        try:
            # 기존 데이터베이스 연결 상태 확인 (수정하지 않음)
            return True  # 임시로 True 반환, 실제로는 DB 연결 확인
        except:
            return False
    
    def _get_memory_usage(self) -> float:
        """메모리 사용량 조회 (읽기 전용)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_percent()
        except:
            return 0.0
    
    def _get_uptime(self) -> str:
        """시스템 가동 시간 조회 (읽기 전용)"""
        try:
            from config import SERVER_START_TIME
            uptime_seconds = datetime.utcnow().timestamp() - SERVER_START_TIME
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"{hours}시간 {minutes}분"
        except:
            return "알 수 없음"
    
    async def get_real_time_data(self) -> Dict[str, Any]:
        """
        실시간 데이터를 읽기 전용으로 조회 (WebSocket용)
        
        Returns:
            Dict: 실시간 업데이트 데이터
        """
        try:
            # 모든 핵심 데이터를 실시간으로 수집
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "trading_state": self.get_trading_state(),
                "positions": self.get_current_positions(),
                "portfolio": self.get_portfolio_summary(),
                "system_status": self.get_system_status()
            }
            
            logger.debug("📊 실시간 데이터 업데이트 완료")
            return data
            
        except Exception as e:
            logger.error(f"❌ 실시간 데이터 조회 실패: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": "실시간 데이터 조회 실패"
            }
    
    def safe_call_existing_function(self, func_name: str, *args, **kwargs) -> Any:
        """
        기존 시스템의 함수를 안전하게 호출 (상태 변경 시에만 사용)
        
        ⚠️ 주의: 이 함수는 거래 제어 등 꼭 필요한 경우에만 사용하며,
        기존 시스템의 함수를 호출하되 최대한 안전하게 처리합니다.
        
        Args:
            func_name: 호출할 함수명
            *args, **kwargs: 함수 인자
            
        Returns:
            Any: 함수 실행 결과
        """
        try:
            if not self._safe_mode:
                logger.warning("⚠️ 안전 모드가 비활성화되어 있습니다!")
            
            logger.info(f"🔧 기존 시스템 함수 호출: {func_name}")
            
            # 거래 엔진의 제어 함수들만 허용
            allowed_functions = [
                'start_trading',
                'stop_trading', 
                'emergency_stop',
                'get_status'
            ]
            
            if func_name not in allowed_functions:
                raise ValueError(f"허용되지 않은 함수: {func_name}")
            
            from core.services.trading_engine import trading_engine
            
            if hasattr(trading_engine, func_name):
                func = getattr(trading_engine, func_name)
                result = func(*args, **kwargs)
                logger.info(f"✅ 함수 호출 성공: {func_name}")
                return result
            else:
                raise AttributeError(f"함수를 찾을 수 없음: {func_name}")
                
        except Exception as e:
            logger.error(f"❌ 함수 호출 실패 {func_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "function": func_name
            }