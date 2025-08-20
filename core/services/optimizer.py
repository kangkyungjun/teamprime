"""최적화 관련 서비스"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

logger = logging.getLogger(__name__)

class WeeklyOptimizer:
    """수익률 최우선 주간 자동 최적화 엔진"""
    
    def __init__(self):
        self.analysis_running = False
        self.last_analysis_date = 0
        self.version_counter = {"BTC": 1, "XRP": 1, "ETH": 1, "DOGE": 1, "BTT": 1}
        
    async def log_optimization(self, coin: str, operation: str, old_params: dict = None, 
                              new_params: dict = None, test_result: str = None, 
                              action_taken: str = None, log_level: str = "INFO"):
        """최적화 로그 기록"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {
                "timestamp": timestamp,
                "coin": coin,
                "operation": operation,
                "old_params": old_params,
                "new_params": new_params,
                "test_result": test_result,
                "action_taken": action_taken,
                "log_level": log_level
            }
            
            if log_level == "ERROR":
                logger.error(f"[최적화] {coin} {operation}: {action_taken}")
            elif log_level == "WARNING":
                logger.warning(f"[최적화] {coin} {operation}: {action_taken}")
            else:
                logger.info(f"[최적화] {coin} {operation}: {action_taken}")
                
        except Exception as e:
            logger.error(f"최적화 로그 기록 실패: {str(e)}")
    
    async def run_weekly_analysis(self) -> Dict:
        """주간 최적화 분석 실행"""
        if self.analysis_running:
            return {"success": False, "error": "이미 분석이 실행 중입니다"}
        
        self.analysis_running = True
        start_time = time.time()
        
        try:
            result = {
                "success": True,
                "coins_optimized": 0,
                "total_return": 0.0,
                "execution_time": 0.0,
                "optimization_results": {}
            }
            
            # 실제 최적화 로직은 구현 예정 - 현재는 스텁
            await asyncio.sleep(1)  # 시뮬레이션
            
            result["execution_time"] = time.time() - start_time
            return result
            
        except Exception as e:
            logger.error(f"주간 최적화 분석 오류: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            self.analysis_running = False


class AutoOptimizationScheduler:
    """자동 최적화 스케줄러 - 매주 일요일 분석 실행"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone='Asia/Seoul')
        self.is_running = False
        self.weekly_optimizer = WeeklyOptimizer()
        
    async def weekly_optimization_job(self):
        """주간 최적화 작업 (매주 일요일 실행)"""
        try:
            logger.info("🕐 [스케줄러] 주간 자동 최적화 시작...")
            result = await self.weekly_optimizer.run_weekly_analysis()
            
            if result["success"]:
                optimized_coins = result.get("coins_optimized", 0)
                total_return = result.get("total_return", 0.0)
                execution_time = result.get("execution_time", 0.0)
                
                logger.info(f"✅ [스케줄러] 주간 최적화 완료!")
                logger.info(f"📊 분석 결과: {optimized_coins}개 코인 최적화, 수익: {total_return:+,.0f}원")
                logger.info(f"⏱️ 실행 시간: {execution_time:.1f}초")
                
            else:
                error = result.get("error", "알 수 없는 오류")
                logger.error(f"❌ [스케줄러] 주간 최적화 실패: {error}")
                
        except Exception as e:
            logger.error(f"🚨 [스케줄러] 예외 발생: {str(e)}")
            await self.weekly_optimizer.log_optimization("SCHEDULER", "job_error", 
                                                        test_result=str(e), 
                                                        action_taken="스케줄러 작업 실패", 
                                                        log_level="ERROR")
    
    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("⚠️ [스케줄러] 이미 실행 중입니다")
            return
            
        try:
            # 매주 일요일 오전 2시에 자동 최적화 실행
            self.scheduler.add_job(
                self.weekly_optimization_job,
                trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # 일요일 (6) 02:00
                id='weekly_optimization',
                name='주간 자동 최적화',
                replace_existing=True
            )
            
            # 스케줄러 시작
            self.scheduler.start()
            self.is_running = True
            
            logger.info("🕐 [스케줄러] 자동 최적화 스케줄러 시작")
            logger.info("📅 매주 일요일 오전 2시에 자동 최적화 실행")
            
            # 프로그램 종료 시 스케줄러 정리
            atexit.register(self.shutdown)
            
        except Exception as e:
            logger.error(f"❌ [스케줄러] 시작 실패: {str(e)}")
    
    def shutdown(self):
        """스케줄러 종료"""
        if self.is_running:
            try:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("🛑 [스케줄러] 자동 최적화 스케줄러 종료")
            except Exception as e:
                logger.error(f"⚠️ [스케줄러] 종료 중 오류: {str(e)}")
    
    def get_next_run_time(self) -> str:
        """다음 실행 시간 조회"""
        if not self.is_running:
            return "스케줄러 중지됨"
            
        try:
            job = self.scheduler.get_job('weekly_optimization')
            if job and job.next_run_time:
                return job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            return "예정된 실행 없음"
        except Exception:
            return "시간 조회 실패"
    
    async def run_manual_optimization(self) -> dict:
        """수동 최적화 실행"""
        try:
            logger.info("🔧 [수동 실행] 주간 최적화 시작...")
            result = await self.weekly_optimizer.run_weekly_analysis()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}


# 글로벌 인스턴스들
weekly_optimizer = WeeklyOptimizer()
auto_scheduler = AutoOptimizationScheduler()