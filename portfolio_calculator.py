#!/usr/bin/env python3
"""
포트폴리오 수익률 계산기 - 최적화된 신호 기반
"""

def calculate_portfolio_performance():
    """실제 백테스팅 데이터를 기반으로 포트폴리오 성과 계산"""
    
    # 백테스팅 결과 기반 통계
    total_trades = 200
    winning_trades = int(200 * 0.567)  # 56.7% 승률
    losing_trades = total_trades - winning_trades
    
    # 수익/손실 분포 (실제 거래 데이터 기반)
    avg_win = 0.8  # 평균 승리 시 수익률 (%)
    avg_loss = -0.6  # 평균 손실 시 손실률 (%)
    
    # 누적 수익률 계산
    initial_capital = 100000  # 10만원
    current_capital = initial_capital
    
    print("🚀 3년간 거래 시뮬레이션 (최적화된 신호)")
    print("=" * 50)
    print(f"초기 자본: {initial_capital:,}원")
    print(f"총 거래 횟수: {total_trades}회")
    print(f"승리 거래: {winning_trades}회 (56.7%)")
    print(f"패배 거래: {losing_trades}회 (43.3%)")
    print()
    
    # 거래별 수익률 적용
    for i in range(total_trades):
        if i < winning_trades:
            # 승리 거래
            profit_rate = avg_win / 100
            current_capital *= (1 + profit_rate)
        else:
            # 패배 거래
            loss_rate = avg_loss / 100
            current_capital *= (1 + loss_rate)
    
    total_return = ((current_capital - initial_capital) / initial_capital) * 100
    
    print(f"📊 최종 결과")
    print("-" * 30)
    print(f"최종 자본: {current_capital:,.0f}원")
    print(f"총 수익률: {total_return:+.1f}%")
    print(f"순이익: {current_capital - initial_capital:+,.0f}원")
    print()
    
    # 연간 수익률 계산
    years = 3
    annual_return = ((current_capital / initial_capital) ** (1/years) - 1) * 100
    print(f"연평균 수익률: {annual_return:.1f}%")
    
    # 월간 거래 빈도
    monthly_trades = total_trades / (years * 12)
    print(f"월평균 거래: {monthly_trades:.1f}회")
    print()
    
    # 시나리오 분석
    print("📈 시나리오 분석")
    print("-" * 30)
    
    scenarios = [
        ("보수적 (승률 50%)", 0.50, 0.6, -0.5, 200),
        ("검증된 기존 조건", 0.567, 0.8, -0.6, 200),  # 56.7% 승률 (백테스팅 검증)
        ("⚠️ 완화 조건 (위험)", 0.520, 0.7, -0.65, 280),  # 거래 40% 증가, 승률 4.7%p 하락
        ("완화 조건 (낙관적)", 0.550, 0.75, -0.6, 280),  # 승률 소폭 하락만
        ("완화 조건 (비관적)", 0.480, 0.65, -0.7, 280),   # 승률 대폭 하락
        ("낙관적 (승률 65%)", 0.65, 1.0, -0.5, 200),
    ]
    
    for name, win_rate, win_avg, loss_avg, scenario_trades in scenarios:
        wins = int(scenario_trades * win_rate)
        losses = scenario_trades - wins
        
        capital = initial_capital
        for _ in range(wins):
            capital *= (1 + win_avg/100)
        for _ in range(losses):
            capital *= (1 + loss_avg/100)
        
        scenario_return = ((capital - initial_capital) / initial_capital) * 100
        annual_return = ((capital / initial_capital) ** (1/3) - 1) * 100
        monthly_trades = scenario_trades / (3 * 12)
        
        risk_indicator = "🔴" if win_rate < 0.52 else "🟡" if win_rate < 0.55 else "🟢"
        print(f"{risk_indicator} {name}:")
        print(f"   총거래: {scenario_trades}회, 승률: {win_rate*100:.1f}%, 월거래: {monthly_trades:.1f}회")
        print(f"   최종자본: {capital:,.0f}원 ({scenario_return:+.1f}%), 연수익률: {annual_return:+.1f}%")
        print()
    
    print()
    print("🚨 조건 완화 위험성 분석")
    print("-" * 40)
    print("• 거래 40% 증가 시 승률 4.7%p 하락만으로도 수익률 급감")
    print("• 승률 56.7% → 52% 하락 시: 연수익률 대폭 감소")  
    print("• 승률 56.7% → 48% 하락 시: 원금 손실 위험")
    print()
    print("💡 핵심 통찰")
    print("-" * 30)
    print("🔥 승률이 수익률에 미치는 영향은 기하급수적")
    print("📊 검증된 56.7% 승률 조건 유지가 최우선")
    print("⚠️ 거래빈도 증가 < 승률 보호")
    print("✅ 데이터 검증 없는 조건 변경 금지")
    print("🎯 수익률 = 승률^거래수 (복리 효과)")

if __name__ == "__main__":
    calculate_portfolio_performance()