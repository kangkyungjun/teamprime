"""
계좌 정보 관리 서비스
잔고 조회, 포트폴리오 분석, 자산 현황 제공
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
from decimal import Decimal

logger = logging.getLogger(__name__)

@dataclass
class AccountBalance:
    """계좌 잔고 정보"""
    currency: str
    balance: float
    locked: float  # 주문 중인 금액
    avg_buy_price: float  # 매수 평균가
    unit_currency: str  # 마켓 단위
    
    @property
    def available_balance(self) -> float:
        """사용 가능한 잔고"""
        return max(0, self.balance - self.locked)
    
    @property
    def total_krw_value(self) -> float:
        """총 원화 가치"""
        if self.currency == "KRW":
            return self.balance
        return self.balance * self.avg_buy_price if self.avg_buy_price > 0 else 0

@dataclass
class PortfolioAsset:
    """포트폴리오 자산"""
    market: str
    currency: str
    balance: float
    avg_buy_price: float
    current_price: float
    
    @property
    def total_value(self) -> float:
        """총 보유 가치 (원화)"""
        return self.balance * self.current_price
    
    @property
    def total_cost(self) -> float:
        """총 매수 금액 (원화)"""
        return self.balance * self.avg_buy_price
    
    @property
    def profit_loss(self) -> float:
        """손익 (원화)"""
        return self.total_value - self.total_cost
    
    @property
    def profit_loss_rate(self) -> float:
        """손익률 (%)"""
        if self.total_cost <= 0:
            return 0.0
        return (self.profit_loss / self.total_cost) * 100

@dataclass
class PortfolioSummary:
    """포트폴리오 요약"""
    total_krw_balance: float  # 원화 잔고
    total_asset_value: float  # 총 자산 가치
    total_cost: float  # 총 투자 금액
    total_profit_loss: float  # 총 손익
    total_profit_loss_rate: float  # 총 손익률
    asset_count: int  # 보유 종목 수
    
    @property
    def total_balance(self) -> float:
        """총 계좌 잔고 (원화 + 자산)"""
        return self.total_krw_balance + self.total_asset_value

class AccountService:
    """계좌 정보 관리 서비스"""
    
    def __init__(self):
        self.balance_cache: Dict[str, AccountBalance] = {}
        self.portfolio_cache: Dict[str, List[PortfolioAsset]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = 60  # 1분 캐시
        
        logger.info("✅ 계좌 정보 서비스 초기화 완료")
    
    async def get_account_balances(self, access_key: str, secret_key: str) -> List[AccountBalance]:
        """계좌 잔고 조회"""
        try:
            # 캐시 확인
            cache_key = f"balance_{hash(access_key)}"
            if self._is_cache_valid(cache_key):
                logger.debug("💾 캐시에서 잔고 정보 조회")
                return list(self.balance_cache.get(cache_key, {}).values())
            
            # 업비트 API 호출
            from ..utils.api_manager import create_authenticated_request
            from core.session.session_manager import session_manager
            
            # 세션에서 API 클라이언트 가져오기
            session_id = session_manager.get_session_id_from_keys(access_key, secret_key)
            if not session_id:
                raise Exception("유효하지 않은 API 키입니다")
            
            api_client = session_manager.get_api_client(session_id)
            if not api_client:
                raise Exception("API 클라이언트를 찾을 수 없습니다")
            
            # 잔고 조회 요청
            url = "https://api.upbit.com/v1/accounts"
            headers = create_authenticated_request("GET", url, {}, access_key, secret_key)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ 잔고 조회 API 오류 ({response.status}): {error_text}")
                        raise Exception(f"잔고 조회 실패: {error_text}")
                    
                    data = await response.json()
                    
                    # AccountBalance 객체 생성
                    balances = []
                    balance_dict = {}
                    
                    for item in data:
                        balance = AccountBalance(
                            currency=item['currency'],
                            balance=float(item['balance']),
                            locked=float(item['locked']),
                            avg_buy_price=float(item.get('avg_buy_price', 0)),
                            unit_currency=item['unit_currency']
                        )
                        
                        # 잔고가 있는 것만 포함
                        if balance.balance > 0 or balance.locked > 0:
                            balances.append(balance)
                            balance_dict[balance.currency] = balance
                    
                    # 캐시 업데이트
                    self.balance_cache[cache_key] = balance_dict
                    self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)
                    
                    logger.info(f"💰 계좌 잔고 조회 완료: {len(balances)}개 통화")
                    return balances
                    
        except Exception as e:
            logger.error(f"❌ 계좌 잔고 조회 오류: {str(e)}")
            raise Exception(f"잔고 조회 실패: {str(e)}")
    
    async def get_portfolio_analysis(self, access_key: str, secret_key: str) -> PortfolioSummary:
        """포트폴리오 분석"""
        try:
            # 잔고 조회
            balances = await self.get_account_balances(access_key, secret_key)
            
            # 원화 잔고 찾기
            krw_balance = 0.0
            crypto_balances = []
            
            for balance in balances:
                if balance.currency == "KRW":
                    krw_balance = balance.available_balance
                else:
                    crypto_balances.append(balance)
            
            # 암호화폐 자산 분석
            portfolio_assets = []
            total_asset_value = 0.0
            total_cost = 0.0
            
            # 현재 시세 조회
            current_prices = await self._get_current_prices([f"KRW-{balance.currency}" for balance in crypto_balances])
            
            for balance in crypto_balances:
                market = f"KRW-{balance.currency}"
                current_price = current_prices.get(market, 0.0)
                
                if current_price > 0:
                    asset = PortfolioAsset(
                        market=market,
                        currency=balance.currency,
                        balance=balance.balance,
                        avg_buy_price=balance.avg_buy_price,
                        current_price=current_price
                    )
                    
                    portfolio_assets.append(asset)
                    total_asset_value += asset.total_value
                    total_cost += asset.total_cost
            
            # 포트폴리오 요약 생성
            total_profit_loss = total_asset_value - total_cost
            total_profit_loss_rate = (total_profit_loss / total_cost * 100) if total_cost > 0 else 0.0
            
            summary = PortfolioSummary(
                total_krw_balance=krw_balance,
                total_asset_value=total_asset_value,
                total_cost=total_cost,
                total_profit_loss=total_profit_loss,
                total_profit_loss_rate=total_profit_loss_rate,
                asset_count=len(portfolio_assets)
            )
            
            logger.info(f"📊 포트폴리오 분석 완료: {summary.asset_count}개 자산, 총 {summary.total_balance:,.0f}원")
            return summary
            
        except Exception as e:
            logger.error(f"❌ 포트폴리오 분석 오류: {str(e)}")
            raise Exception(f"포트폴리오 분석 실패: {str(e)}")
    
    async def get_detailed_portfolio(self, access_key: str, secret_key: str) -> List[PortfolioAsset]:
        """상세 포트폴리오 조회"""
        try:
            # 캐시 확인
            cache_key = f"portfolio_{hash(access_key)}"
            if self._is_cache_valid(cache_key):
                logger.debug("💾 캐시에서 포트폴리오 조회")
                return self.portfolio_cache.get(cache_key, [])
            
            # 잔고 조회
            balances = await self.get_account_balances(access_key, secret_key)
            
            # 암호화폐 자산만 필터링
            crypto_balances = [b for b in balances if b.currency != "KRW" and b.balance > 0]
            
            if not crypto_balances:
                return []
            
            # 현재 시세 조회
            markets = [f"KRW-{balance.currency}" for balance in crypto_balances]
            current_prices = await self._get_current_prices(markets)
            
            # 포트폴리오 자산 생성
            portfolio_assets = []
            
            for balance in crypto_balances:
                market = f"KRW-{balance.currency}"
                current_price = current_prices.get(market, 0.0)
                
                if current_price > 0:
                    asset = PortfolioAsset(
                        market=market,
                        currency=balance.currency,
                        balance=balance.balance,
                        avg_buy_price=balance.avg_buy_price,
                        current_price=current_price
                    )
                    portfolio_assets.append(asset)
            
            # 손익률 기준 정렬 (수익률 높은 순)
            portfolio_assets.sort(key=lambda x: x.profit_loss_rate, reverse=True)
            
            # 캐시 업데이트
            self.portfolio_cache[cache_key] = portfolio_assets
            self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_duration)
            
            logger.info(f"📋 상세 포트폴리오 조회 완료: {len(portfolio_assets)}개 자산")
            return portfolio_assets
            
        except Exception as e:
            logger.error(f"❌ 상세 포트폴리오 조회 오류: {str(e)}")
            raise Exception(f"상세 포트폴리오 조회 실패: {str(e)}")
    
    async def _get_current_prices(self, markets: List[str]) -> Dict[str, float]:
        """현재 시세 조회"""
        try:
            if not markets:
                return {}
            
            market_param = ",".join(markets)
            url = f"https://api.upbit.com/v1/ticker?markets={market_param}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"❌ 시세 조회 API 오류: {response.status}")
                        return {}
                    
                    data = await response.json()
                    prices = {}
                    
                    for item in data:
                        market = item['market']
                        price = float(item['trade_price'])
                        prices[market] = price
                    
                    logger.debug(f"📈 현재 시세 조회 완료: {len(prices)}개 마켓")
                    return prices
                    
        except Exception as e:
            logger.error(f"❌ 시세 조회 오류: {str(e)}")
            return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[cache_key]
    
    def clear_cache(self, access_key: str = None):
        """캐시 클리어"""
        try:
            if access_key:
                # 특정 사용자 캐시만 클리어
                cache_key = f"balance_{hash(access_key)}"
                portfolio_key = f"portfolio_{hash(access_key)}"
                
                self.balance_cache.pop(cache_key, None)
                self.portfolio_cache.pop(portfolio_key, None)
                self.cache_expiry.pop(cache_key, None)
                self.cache_expiry.pop(portfolio_key, None)
                
                logger.info(f"🗑️ 사용자 캐시 클리어 완료")
            else:
                # 전체 캐시 클리어
                self.balance_cache.clear()
                self.portfolio_cache.clear()
                self.cache_expiry.clear()
                
                logger.info(f"🗑️ 전체 캐시 클리어 완료")
                
        except Exception as e:
            logger.error(f"❌ 캐시 클리어 오류: {str(e)}")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 조회"""
        return {
            "balance_cache_size": len(self.balance_cache),
            "portfolio_cache_size": len(self.portfolio_cache),
            "total_cache_entries": len(self.cache_expiry),
            "cache_duration_seconds": self.cache_duration
        }

# 전역 계좌 서비스 인스턴스
account_service = AccountService()