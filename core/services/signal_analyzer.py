"""신호 분석 시스템 - 거래량 급증 및 기술적 지표 분석 (실시간 API 기반)"""

import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class SignalAnalyzer:
    """신호 분석 엔진 - 거래량 급증 및 기술적 지표 기반 매수/매도 신호 감지"""
    
    def __init__(self):
        self.min_candles = 20  # 최소 캔들 수 (실시간 API 최적화)
        
    async def check_buy_signal(self, market: str, params: Dict) -> Optional[Dict]:
        """종합 매수 신호 확인"""
        try:
            # 1. 기본 데이터 조회
            candle_data = await self._get_candle_data(market, self.min_candles)
            if not candle_data or len(candle_data) < self.min_candles:
                logger.warning(f"⚠️ {market} 캔들 데이터 부족 ({len(candle_data) if candle_data else 0}개)")
                return None
            
            # 2. 거래량 급증 확인
            volume_signal = await self._check_volume_surge(market, params)
            if not volume_signal["is_surge"]:
                return None
            
            # 3. 가격 변동률 확인
            price_change = self._calculate_price_change(candle_data)
            if price_change < params["price_change"]:
                return None
            
            # 4. 기술적 지표 확인
            technical_signals = self._calculate_technical_indicators(candle_data, params)
            if not technical_signals["bullish"]:
                return None
            
            # 5. 캔들 패턴 확인
            candle_pattern = self._analyze_candle_pattern(candle_data, params)
            if not candle_pattern["bullish"]:
                return None
            
            # 6. 종합 신호 강도 계산
            signal_strength = self._calculate_signal_strength(
                volume_signal, technical_signals, candle_pattern, price_change
            )
            
            # MTFA 최적화된 코인별 신뢰도 임계값 사용
            mtfa_threshold = params.get("mtfa_threshold", 0.80) * 100  # 퍼센트로 변환
            if signal_strength >= mtfa_threshold:
                return {
                    "should_buy": True,
                    "signal_strength": signal_strength,
                    "confidence": technical_signals["confidence"],
                    "reason": f"거래량 급증 {volume_signal['surge_ratio']:.1f}배, 가격상승 {price_change:.2f}%",
                    "volume_surge_ratio": volume_signal["surge_ratio"],
                    "price_change": price_change,
                    "technical_score": technical_signals["score"],
                    "candle_score": candle_pattern["score"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"⚠️ {market} 신호 분석 오류: {str(e)}")
            return None

    async def analyze_buy_conditions_detailed(self, market: str, params: Dict) -> Dict:
        """실시간 매수 조건 세부 분석 - 개별 조건별 상태 확인"""
        try:
            logger.debug(f"🎯 {market} 상세 분석 시작")
            # 1. 기본 데이터 조회
            candle_data = await self._get_candle_data(market, self.min_candles)
            
            result = {
                "market": market,
                "timestamp": int(time.time()),
                "data_available": len(candle_data) >= self.min_candles if candle_data else False,
                "conditions": {},
                "overall_signal": "조건x",
                "signal_strength": 0,
                "current_price": 0.0
            }
            
            if not candle_data or len(candle_data) < self.min_candles:
                result["conditions"] = {
                    "data_sufficient": {"status": "❌", "value": f"{len(candle_data) if candle_data else 0}개", "required": f"{self.min_candles}개"},
                    "volume_surge": {"status": "❌", "value": "데이터 부족", "required": f"{params.get('volume_mult', 1.5)}배"},
                    "price_change": {"status": "❌", "value": "데이터 부족", "required": f"{params.get('price_change', 0.3)}%"},
                    "technical_signals": {"status": "❌", "value": "데이터 부족", "required": "50점"},
                    "candle_pattern": {"status": "❌", "value": "데이터 부족", "required": "50점"}
                }
                return result
            
            result["current_price"] = candle_data[-1]["close"]
            
            # 2. 거래량 급증 분석
            volume_signal = await self._check_volume_surge(market, params)
            volume_threshold = params.get("volume_mult", 1.5)
            result["conditions"]["volume_surge"] = {
                "status": "✅" if volume_signal["is_surge"] else "❌",
                "value": f"{volume_signal['surge_ratio']:.1f}배",
                "required": f"{volume_threshold}배",
                "details": f"최근: {volume_signal.get('recent_volume', 0):.0f}, 평균: {volume_signal.get('historical_volume', 0):.0f}"
            }
            
            # 3. 가격 변동률 분석
            price_change = self._calculate_price_change(candle_data)
            price_threshold = params.get("price_change", 0.3)
            result["conditions"]["price_change"] = {
                "status": "✅" if price_change >= price_threshold else "❌",
                "value": f"{price_change:.2f}%",
                "required": f"{price_threshold}%",
                "details": f"5분간 변동률"
            }
            
            # 4. 기술적 지표 분석
            technical_signals = self._calculate_technical_indicators(candle_data, params)
            result["conditions"]["technical_signals"] = {
                "status": "✅" if technical_signals["bullish"] else "❌",
                "value": f"{technical_signals['score']}점",
                "required": "50점",
                "details": f"EMA5: {technical_signals.get('ema5', 0):.0f}, RSI: {technical_signals.get('rsi', 0):.1f}, VWAP: {technical_signals.get('vwap', 0):.0f}"
            }
            
            # 5. 캔들 패턴 분석
            candle_pattern = self._analyze_candle_pattern(candle_data, params)
            result["conditions"]["candle_pattern"] = {
                "status": "✅" if candle_pattern["bullish"] else "❌",
                "value": f"{candle_pattern['score']}점",
                "required": "50점",
                "details": f"캔들 포지션: {candle_pattern.get('candle_position', 0):.2f}"
            }
            
            # 6. 데이터 충분성 확인
            result["conditions"]["data_sufficient"] = {
                "status": "✅",
                "value": f"{len(candle_data)}개",
                "required": f"{self.min_candles}개",
                "details": "최근 데이터 사용"
            }
            
            # 7. 종합 신호 강도 계산
            if all(cond["status"] == "✅" for cond in result["conditions"].values()):
                signal_strength = self._calculate_signal_strength(
                    volume_signal, technical_signals, candle_pattern, price_change
                )
                result["signal_strength"] = signal_strength
                
                if signal_strength >= 60:
                    result["overall_signal"] = "가능o"
                else:
                    result["overall_signal"] = "조건x"
            else:
                result["overall_signal"] = "조건x"
            
            return result
            
        except Exception as e:
            logger.error(f"⚠️ {market} 상세 조건 분석 오류: {str(e)}")
            return {
                "market": market,
                "timestamp": int(time.time()),
                "data_available": False,
                "conditions": {},
                "overall_signal": "오류",
                "signal_strength": 0,
                "current_price": 0.0,
                "error": str(e)
            }
    
    async def _get_candle_data(self, market: str, limit: int = 20) -> List[Dict]:
        """실시간 캔들 데이터 조회 - 업비트 API 직접 호출"""
        try:
            # 공개 업비트 클라이언트 가져오기 (인증 불필요)
            from ..api.system import public_upbit_client
            
            if not public_upbit_client:
                logger.error(f"⚠️ 업비트 클라이언트가 연결되지 않았습니다")
                return []
            
            logger.debug(f"🔍 {market} 캔들 데이터 요청 시작...")
            
            # 업비트 API에서 직접 캔들 데이터 가져오기
            response = await public_upbit_client.get_minute_candles(market, limit)
            
            logger.debug(f"📥 {market} API 응답: {type(response)}, 길이: {len(response) if response else 0}")
            
            if not response or not isinstance(response, list):
                logger.warning(f"⚠️ {market} API 응답이 비어있습니다 - 응답: {response}")
                return []
            
            # 첫 번째 캔들 데이터 구조 확인 (디버깅용)
            if response and len(response) > 0:
                logger.debug(f"🔍 {market} 첫 번째 캔들 데이터 구조: {list(response[0].keys())}")
                logger.debug(f"🔍 {market} 첫 번째 캔들 샘플: trade_price={response[0].get('trade_price')}, closing_price={response[0].get('closing_price')}")
            
            # 데이터 변환 (시간순 정렬 - 최신 데이터가 뒤로)
            candle_data = []
            for candle in reversed(response):  # API는 최신순이므로 뒤집기
                candle_data.append({
                    "timestamp": int(candle.get("timestamp", 0) / 1000),  # 밀리초 → 초
                    "open": float(candle.get("opening_price", 0)),
                    "high": float(candle.get("high_price", 0)),
                    "low": float(candle.get("low_price", 0)),
                    "close": float(candle.get("trade_price", 0)),
                    "volume": float(candle.get("candle_acc_trade_volume", 0))
                })
            
            logger.debug(f"📊 {market} 실시간 캔들 데이터 {len(candle_data)}개 조회 완료")
            return candle_data
            
        except Exception as e:
            logger.error(f"⚠️ {market} 실시간 캔들 데이터 조회 오류: {str(e)}")
            return []
    
    async def _check_volume_surge(self, market: str, params: Dict) -> Dict:
        """거래량 급증 확인 - 실시간 캔들 데이터 기반"""
        try:
            # 실시간 캔들 데이터에서 거래량 정보 추출 (20개면 충분)
            # _get_candle_data가 이미 public_upbit_client를 사용하므로 그대로 호출
            candle_data = await self._get_candle_data(market, 20)
            
            if len(candle_data) < 10:
                return {"is_surge": False, "surge_ratio": 0}
            
            # 거래량만 추출
            volumes = [candle["volume"] for candle in candle_data]
            
            # 최근 3개 캔들의 평균 거래량
            recent_volume = sum(volumes[-3:]) / 3
            
            # 과거 평균 거래량 (최근 3개 제외)
            historical_volume = sum(volumes[:-3]) / (len(volumes) - 3)
            
            if historical_volume == 0:
                return {"is_surge": False, "surge_ratio": 0}
            
            surge_ratio = recent_volume / historical_volume
            volume_threshold = params.get("volume_mult", 1.5)
            
            return {
                "is_surge": surge_ratio >= volume_threshold,
                "surge_ratio": surge_ratio,
                "recent_volume": recent_volume,
                "historical_volume": historical_volume
            }
            
        except Exception as e:
            logger.error(f"⚠️ {market} 거래량 급증 확인 오류: {str(e)}")
            return {"is_surge": False, "surge_ratio": 0}
    
    def _calculate_price_change(self, candle_data: List[Dict]) -> float:
        """가격 변동률 계산"""
        if len(candle_data) < 5:
            return 0.0
        
        # 최근 5분간 가격 변동률
        recent_price = candle_data[-1]["close"]
        past_price = candle_data[-5]["close"]
        
        if past_price == 0:
            return 0.0
        
        return ((recent_price - past_price) / past_price) * 100
    
    def _calculate_technical_indicators(self, candle_data: List[Dict], params: Dict) -> Dict:
        """기술적 지표 계산"""
        try:
            closes = [candle["close"] for candle in candle_data]
            volumes = [candle["volume"] for candle in candle_data]
            
            if len(closes) < 14:
                return {"bullish": False, "confidence": 0, "score": 0}
            
            # EMA 계산
            ema5 = self._calculate_ema(closes, 5)
            ema10 = self._calculate_ema(closes, 10)
            
            # RSI 계산
            rsi = self._calculate_rsi(closes, 14)
            
            # VWAP 계산
            vwap = self._calculate_vwap(candle_data)
            current_price = closes[-1]
            
            # 신호 점수 계산
            score = 0
            
            # EMA 크로스오버 (EMA5 > EMA10)
            if ema5 > ema10:
                score += 25
            
            # RSI 조건 (30 < RSI < 70)
            if 30 < rsi < 70:
                score += 20
            
            # VWAP 상승 돌파
            if current_price > vwap:
                score += 25
            
            # 상승 추세 확인
            if len(closes) >= 3 and closes[-1] > closes[-3]:
                score += 15
            
            # 거래량 증가 확인
            if len(volumes) >= 2 and volumes[-1] > volumes[-2]:
                score += 15
            
            confidence = min(score, 100)
            
            return {
                "bullish": score >= 50,
                "confidence": confidence,
                "score": score,
                "ema5": ema5,
                "ema10": ema10,
                "rsi": rsi,
                "vwap": vwap
            }
            
        except Exception as e:
            logger.error(f"기술적 지표 계산 오류: {str(e)}")
            return {"bullish": False, "confidence": 0, "score": 0}
    
    def _analyze_candle_pattern(self, candle_data: List[Dict], params: Dict) -> Dict:
        """캔들 패턴 분석"""
        try:
            if len(candle_data) < 3:
                return {"bullish": False, "score": 0}
            
            score = 0
            latest = candle_data[-1]
            prev = candle_data[-2]
            
            # 양봉 여부
            if latest["close"] > latest["open"]:
                score += 30
            
            # 상승 캔들 연속성
            if latest["close"] > prev["close"]:
                score += 25
            
            # 캔들 포지션 (고가 대비 종가 위치)
            if latest["high"] > latest["low"]:
                candle_position = (latest["close"] - latest["low"]) / (latest["high"] - latest["low"])
                candle_threshold = params.get("candle_pos", 0.6)
                
                if candle_position >= candle_threshold:
                    score += 25
            
            # 거래량과 가격 상승 동반
            if len(candle_data) >= 2:
                if (latest["volume"] > prev["volume"] and 
                    latest["close"] > prev["close"]):
                    score += 20
            
            return {
                "bullish": score >= 50,
                "score": score,
                "candle_position": candle_position if 'candle_position' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"캔들 패턴 분석 오류: {str(e)}")
            return {"bullish": False, "score": 0}
    
    def _calculate_signal_strength(self, volume_signal: Dict, technical_signals: Dict, 
                                 candle_pattern: Dict, price_change: float) -> int:
        """종합 신호 강도 계산"""
        strength = 0
        
        # 거래량 급증 (30점)
        if volume_signal["is_surge"]:
            surge_ratio = volume_signal["surge_ratio"]
            if surge_ratio >= 3.0:
                strength += 30
            elif surge_ratio >= 2.0:
                strength += 20
            elif surge_ratio >= 1.5:
                strength += 15
        
        # 기술적 지표 (30점)
        strength += min(technical_signals["score"] * 0.3, 30)
        
        # 캔들 패턴 (20점)
        strength += min(candle_pattern["score"] * 0.2, 20)
        
        # 가격 변동률 (20점)
        if price_change >= 1.0:
            strength += 20
        elif price_change >= 0.5:
            strength += 15
        elif price_change >= 0.3:
            strength += 10
        elif price_change >= 0.1:
            strength += 5
        
        return min(int(strength), 100)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """지수 이동 평균 계산"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_vwap(self, candle_data: List[Dict]) -> float:
        """VWAP (거래량 가중 평균 가격) 계산"""
        if not candle_data:
            return 0.0
        
        total_volume = 0
        total_price_volume = 0
        
        for candle in candle_data:
            typical_price = (candle["high"] + candle["low"] + candle["close"]) / 3
            volume = candle["volume"]
            
            total_price_volume += typical_price * volume
            total_volume += volume
        
        if total_volume == 0:
            return 0.0
        
        return total_price_volume / total_volume

# 전역 신호 분석기 인스턴스
signal_analyzer = SignalAnalyzer()