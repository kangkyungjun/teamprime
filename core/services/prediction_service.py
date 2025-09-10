"""
수익 예측 및 트렌드 분석 서비스
- 선형 회귀 기반 수익 예측
- 계절성 분석 및 트렌드 탐지
- 리스크 분석 및 신뢰구간 계산
- 비즈니스 인사이트 제공
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """예측 결과 데이터 클래스"""
    date: str
    predicted_income: float
    predicted_expense: float
    predicted_profit: float
    confidence_lower: float
    confidence_upper: float
    trend_strength: float

@dataclass 
class TrendAnalysis:
    """트렌드 분석 결과"""
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-100
    seasonality_detected: bool
    seasonal_pattern: Dict[str, float]
    volatility: float
    growth_rate: float

class SimplePredictionService:
    """간단한 예측 서비스 (sklearn 없이 구현)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def predict_revenue_trends(
        self, 
        historical_data: List[Dict], 
        periods_ahead: int = 6
    ) -> Tuple[List[PredictionResult], TrendAnalysis]:
        """
        수익 트렌드 예측
        
        Args:
            historical_data: 과거 데이터 [{month, income, expense, profit}, ...]
            periods_ahead: 예측할 미래 기간 수 (개월)
            
        Returns:
            예측 결과와 트렌드 분석
        """
        
        if len(historical_data) < 3:
            raise ValueError("예측을 위해서는 최소 3개월의 데이터가 필요합니다")
        
        # 데이터 전처리
        processed_data = self._preprocess_data(historical_data)
        
        # 트렌드 분석
        trend_analysis = self._analyze_trends(processed_data)
        
        # 예측 수행
        predictions = self._generate_predictions(processed_data, periods_ahead, trend_analysis)
        
        return predictions, trend_analysis
    
    def _preprocess_data(self, data: List[Dict]) -> Dict:
        """데이터 전처리"""
        
        # 날짜순 정렬
        sorted_data = sorted(data, key=lambda x: x['month'])
        
        months = [item['month'] for item in sorted_data]
        incomes = [float(item.get('income', item.get('revenue', 0))) for item in sorted_data]
        expenses = [float(item.get('expense', 0)) for item in sorted_data]
        profits = [float(item.get('profit', income - expense)) 
                  for item, income, expense in zip(sorted_data, incomes, expenses)]
        
        return {
            'months': months,
            'incomes': incomes,
            'expenses': expenses,
            'profits': profits,
            'n_points': len(months)
        }
    
    def _analyze_trends(self, data: Dict) -> TrendAnalysis:
        """트렌드 분석"""
        
        profits = data['profits']
        n_points = data['n_points']
        
        if n_points < 2:
            return TrendAnalysis(
                trend_direction="stable",
                trend_strength=0,
                seasonality_detected=False,
                seasonal_pattern={},
                volatility=0,
                growth_rate=0
            )
        
        # 선형 트렌드 계산 (최소제곱법)
        x = list(range(n_points))
        y = profits
        
        slope, intercept = self._linear_regression(x, y)
        
        # 트렌드 방향 결정
        trend_direction = "stable"
        if abs(slope) > 0.1:  # 임계값
            trend_direction = "increasing" if slope > 0 else "decreasing"
        
        # 트렌드 강도 (R-squared 기반)
        r_squared = self._calculate_r_squared(x, y, slope, intercept)
        trend_strength = min(100, r_squared * 100)
        
        # 변동성 계산 (표준편차 / 평균)
        mean_profit = np.mean(profits) if profits else 0
        volatility = (np.std(profits) / abs(mean_profit) * 100) if mean_profit != 0 else 0
        
        # 성장률 계산 (첫 번째와 마지막 값 비교)
        if len(profits) >= 2 and profits[0] != 0:
            growth_rate = ((profits[-1] - profits[0]) / abs(profits[0])) * 100
        else:
            growth_rate = 0
        
        # 계절성 탐지 (간단한 방법)
        seasonality_detected, seasonal_pattern = self._detect_seasonality(data)
        
        return TrendAnalysis(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            seasonality_detected=seasonality_detected,
            seasonal_pattern=seasonal_pattern,
            volatility=volatility,
            growth_rate=growth_rate
        )
    
    def _generate_predictions(
        self, 
        data: Dict, 
        periods_ahead: int,
        trend_analysis: TrendAnalysis
    ) -> List[PredictionResult]:
        """예측 생성"""
        
        predictions = []
        
        # 현재 트렌드 기반 예측
        incomes = data['incomes']
        expenses = data['expenses'] 
        profits = data['profits']
        n_points = data['n_points']
        
        # 선형 회귀로 트렌드 추출
        x_income = list(range(n_points))
        x_expense = list(range(n_points))
        x_profit = list(range(n_points))
        
        income_slope, income_intercept = self._linear_regression(x_income, incomes)
        expense_slope, expense_intercept = self._linear_regression(x_expense, expenses)
        profit_slope, profit_intercept = self._linear_regression(x_profit, profits)
        
        # 마지막 월 구하기
        last_month = datetime.strptime(data['months'][-1], '%Y-%m')
        
        # 예측 생성
        for i in range(1, periods_ahead + 1):
            future_month = last_month + timedelta(days=32 * i)
            future_month_str = future_month.strftime('%Y-%m')
            
            future_x = n_points + i - 1
            
            # 기본 예측값
            pred_income = income_slope * future_x + income_intercept
            pred_expense = expense_slope * future_x + expense_intercept
            pred_profit = profit_slope * future_x + profit_intercept
            
            # 계절성 보정
            if trend_analysis.seasonality_detected:
                seasonal_factor = self._get_seasonal_factor(
                    future_month.month, trend_analysis.seasonal_pattern
                )
                pred_income *= seasonal_factor
                pred_expense *= seasonal_factor
                pred_profit = pred_income - pred_expense
            
            # 신뢰구간 계산 (변동성 기반)
            volatility_factor = trend_analysis.volatility / 100
            confidence_range = pred_profit * volatility_factor * 1.96  # 95% 신뢰구간
            
            predictions.append(PredictionResult(
                date=future_month_str,
                predicted_income=max(0, pred_income),
                predicted_expense=max(0, pred_expense),
                predicted_profit=pred_profit,
                confidence_lower=pred_profit - confidence_range,
                confidence_upper=pred_profit + confidence_range,
                trend_strength=trend_analysis.trend_strength
            ))
        
        return predictions
    
    def _linear_regression(self, x: List[float], y: List[float]) -> Tuple[float, float]:
        """단순 선형 회귀"""
        n = len(x)
        if n == 0:
            return 0, 0
            
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x_squared = sum(xi * xi for xi in x)
        
        # 기울기 계산
        denominator = n * sum_x_squared - sum_x * sum_x
        if denominator == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # y절편 계산
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    def _calculate_r_squared(self, x: List[float], y: List[float], slope: float, intercept: float) -> float:
        """R-squared 계산"""
        if not y:
            return 0
            
        y_mean = sum(y) / len(y)
        
        # 총 제곱합
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        
        # 잔차 제곱합
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
        
        # R-squared
        if ss_tot == 0:
            return 1 if ss_res == 0 else 0
        else:
            return 1 - (ss_res / ss_tot)
    
    def _detect_seasonality(self, data: Dict) -> Tuple[bool, Dict[str, float]]:
        """계절성 탐지"""
        
        months = data['months']
        profits = data['profits']
        
        if len(months) < 12:  # 1년 미만의 데이터
            return False, {}
        
        # 월별 평균 계산
        monthly_data = {}
        for month_str, profit in zip(months, profits):
            month_num = int(month_str.split('-')[1])
            if month_num not in monthly_data:
                monthly_data[month_num] = []
            monthly_data[month_num].append(profit)
        
        # 월별 평균 계산
        monthly_averages = {}
        for month, values in monthly_data.items():
            monthly_averages[month] = sum(values) / len(values)
        
        # 계절성 판정 (월별 평균의 변동성이 임계값 초과)
        if len(monthly_averages) >= 6:
            avg_values = list(monthly_averages.values())
            overall_avg = sum(avg_values) / len(avg_values)
            
            # 변동계수 계산
            if overall_avg != 0:
                coefficient_of_variation = (np.std(avg_values) / abs(overall_avg)) * 100
                seasonality_detected = coefficient_of_variation > 20  # 20% 이상 변동
            else:
                seasonality_detected = False
            
            # 계절 패턴을 비율로 변환
            seasonal_pattern = {}
            if seasonality_detected and overall_avg != 0:
                for month, avg in monthly_averages.items():
                    seasonal_pattern[str(month)] = avg / overall_avg
        else:
            seasonality_detected = False
            seasonal_pattern = {}
        
        return seasonality_detected, seasonal_pattern
    
    def _get_seasonal_factor(self, month: int, seasonal_pattern: Dict[str, float]) -> float:
        """계절 보정 팩터 가져오기"""
        return seasonal_pattern.get(str(month), 1.0)
    
    def generate_business_insights(
        self, 
        predictions: List[PredictionResult],
        trend_analysis: TrendAnalysis,
        current_data: Dict
    ) -> List[str]:
        """비즈니스 인사이트 생성"""
        
        insights = []
        
        # 트렌드 기반 인사이트
        if trend_analysis.trend_direction == "increasing":
            if trend_analysis.trend_strength > 70:
                insights.append("🚀 강력한 성장 트렌드가 감지되었습니다! 현재 전략을 유지하고 확장을 고려하세요.")
            else:
                insights.append("📈 완만한 성장세를 보이고 있습니다. 성장 가속화 전략을 검토해보세요.")
        elif trend_analysis.trend_direction == "decreasing":
            if trend_analysis.trend_strength > 70:
                insights.append("🚨 수익 감소 트렌드가 뚜렷합니다. 즉시 개선 전략이 필요합니다.")
            else:
                insights.append("⚠️ 수익이 소폭 감소하고 있습니다. 원인 분석과 대응책 마련이 필요합니다.")
        else:
            insights.append("📊 수익이 안정적으로 유지되고 있습니다. 새로운 성장 동력 발굴을 고려하세요.")
        
        # 변동성 기반 인사이트
        if trend_analysis.volatility > 50:
            insights.append("⚡ 수익 변동성이 높습니다. 리스크 관리와 안정성 확보가 중요합니다.")
        elif trend_analysis.volatility < 20:
            insights.append("🛡️ 수익이 안정적입니다. 예측 가능한 비즈니스 환경을 구축했습니다.")
        
        # 계절성 기반 인사이트
        if trend_analysis.seasonality_detected:
            peak_month = max(trend_analysis.seasonal_pattern.items(), key=lambda x: x[1])
            insights.append(f"📅 계절성이 감지되었습니다. {peak_month[0]}월에 수익이 최대가 됩니다.")
        
        # 예측 기반 인사이트
        if predictions:
            future_profits = [p.predicted_profit for p in predictions]
            avg_future_profit = sum(future_profits) / len(future_profits)
            
            current_avg_profit = sum(current_data.get('profits', [0])) / len(current_data.get('profits', [1]))
            
            if avg_future_profit > current_avg_profit * 1.1:
                insights.append("💰 향후 6개월간 수익 개선이 예상됩니다. 투자 확대를 고려하세요.")
            elif avg_future_profit < current_avg_profit * 0.9:
                insights.append("💸 향후 수익 감소가 우려됩니다. 비용 절감과 효율성 개선이 필요합니다.")
            
            # 신뢰구간 기반 리스크 평가
            max_risk = max(p.confidence_upper - p.confidence_lower for p in predictions)
            if max_risk > abs(avg_future_profit) * 0.5:
                insights.append("🎲 예측 불확실성이 높습니다. 다양한 시나리오를 준비하세요.")
        
        # 성장률 기반 인사이트
        if abs(trend_analysis.growth_rate) > 20:
            if trend_analysis.growth_rate > 0:
                insights.append(f"🎯 연간 성장률이 {trend_analysis.growth_rate:.1f}%로 우수합니다!")
            else:
                insights.append(f"📉 연간 성장률이 {trend_analysis.growth_rate:.1f}%로 개선이 필요합니다.")
        
        return insights

# 전역 예측 서비스 인스턴스
prediction_service = SimplePredictionService()