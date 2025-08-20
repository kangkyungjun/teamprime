#!/usr/bin/env python3
"""
API 호출 상태 실시간 모니터링 스크립트
노트북을 덮었을 때 API 호출이 실제로 중단되는지 확인
"""

import requests
import time
import json
from datetime import datetime
import sys
import signal

class APIMonitor:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.running = True
        self.last_cycle_number = 0
        self.api_call_count = 0
        self.start_time = time.time()
        
        # SIGINT 핸들러 등록 (Ctrl+C로 종료)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Ctrl+C 시 정상 종료"""
        print("\n\n🛑 모니터링 중지됨")
        self.running = False
        sys.exit(0)
    
    def get_system_status(self):
        """시스템 상태 조회"""
        try:
            response = requests.get(f"{self.base_url}/api/coin-api-status", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            return {"error": str(e)}
    
    def get_real_time_conditions(self):
        """실시간 매수 조건 확인"""
        try:
            response = requests.get(f"{self.base_url}/real-time-buy-conditions", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            return {"error": str(e)}
    
    def check_upbit_api_direct(self):
        """업비트 API 직접 호출로 연결 상태 확인"""
        try:
            response = requests.get("https://api.upbit.com/v1/candles/minutes/1?market=KRW-BTC&count=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "response_time": response.elapsed.total_seconds(),
                    "data_count": len(data) if data else 0
                }
            else:
                return {"status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def print_status(self, system_status, conditions_status, upbit_direct):
        """상태 정보 출력"""
        current_time = datetime.now().strftime("%H:%M:%S")
        elapsed = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print(f"⏰ {current_time} | 경과시간: {elapsed:.0f}초 | API 호출 횟수: {self.api_call_count}")
        print(f"{'='*80}")
        
        # 시스템 상태
        if system_status and "error" not in system_status:
            cycle_info = system_status.get("cycle_info", {})
            cycle_number = cycle_info.get("cycle_number", 0)
            current_phase = cycle_info.get("current_phase", "unknown")
            progress = cycle_info.get("total_progress", 0) * 100
            
            # 사이클 변화 감지
            if cycle_number != self.last_cycle_number:
                print(f"🔄 **새로운 사이클 시작**: #{cycle_number}")
                self.last_cycle_number = cycle_number
            
            print(f"📊 사이클 #{cycle_number} | 상태: {current_phase} | 진행률: {progress:.1f}%")
            
            # 현재 처리 중인 코인
            phase_details = cycle_info.get("phase_details", {})
            current_coin = phase_details.get("current_coin")
            completed_coins = phase_details.get("coins_completed", [])
            remaining_coins = phase_details.get("coins_remaining", [])
            
            if current_coin:
                print(f"🔍 현재 처리: {current_coin}")
            print(f"✅ 완료: {completed_coins}")
            print(f"⏳ 대기: {remaining_coins}")
        else:
            print(f"❌ 시스템 상태 오류: {system_status}")
        
        # 실시간 매수 조건
        if conditions_status and "error" not in conditions_status:
            print(f"\n📈 실시간 매수 조건 (최신 업데이트: {current_time})")
            conditions = conditions_status.get("conditions", [])
            for condition in conditions[:3]:  # 처음 3개만 표시
                market = condition.get("market", "")
                coin = condition.get("coin", "")
                status = condition.get("status", "")
                signal_strength = condition.get("signal_strength", 0)
                current_price = condition.get("current_price", 0)
                
                print(f"  {coin}: {status} | 신호강도: {signal_strength} | 현재가: {current_price:,.0f}")
        else:
            print(f"❌ 매수 조건 조회 오류: {conditions_status}")
        
        # 업비트 API 직접 호출
        print(f"\n🌐 업비트 API 직접 호출:")
        if upbit_direct.get("status") == "success":
            response_time = upbit_direct.get("response_time", 0)
            data_count = upbit_direct.get("data_count", 0)
            print(f"  ✅ 성공 | 응답시간: {response_time:.3f}초 | 데이터: {data_count}개")
        else:
            print(f"  ❌ 실패 | {upbit_direct}")
    
    def run(self):
        """모니터링 실행"""
        print("🚀 API 상태 모니터링 시작")
        print("노트북을 덮기 전에 이 상태를 확인하고, 덮은 후 변화를 관찰하세요")
        print("Ctrl+C로 종료")
        
        while self.running:
            try:
                # API 호출 횟수 증가
                self.api_call_count += 1
                
                # 각종 상태 정보 수집
                system_status = self.get_system_status()
                conditions_status = self.get_real_time_conditions()
                upbit_direct = self.check_upbit_api_direct()
                
                # 상태 출력
                self.print_status(system_status, conditions_status, upbit_direct)
                
                # 30초 대기
                print(f"\n⏳ 30초 대기 중... (다음 체크: {datetime.fromtimestamp(time.time() + 30).strftime('%H:%M:%S')})")
                time.sleep(30)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n❌ 모니터링 오류: {e}")
                time.sleep(10)
        
        print("\n✅ 모니터링 종료")

if __name__ == "__main__":
    monitor = APIMonitor()
    monitor.run()