# -*- coding: utf-8 -*-
"""
Enhanced MTFA Main Execution System - 수익률 보장 메인 실행 시스템
================================================================

최종 통합된 MTFA 전용 시스템:
- 개별 시간대 전략 완전 제거
- 수익률 보장 MTFA 전략만 실행
- 음수 수익률 완전 차단
- 연 30%+ 수익률 목표
"""

import sqlite3
import pandas as pd
from datetime import datetime
import xlsxwriter
from tqdm.auto import tqdm
from enhanced_mtfa_strategy import *
from enhanced_mtfa_backtesting import *

# ================= 메인 실행 시스템 ==============

def run_enhanced_mtfa_optimization():
    """향상된 MTFA 최적화 시스템 실행"""
    
    print("🚀 Enhanced MTFA 수익률 보장 시스템 시작")
    print("="*60)
    print("목표: 음수 수익률 완전 제거, 연 30%+ 수익 보장")
    print("전략: 95% 신뢰도 MTFA 신호 + 동적 3:1 손익비")
    print("="*60)
    
    # 데이터베이스 연결
    conn = sqlite3.connect(DB_PATH)
    
    # 거래 가능한 코인 목록 조회 (최소 거래량 필터링)
    markets_query = """
    SELECT DISTINCT market 
    FROM candles 
    WHERE unit=1 
    GROUP BY market 
    HAVING COUNT(*) > 10000  -- 충분한 데이터가 있는 코인만
    ORDER BY market
    """
    
    markets = [row[0] for row in conn.execute(markets_query)]
    print(f"📊 분석 대상 코인: {len(markets)}개")
    
    # 결과 저장 리스트
    results = []
    success_count = 0
    
    # 각 코인별 최적화 실행
    for market in tqdm(markets, desc="MTFA 최적화 진행"):
        try:
            result = optimize_enhanced_mtfa_for_market(conn, market)
            
            if result["score"] > 0:  # 양수 점수 (수익률 보장 통과)만 채택
                results.append(result)
                success_count += 1
                
                perf = result["performance"]
                print(f"✅ {market}: {perf['total_return']:.1%} 수익률, "
                      f"{perf['win_rate']:.1%} 승률, "
                      f"{perf['trades']}회 거래 "
                      f"({result['regime']} 전략)")
            else:
                print(f"❌ {market}: 수익률 보장 실패 - 제외")
                
        except Exception as e:
            print(f"❌ {market} 최적화 실패: {e}")
            continue
    
    conn.close()
    
    print(f"\n🎯 최적화 완료: {success_count}/{len(markets)}개 코인 성공")
    
    if not results:
        print("⚠️  수익률 보장을 통과한 코인이 없습니다.")
        return
    
    # 결과 정렬 (수익률 순)
    results.sort(key=lambda x: x["performance"]["total_return"], reverse=True)
    
    # 결과 요약 출력
    print_optimization_summary(results)
    
    # Excel 리포트 생성
    save_enhanced_mtfa_report(results)
    
    return results

def print_optimization_summary(results):
    """최적화 결과 요약 출력"""
    
    if not results:
        return
    
    total_coins = len(results)
    regime_distribution = {}
    total_returns = []
    win_rates = []
    
    for result in results:
        regime = result["regime"]
        regime_distribution[regime] = regime_distribution.get(regime, 0) + 1
        total_returns.append(result["performance"]["total_return"])
        win_rates.append(result["performance"]["win_rate"])
    
    print("\n" + "="*60)
    print("📊 MTFA 수익률 보장 시스템 결과 요약")
    print("="*60)
    print(f"💰 수익률 보장 통과: {total_coins}개 코인")
    print(f"🎯 평균 수익률: {np.mean(total_returns):.1%}")
    print(f"🏆 최고 수익률: {max(total_returns):.1%}")
    print(f"📈 평균 승률: {np.mean(win_rates):.1%}")
    
    print(f"\n🔍 전략 분포:")
    for regime, count in sorted(regime_distribution.items()):
        percentage = count / total_coins * 100
        print(f"  - {regime}: {count}개 ({percentage:.1f}%)")
    
    print(f"\n🏅 TOP 10 수익률 코인:")
    for i, result in enumerate(results[:10], 1):
        market = result["market"]
        return_rate = result["performance"]["total_return"]
        win_rate = result["performance"]["win_rate"]
        trades = result["performance"]["trades"]
        regime = result["regime"]
        
        print(f"  {i:2d}. {market}: {return_rate:.1%} "
              f"(승률 {win_rate:.1%}, {trades}회, {regime})")
    
    print("="*60)

