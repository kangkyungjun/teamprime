# -*- coding: utf-8 -*-
"""
Enhanced MTFA Backtesting Engine - 수익률 보장 백테스팅 시스템
============================================================

개선된 백테스팅 엔진:
1. 실시간 신뢰도 기반 매수 신호
2. 동적 손익비 적용
3. 시장 상황별 적응형 전략
4. 엄격한 수익률 검증
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from math import ceil, sqrt
from tqdm.auto import tqdm
from enhanced_mtfa_strategy import *

# ================= 데이터 로딩 및 전처리 ==============

def load_and_merge_mtfa_data(conn, market):
    """MTFA 분석을 위한 다중 시간대 데이터 로딩 및 병합"""
    
    print(f"📊 {market} MTFA 데이터 로딩 중...")
    
    # 1분, 5분, 15분봉 데이터 로딩
    try:
        df_1m = pd.read_sql(f"""
            SELECT ts, open, high, low, close, volume 
            FROM candles 
            WHERE market='{market}' AND unit=1 
            ORDER BY ts ASC
        """, conn)
        
        df_5m = pd.read_sql(f"""
            SELECT ts, open, high, low, close, volume 
            FROM candles 
            WHERE market='{market}' AND unit=5 
            ORDER BY ts ASC
        """, conn)
        
        df_15m = pd.read_sql(f"""
            SELECT ts, open, high, low, close, volume 
            FROM candles 
            WHERE market='{market}' AND unit=15 
            ORDER BY ts ASC
        """, conn)
        
        if df_1m.empty or df_5m.empty or df_15m.empty:
            print(f"❌ {market} 데이터 부족")
            return pd.DataFrame()
        
        # 시간대별 기술적 지표 계산
        df_1m = add_technical_indicators(df_1m, "1m")
        df_5m = add_technical_indicators(df_5m, "5m") 
        df_15m = add_technical_indicators(df_15m, "15m")
        
        # 시간 정렬 병합 (merge_asof 사용)
        df_1m['ts_dt'] = pd.to_datetime(df_1m['ts'], unit='s')
        df_5m['ts_dt'] = pd.to_datetime(df_5m['ts'], unit='s')
        df_15m['ts_dt'] = pd.to_datetime(df_15m['ts'], unit='s')
        
        # 1분봉 기준으로 5분봉, 15분봉 데이터 병합
        df_merged = pd.merge_asof(
            df_1m.sort_values('ts_dt'), 
            df_5m.sort_values('ts_dt').add_suffix('_5m'),
            left_on='ts_dt', 
            right_on='ts_dt_5m', 
            direction='backward'
        )
        
        df_merged = pd.merge_asof(
            df_merged.sort_values('ts_dt'),
            df_15m.sort_values('ts_dt').add_suffix('_15m'),
            left_on='ts_dt',
            right_on='ts_dt_15m',
            direction='backward'
        )
        
        # 필요한 컬럼만 정리
        df_merged = df_merged.dropna()
        
        print(f"✅ {market} MTFA 데이터 병합 완료: {len(df_merged):,}개 레코드")
        return df_merged
        
    except Exception as e:
        print(f"❌ {market} 데이터 로딩 실패: {e}")
        return pd.DataFrame()

def add_technical_indicators(df, timeframe_suffix):
    """시간대별 기술적 지표 계산"""
    
    df = df.copy()
    
    # EMA (지수이동평균)
    df[f'ema_short_{timeframe_suffix}'] = df['close'].ewm(span=12, adjust=False).mean()
    df[f'ema_long_{timeframe_suffix}'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # RSI (상대강도지수) 
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df[f'rsi_{timeframe_suffix}'] = 100 - (100 / (1 + rs))
    
    # MACD
    macd = df[f'ema_short_{timeframe_suffix}'] - df[f'ema_long_{timeframe_suffix}']
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    df[f'macd_signal_{timeframe_suffix}'] = (macd > macd_signal).astype(int)
    
    # 가격 변화율
    df[f'price_change_{timeframe_suffix}'] = df['close'].pct_change()
    
    # 거래량 이동평균
    df[f'volume_{timeframe_suffix}'] = df['volume']
    
    # 볼린저밴드 포지션 (임시로 단순 계산)
    bb_middle = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df[f'bb_position_{timeframe_suffix}'] = (df['close'] - bb_middle) / (bb_std * 2)
    
    return df

# ================= 향상된 백테스팅 엔진 ==============

def simulate_enhanced_mtfa_trades(df_merged, market_regime="sideways"):
    """향상된 MTFA 백테스팅 시뮬레이션"""
    
    if df_merged.empty or len(df_merged) < 100:
        return pd.DataFrame(), {"error": "데이터 부족"}
    
    print(f"🔄 시뮬레이션 시작 - 시장상황: {market_regime}")
    
    # 신호 생성
    signals = ultra_high_confidence_mtfa_signal(df_merged, market_regime)
    signal_indices = np.where(signals)[0]
    
    if len(signal_indices) == 0:
        return pd.DataFrame(), {"error": "신호 없음"}
    
    print(f"🎯 생성된 신호: {len(signal_indices)}개")
    
    trades = []
    regime_config = MARKET_REGIME_CONFIG[market_regime]
    max_daily_trades = regime_config["max_daily_trades"]
    
    # 일별 거래 제한 추적
    daily_trade_count = {}
    daily_pnl = {}
    
    for signal_idx in signal_indices:
        
        # 신뢰도 계산
        confidence = calculate_signal_confidence(df_merged, signal_idx)
        
        # 동적 손익비 결정
        risk_reward = get_dynamic_risk_reward(confidence, market_regime)
        if risk_reward is None:
            continue  # 신뢰도 부족으로 거래 건너뛰기
        
        # 날짜별 거래 제한 체크
        entry_date = pd.to_datetime(df_merged.iloc[signal_idx]['ts'], unit='s').date()
        daily_count = daily_trade_count.get(entry_date, 0)
        daily_loss = daily_pnl.get(entry_date, 0.0)
        
        # 일일 제한 체크
        if daily_count >= max_daily_trades:
            continue
        if daily_loss <= DAILY_LOSS_CUT_PCT:
            continue
            
        # 거래 실행
        entry_price = df_merged.iloc[signal_idx]['close']
        entry_ts = df_merged.iloc[signal_idx]['ts']
        
        # 이후 봉들에서 익절/손절 체크
        exit_result = find_exit_point(df_merged, signal_idx, entry_price, risk_reward)
        
        if exit_result:
            trade_return = exit_result['return']
            
            trades.append({
                'entry_ts': entry_ts,
                'exit_ts': exit_result['exit_ts'],
                'entry_price': entry_price,
                'exit_price': exit_result['exit_price'],
                'return': trade_return,
                'confidence': confidence,
                'hold_minutes': exit_result['hold_minutes'],
                'exit_reason': exit_result['reason']
            })
            
            # 일별 카운트 및 PnL 업데이트
            daily_trade_count[entry_date] = daily_count + 1
            daily_pnl[entry_date] = daily_loss + trade_return
    
    trades_df = pd.DataFrame(trades)
    
    if trades_df.empty:
        return pd.DataFrame(), {"error": "실행된 거래 없음"}
    
    # 성과 지표 계산
    performance = calculate_enhanced_performance_metrics(trades_df)
    
    return trades_df, performance

def find_exit_point(df_merged, entry_idx, entry_price, risk_reward):
    """개선된 출구점 찾기 (실제 거래비용 반영)"""
    
    tp_target = entry_price * (1 + risk_reward['take_profit'])
    sl_target = entry_price * (1 + risk_reward['stop_loss'])
    
    # 실제 거래비용 반영
    tp_price_after_cost = tp_target * A_OUT / A_IN  # 거래비용 차감 후 실제 받을 금액
    sl_price_after_cost = sl_target * A_OUT / A_IN
    
    max_hold_bars = min(60, len(df_merged) - entry_idx - 1)  # 최대 60분 보유
    
    for i in range(1, max_hold_bars + 1):
        if entry_idx + i >= len(df_merged):
            break
            
        current_bar = df_merged.iloc[entry_idx + i]
        high = current_bar['high']
        low = current_bar['low'] 
        close = current_bar['close']
        
        # 익절 체크
        if high >= tp_target:
            return {
                'exit_ts': current_bar['ts'],
                'exit_price': tp_target,
                'return': (tp_price_after_cost / entry_price) - 1.0,
                'hold_minutes': i,
                'reason': 'TP'
            }
        
        # 손절 체크  
        if low <= sl_target:
            return {
                'exit_ts': current_bar['ts'],
                'exit_price': sl_target,
                'return': (sl_price_after_cost / entry_price) - 1.0,
                'hold_minutes': i,
                'reason': 'SL'
            }
    
    # 시간 만료로 종료
    final_bar = df_merged.iloc[entry_idx + max_hold_bars]
    final_price_after_cost = final_bar['close'] * A_OUT / A_IN
    
    return {
        'exit_ts': final_bar['ts'],
        'exit_price': final_bar['close'],
        'return': (final_price_after_cost / entry_price) - 1.0,
        'hold_minutes': max_hold_bars,
        'reason': 'TTL'
    }

def calculate_enhanced_performance_metrics(trades_df):
    """향상된 성과 지표 계산"""
    
    if trades_df.empty:
        return {"total_return": 0, "win_rate": 0, "trades": 0, "max_drawdown": 0}
    
    returns = trades_df['return'].values
    
    # 기본 지표
    total_return = np.expm1(np.log1p(returns).sum())  # 복리 수익률
    win_rate = np.mean(returns > 0)
    total_trades = len(returns)
    avg_return = np.mean(returns)
    
    # 누적 수익률 곡선으로 MDD 계산
    cumulative_returns = INITIAL_CAPITAL * np.exp(np.log1p(returns).cumsum())
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - running_max) / running_max
    max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
    
    # 샤프 비율 계산
    if np.std(returns) > 0:
        sharpe_ratio = np.sqrt(252) * np.mean(returns) / np.std(returns)  # 연율화
    else:
        sharpe_ratio = 0
    
    # Profit Factor 계산
    gross_profit = np.sum(returns[returns > 0]) if np.any(returns > 0) else 0
    gross_loss = abs(np.sum(returns[returns < 0])) if np.any(returns < 0) else 0.001  # 0으로 나누기 방지
    profit_factor = gross_profit / gross_loss
    
    # 최종 자본
    final_capital = INITIAL_CAPITAL * (1 + total_return)
    
    return {
        "total_return": total_return,
        "win_rate": win_rate, 
        "trades": total_trades,
        "avg_return": avg_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "profit_factor": profit_factor,
        "final_capital": final_capital,
        "avg_confidence": trades_df['confidence'].mean(),
        "avg_hold_minutes": trades_df['hold_minutes'].mean()
    }

# ================= 최적화 시스템 ==============

def optimize_enhanced_mtfa_for_market(conn, market):
    """시장별 향상된 MTFA 전략 최적화"""
    
    print(f"\n🚀 {market} 최적화 시작")
    
    # 데이터 로딩
    df_merged = load_and_merge_mtfa_data(conn, market)
    
    if df_merged.empty:
        return {"market": market, "status": "데이터 부족", "score": -999999}
    
    best_result = None
    best_score = -999999
    
    # 시장 상황별 테스트
    for regime in ["bull_strong", "bull_weak", "sideways", "bear"]:
        
        print(f"  📊 {regime} 모드 테스트 중...")
        
        try:
            trades_df, performance = simulate_enhanced_mtfa_trades(df_merged, regime)
            
            if performance.get("error"):
                print(f"    ❌ {regime}: {performance['error']}")
                continue
            
            # 수익률 보장 검증
            score = ultimate_profitability_score(performance)
            
            print(f"    📈 {regime}: 수익률 {performance['total_return']:.1%}, "
                  f"승률 {performance['win_rate']:.1%}, "
                  f"거래 {performance['trades']}회, "
                  f"점수 {score:.0f}")
            
            if score > best_score:
                best_score = score
                best_result = {
                    "market": market,
                    "regime": regime,
                    "performance": performance,
                    "trades_df": trades_df,
                    "score": score,
                    "status": "OK"
                }
                
        except Exception as e:
            print(f"    ❌ {regime} 테스트 실패: {e}")
            continue
    
    if best_result is None:
        return {"market": market, "status": "모든 전략 실패", "score": -999999}
    
    print(f"✅ {market} 최적화 완료 - 최고 전략: {best_result['regime']}")
    return best_result

print("🔧 Enhanced MTFA Backtesting Engine 로딩 완료")
print("💡 특징: 실시간 신뢰도 기반 매수 + 동적 손익비 + 엄격한 수익률 검증")