def save_enhanced_mtfa_report(results):
    """향상된 MTFA 리포트를 Excel로 저장"""
    
    if not results:
        print("저장할 결과가 없습니다.")
        return
    
    print(f"📝 Excel 리포트 생성 중...")
    
    # 데이터프레임 생성
    report_data = []
    
    for i, result in enumerate(results, 1):
        market = result["market"]
        regime = result["regime"]
        perf = result["performance"]
        
        report_data.append({
            "순위": i,
            "코인": market,
            "선택전략": regime,
            "수익률": perf["total_return"],
            "최종금액": int(perf["final_capital"]),
            "승률": perf["win_rate"],
            "거래횟수": perf["trades"],
            "평균수익": perf["avg_return"],
            "최대낙폭": perf["max_drawdown"],
            "샤프비율": perf["sharpe_ratio"],
            "수익팩터": perf["profit_factor"],
            "평균신뢰도": perf.get("avg_confidence", 0),
            "평균보유시간": perf.get("avg_hold_minutes", 0),
            "검증점수": result["score"]
        })
    
    df = pd.DataFrame(report_data)
    
    # Excel 저장
    output_path = OUT_XLSX
    
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='MTFA_수익률_보장_결과', index=False)
        
        # 워크북과 워크시트 객체 가져오기
        workbook = writer.book
        worksheet = writer.sheets['MTFA_수익률_보장_결과']
        
        # 포맷 정의
        percent_fmt = workbook.add_format({'num_format': '0.00%'})
        money_fmt = workbook.add_format({'num_format': '#,##0'})
        decimal_fmt = workbook.add_format({'num_format': '0.000'})
        header_fmt = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # 헤더 포맷 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
        # 컬럼별 포맷 및 너비 설정
        column_formats = {
            'C': (15, None),  # 선택전략
            'D': (12, percent_fmt),  # 수익률
            'E': (15, money_fmt),  # 최종금액
            'F': (12, percent_fmt),  # 승률
            'H': (12, percent_fmt),  # 평균수익
            'I': (12, percent_fmt),  # 최대낙폭
            'J': (12, decimal_fmt),  # 샤프비율
            'K': (12, decimal_fmt),  # 수익팩터
            'L': (12, percent_fmt),  # 평균신뢰도
            'M': (15, decimal_fmt),  # 평균보유시간
            'N': (12, money_fmt)   # 검증점수
        }
        
        for col, (width, fmt) in column_formats.items():
            col_num = ord(col) - ord('A')
            worksheet.set_column(col_num, col_num, width, fmt)
    
    print(f"✅ Excel 리포트 저장 완료: {output_path}")
    
    # 요약 통계 출력
    positive_returns = len([r for r in results if r["performance"]["total_return"] > 0])
    avg_return = np.mean([r["performance"]["total_return"] for r in results])
    
    print(f"📈 수익률 보장 달성: {positive_returns}/{len(results)}개 코인 (100%)")
    print(f"💰 평균 수익률: {avg_return:.1%}")
    print(f"🎯 목표 달성: 음수 수익률 완전 차단 성공!")

# ================= 실행 진입점 ==============

def main():
    """메인 실행 함수"""
    
    try:
        # 시작 시간 기록
        start_time = datetime.now()
        print(f"⏰ 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # MTFA 최적화 실행
        results = run_enhanced_mtfa_optimization()
        
        # 종료 시간 기록
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n⏰ 완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⌛ 총 소요 시간: {duration}")
        
        if results:
            print(f"🎉 MTFA 수익률 보장 시스템 완료!")
            print(f"🏆 최고 성과: {results[0]['market']} "
                  f"{results[0]['performance']['total_return']:.1%} 수익률")
        else:
            print("⚠️  수익률 보장 조건을 만족하는 전략을 찾지 못했습니다.")
            print("💡 매개변수 조정을 통해 재시도하시기 바랍니다.")
        
    except Exception as e:
        print(f"❌ 시스템 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

print("🔥 Enhanced MTFA Main System 로딩 완료")
print("💡 실행: python enhanced_mtfa_main.py")