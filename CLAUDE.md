# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a modular cryptocurrency trading system for Upbit exchange that combines:
- **Real-time API-based signal analysis** (NO data storage - live API calls only)
- Advanced volume surge analysis and pattern recognition with 6-stage buy conditions
- **REST API-based** real-time market data retrieval (NO WebSocket dependencies)
- Automated multi-coin trading engine with scalping capabilities
- Web dashboard for trading control and portfolio monitoring
- Backtest analysis and parameter optimization

## 🎯 Core Principles

### 💰 **Primary Objective: Maximum Profitability**
- **수익률 최대화가 최우선 목표**: 모든 기능과 최적화는 수익성 향상을 위해 설계
- **데이터 기반 의사결정**: 백테스팅과 실시간 성과 분석을 통한 지속적인 수익률 개선
- **스캘핑 최적화**: 0.5% 목표 수익률, -0.3% 손절매로 단기 고빈도 거래 수익 극대화
- **자동 최적화**: 24시간 주기로 파라미터 튜닝하여 시장 변화에 맞는 최적 수익률 추구

### 🛡️ **Functional Integrity: Preserve Core Features**
- **본래 기능 훼손 금지**: 기존 거래 알고리즘과 수익 창출 로직은 절대 변경하지 않음
- **검증된 로직 보존**: 검증된 거래 전략과 리스크 관리 메커니즘 유지
- **성능 저하 방지**: 모듈화 과정에서 거래 속도나 신호 감지 성능 저하 없음
- **실제 데이터만 사용**: Mock data, 더미 데이터, 가짜 응답 절대 금지 - 실제 시장 데이터만 사용
- **하드코딩 금지**: 가용 자금, 잔고 등 실제 계좌 정보는 하드코딩 금지 - 실제 업비트 API에서 가져오기
- **호환성 유지**: 기존 API 엔드포인트와 데이터 구조 완전 호환성 보장
- **🚨 NO DATA STORAGE**: 캔들 데이터, 시장 데이터 저장 금지 - 실시간 API 호출만 사용
- **실시간 우선**: SQLite 의존성 제거, 모든 분석은 실시간 업비트 API 기반으로만 수행

### ⚡ **Performance & Reliability**
- **안정성 우선**: REST API 기반으로 안정적인 거래 실행
- **실시간 대응**: 1분 주기 신호 분석으로 빠른 시장 변화 대응
- **위험 관리**: 최대 5분 보유, 최대 5개 동시 포지션으로 리스크 제한
- **자동 복구**: 장애 상황에서도 거래 기회 손실 최소화

## Architecture

### Modular Architecture (v2.0)
The system has been refactored from a 9,800-line monolith into a clean modular structure:

```
teamprime/
├── main.py                    # Main application entry point (200 lines)
├── config.py                  # System configuration
├── database.py               # Database connections
├── api_client.py             # API client wrapper
├── data_analysis.py          # Data analysis (legacy, being migrated)
│
└── core/                     # Core modules
    ├── models/               # Data models
    │   ├── trading.py        # Position, TradingState classes
    │   └── response.py       # API response models
    │
    ├── services/             # Business logic
    │   ├── trading_engine.py # MultiCoinTradingEngine
    │   ├── optimizer.py      # Auto optimization system
    │   └── signal_analyzer.py# Signal analysis engine
    │
    ├── api/                  # FastAPI routers
    │   ├── trading.py        # Trading endpoints
    │   ├── analysis.py       # Analysis endpoints
    │   └── system.py         # System endpoints
    │
    └── utils/                # Utilities
        └── datetime_utils.py # Date/time helpers
```

### Key Components

1. **Core Models** (`core/models/`): Data structures for trading positions and API responses
2. **Services Layer** (`core/services/`): Business logic including trading engine and optimizers
3. **API Layer** (`core/api/`): REST API endpoints organized by domain
4. **Configuration** (`config.py`): Centralized system settings and constants
5. **Database Layer** (`database.py`): SQLite connection and schema management

### Data Flow (Real-time API Based)
```
Upbit REST API (Real-time) → Signal Analyzer (6-Stage Analysis)
                ↓                         ↓
        Public API Client          Trading Engine
                ↓                         ↓
        Current Price & Candles    Buy/Sell Decisions
                ↓                         ↓
Real-time UI ← FastAPI Routers ← Trade Execution
```

### 6-Stage Real-time Buy Condition Analysis
1. **Data Sufficiency Check**: 최소 20개 캔들 데이터 확보 확인
2. **Volume Surge Analysis**: 최근 3개 vs 과거 평균 거래량 비교 (임계값: 코인별 설정)
3. **Price Change Validation**: 5분간 가격 변동률 확인 (임계값: 코인별 설정)
4. **Technical Indicators**: EMA5/10, RSI, VWAP 종합 점수 (50점 이상 필요)
5. **Candle Pattern Analysis**: 캔들 포지션 분석 (고가 대비 종가 위치, 50점 이상 필요)
6. **Overall Signal Strength**: 모든 조건 통과시에만 매수 신호 생성 (60점 이상 필요)

### Database Schema
```sql
candles (
    market STRING,   -- "KRW-BTC", "KRW-XRP", etc.
    unit INTEGER,    -- 1, 5, or 15 (minutes)
    ts INTEGER,      -- UTC epoch seconds (composite PK)
    open FLOAT,
    high FLOAT, 
    low FLOAT,
    close FLOAT,
    volume FLOAT
)

ticks (
    market STRING,
    timestamp INTEGER,
    trade_price FLOAT,
    trade_volume FLOAT,
    ask_bid STRING,    -- ASK or BID
    ts_minute INTEGER  -- For minute-level grouping
)

orderbook_snapshots (
    market STRING,
    timestamp INTEGER,
    -- Additional orderbook data fields
)
```

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install fastapi uvicorn aiohttp sqlalchemy aiosqlite python-dotenv websockets pydantic requests

# Start main application
python main.py

# Start development server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Start portfolio calculator (standalone performance analysis)
python portfolio_calculator.py
```

### Module Development
```bash
# Import core modules for development
from core.models import Position, TradingState, CandleOut
from core.services import trading_engine, auto_scheduler, signal_analyzer
from core.api import trading_router, analysis_router, system_router
from core.utils import utc_now, parse_minutes_payload

# Configuration access
from config import DEFAULT_MARKETS, SCALPING_CONFIG, ANALYSIS_CONFIG, OPTIMIZATION_CONFIG
```

### Module Structure Navigation
```bash
# Core Models (core/models/)
# - trading.py: Position, TradingState classes
# - response.py: API response models (CandleOut, etc.)

# Services (core/services/)
# - trading_engine.py: MultiCoinTradingEngine class
# - optimizer.py: WeeklyOptimizer, AutoOptimizationScheduler
# - signal_analyzer.py: Real-time signal analysis

# API Routers (core/api/)
# - trading.py: Trading control endpoints
# - analysis.py: Data analysis endpoints  
# - system.py: System status endpoints

# Configuration
# - config.py: All system settings and constants
# - database.py: Database connection and schema
```

### Database Operations
```bash
# Database inspection
sqlite3 upbit_candles.db
.tables
SELECT market, unit, COUNT(*) FROM candles GROUP BY market, unit;

# Check data freshness
SELECT market, MAX(ts) as latest_ts, 
       datetime(MAX(ts), 'unixepoch') as latest_time
FROM candles GROUP BY market;
```

### API Testing
```bash
# System status
curl http://localhost:8001/api/system-status

# Start/stop trading
curl -X POST http://localhost:8001/api/start-trading
curl -X POST http://localhost:8001/api/stop-trading

# Volume surge analysis
curl "http://localhost:8001/volume-surge-analysis?market=KRW-BTC&hours=24"

# Backtest analysis
curl "http://localhost:8001/backtest-performance?market=KRW-BTC&days=30"

# Parameter optimization
curl "http://localhost:8001/optimize-coin-parameters/KRW-BTC"
curl -X POST http://localhost:8001/api/run-manual-optimization

# Data quality and cache status
curl http://localhost:8001/api/data-quality
curl http://localhost:8001/api/cache-status

# Trading analysis
curl http://localhost:8001/api/trading-status
curl http://localhost:8001/api/trading-logs
```

### Environment Configuration
```env
MARKETS=KRW-BTC,KRW-XRP,KRW-ETH,KRW-DOGE,KRW-BTT
YEARS=3
DB_URL=sqlite+aiosqlite:///./upbit_candles.db
```

## Key System Components

### Core Models (`core/models/`)
- **Position** (`trading.py`): Individual trade position tracking with P&L calculation
- **TradingState** (`trading.py`): Global trading state management and portfolio tracking
- **CandleOut** (`response.py`): Standardized API response models for market data

### Public API Client (`core/api/system.py`)
- **PublicUpbitAPI**: 인증 불필요한 공개 캔들 데이터 조회 전용 클라이언트
- **Real-time Data**: 매번 새로운 API 호출로 최신 20개 캔들 데이터 조회
- **No Authentication**: 캔들 데이터는 공개 API이므로 로그인 없이도 분석 가능

### Trading Engine (`core/services/trading_engine.py`)
- **Scalping Mode**: Ultra-fast trading optimized for 0.5% profit target, -0.3% stop loss
- **Multi-coin Analysis**: Simultaneous monitoring of 5+ cryptocurrencies via REST API
- **Signal-driven Trading**: 1-minute interval signal analysis with confidence scoring
- **Risk Management**: Position limits, daily loss limits, maximum holding time (5 minutes)
- **REST API Mode**: Stable operation without WebSocket dependencies

### Signal Analyzer (`core/services/signal_analyzer.py`) - Real-time API Based
- **Real-time Volume Analysis**: 실시간 API 호출로 최근 3개 vs 과거 평균 거래량 비교
- **Live Technical Indicators**: 실시간 EMA5/10, RSI, VWAP 계산 (최신 20개 캔들 기반)
- **6-Stage Buy Condition Validation**: 
  1. 데이터 충분성 (20개 캔들) → 2. 거래량 급증 확인 → 3. 가격 변동률 검증 
  4. 기술적 지표 점수 → 5. 캔들 패턴 분석 → 6. 종합 신호 강도 계산
- **Instant Analysis**: SQLite 제거로 API 호출 → 즉시 분석 → 즉시 결과 반환
- **Live Price Integration**: 실시간 현재가와 함께 매수 조건 상태 제공

### Auto Optimizer (`core/services/optimizer.py`)
- **Automated Parameter Tuning**: 24-hour optimization cycles with backtesting
- **Performance Tracking**: Win rate targeting (60%+) with trade history analysis
- **Scheduler Integration**: Background optimization with minimal trading disruption
- **Dynamic Adaptation**: Parameter adjustment based on market conditions

### API Routers (`core/api/`)
- **Trading Router** (`trading.py`): Start/stop trading, position management, emergency controls
- **Analysis Router** (`analysis.py`): Volume analysis, backtesting, multi-coin analysis
- **System Router** (`system.py`): Health checks, status monitoring, data quality metrics

### Configuration System (`config.py`)
- **Trading Settings**: Scalping parameters, position limits, risk management
- **Analysis Settings**: Technical indicator periods, pattern recognition thresholds
- **Optimization Settings**: Auto-optimization schedules and performance targets
- **System Settings**: Logging, web server, database configuration

## Web Dashboard Features

### Main Interface (`http://localhost:8001/`)
- **System Status**: WebSocket connection, data quality, API health
- **Trading Controls**: Start/stop automation, emergency stop
- **Real-time Monitoring**: Positions, P&L, market data
- **Data Analysis**: 1-year/3-year historical analysis modals

### API Endpoints
- `/api/system-status` - Real-time system health and connection status
- `/api/trading-status` - Current positions and trading state
- `/api/start-trading` - Initialize automated trading engine
- `/api/stop-trading` - Stop automated trading engine
- `/api/emergency-stop` - Immediate halt of all trading activity
- `/api/data-quality` - Data freshness and completeness metrics
- `/api/cache-status` - Performance monitoring and cache statistics
- `/volume-surge-analysis` - Real-time volume anomaly detection
- `/backtest-performance` - Historical performance analysis
- `/optimize-coin-parameters/{market}` - Individual coin optimization
- `/api/run-manual-optimization` - Manual parameter optimization trigger
- `/multi-coin-analysis` - Cross-coin analysis and comparison
- `/portfolio-optimization` - Portfolio allocation recommendations

### 🚨 Real-time API Endpoints (v2.1)
- `/real-time-buy-conditions` - **6단계 실시간 매수 조건 분석** 
  - 실시간 업비트 API 호출로 현재가 및 20개 캔들 데이터 조회
  - 코인별 상세 조건 상태 (✅/❌) 및 실제값 vs 요구값 비교
  - 데이터 저장 없이 즉시 분석 후 결과 반환
- `/buy-conditions-summary` - 간략한 매수 조건 요약 정보

## Development Considerations

### Modular Development Guidelines
- **Module Independence**: Each core module should have minimal dependencies
- **Single Responsibility**: Each module handles one specific domain (trading, analysis, API)
- **Clean Interfaces**: Use proper imports and avoid circular dependencies
- **Configuration Centralization**: All settings managed through `config.py`

### Trading Safety Mechanisms
- **Position Limits**: Maximum 5 concurrent positions configured in `SCALPING_CONFIG`
- **Risk Management**: Built-in profit targets (0.5%) and stop losses (-0.3%)
- **Hold Time Limits**: Maximum 5-minute position holding time for scalping
- **Signal Confidence**: Minimum 50% confidence threshold for trade execution
- **Emergency Controls**: Immediate position closure via `/api/emergency-stop`

### Module Architecture Patterns
- **Services Pattern**: Business logic isolated in `core/services/`
- **Repository Pattern**: Database operations in dedicated modules
- **Router Pattern**: API endpoints organized by domain in `core/api/`
- **Model Pattern**: Data structures defined in `core/models/`

### REST API Strategy
- **Stability Focus**: Removed WebSocket dependencies for reliable operation
- **Rate Limiting**: Upbit API compliance with 600 req/min, 10 req/sec limits
- **Interval-based**: 1-minute signal analysis cycles to minimize API calls
- **Error Recovery**: Graceful handling of API failures with retry logic

### Database Performance
- **Composite Primary Key**: (market, unit, ts) for automatic deduplication
- **Incremental Sync**: Only fetches missing data gaps using time-based queries
- **Batch Operations**: Efficient `INSERT OR IGNORE` for upserts
- **Connection Management**: Async SQLite with proper connection pooling

### Configuration Management
- **Environment Variables**: Market selection, years of data, database URL
- **Typed Constants**: All configuration in `config.py` with proper typing
- **Profile-based Settings**: Separate configs for scalping, analysis, optimization
- **Runtime Validation**: Configuration validation at startup

## System Monitoring

### Log Patterns
```
✅ WebSocket 연결 및 구독 완료  - Successful connection
📊 WebSocket 성능: X.X msg/s   - Performance metrics
⚠️ 연속 X회 실패              - Rate limit warnings
❌ WebSocket 연결 오류         - Connection errors
```

### Critical Module Instances
- `trading_engine` - MultiCoinTradingEngine instance in `core.services.trading_engine`
- `trading_state` - Global TradingState in `core.services.trading_engine`  
- `auto_scheduler` - AutoOptimizationScheduler in `core.services.optimizer`
- `signal_analyzer` - SignalAnalyzer in `core.services.signal_analyzer`

### System Configuration
- Default port: 8001 (configured in `config.py`)
- FastAPI runs on all interfaces (0.0.0.0) for remote access
- REST API mode: No WebSocket dependencies for stability
- Database: SQLite with async operations via aiosqlite

## Testing and Debugging

### Common Issues
- **"시스템 정보를 불러오는 중..."**: API endpoint errors, check global variable access
- **WebSocket disconnections**: Network issues or API rate limits
- **Trading not starting**: Login status or insufficient funds
- **Database lock errors**: Multiple sync processes running simultaneously

### Debug Endpoints
- `/api/system-status/detailed` - Extended diagnostics with WebSocket metrics
- `/api/data-quality` - Data freshness and completeness metrics
- `/api/cache-status` - Performance monitoring and cache statistics
- `/api/realtime-candle-status` - Real-time candle data processing status
- `/api/ultra-fast-signals` - Ultra-fast trading signal analysis
- `/api/coin-trading-criteria` - Individual coin trading criteria and thresholds
- `/api/strategy-history` - Historical strategy performance tracking

### Performance Constants
- **BATCH**: 200 (Upbit API candles limit per request, configured in `config.py`)
- **CONCURRENCY**: 1 (Serial processing for rate limit safety)
- **Rate Limits**: REST API (600/min, 10/sec), Order API (200/min, 8/sec)
- **Signal Intervals**: 1-minute cycles for real-time analysis
- **Optimization Cycles**: 24-hour automated parameter tuning
- **🚨 MANDATORY 60-SECOND RULE**: All Upbit API requests MUST maintain 60-second intervals to comply with API regulations

## Migration from Legacy Architecture

### Key Changes in v2.0
- **Single File → Modular**: 9,800-line monolith split into focused modules
- **WebSocket → REST API**: Improved stability with interval-based data collection
- **Hardcoded → Configuration**: All settings centralized in `config.py`
- **Embedded → Service Layer**: Business logic extracted to `core/services/`

### 🚨 Critical Changes in v2.1 (Real-time API Migration)
- **SQLite Storage → Real-time API**: Complete removal of data storage dependencies
- **Database-driven → Live Analysis**: All signal analysis now uses direct Upbit API calls
- **Cached Data → Fresh Data**: Every analysis fetches live 20-candle data from Upbit
- **Complex Storage Logic → Simple API Client**: Simplified architecture with PublicUpbitAPI class
- **Mixed Architecture → Pure Real-time**: No hybrid approach - 100% real-time API based

### Import Path Changes
```python
# Legacy (v1.0)
from main import MultiCoinTradingEngine, Position, TradingState

# Modular (v2.0)
from core.services.trading_engine import trading_engine, trading_state
from core.models.trading import Position, TradingState
```

### Configuration Migration
```python
# Legacy: Hardcoded constants in main.py
PROFIT_TARGET = 0.5
STOP_LOSS = -0.3

# Modular: Centralized configuration
from config import SCALPING_CONFIG
profit_target = SCALPING_CONFIG["profit_target"]
stop_loss = SCALPING_CONFIG["stop_loss"]
```

### Legacy Files
- `main.py.backup` - Original 9,800-line monolith (backup)
- `data_analysis.py` - Analysis functions (being migrated to `core/services/`)
- `trading_engine.py` - Legacy trading engine (replaced by `core/services/trading_engine.py`)

### Development Best Practices
- **💰 Profitability First**: All changes must maintain or improve profitability metrics
- **🛡️ Core Function Preservation**: Never modify proven trading algorithms or profit-generating logic
- **📊 Performance Validation**: Test all changes against historical performance benchmarks
- **Module Testing**: Test individual modules in isolation
- **Clean Imports**: Use absolute imports from `core` package
- **Configuration First**: Check `config.py` before hardcoding values
- **Service Layer**: Put business logic in `core/services/`, not API routes

### 🚨 Critical Development Rules
- **NO MODIFICATION** of core trading algorithms in `core/services/trading_engine.py`
- **NO CHANGES** to profit targets (0.5%) or stop-loss (-0.3%) without backtesting validation
- **NO PERFORMANCE DEGRADATION** in signal detection or trade execution speed
- **NO MOCK DATA**: Never add mock data, dummy data, or fake responses - use only real market data
- **NO HARDCODING**: Never hardcode account balances, available funds, or financial data - use real Upbit API
- **MANDATORY BACKTESTING** for any parameter or logic changes
- **PRESERVE API COMPATIBILITY** for all existing endpoints
- **🚨 UPBIT API 60-SECOND RULE COMPLIANCE**: ALL Upbit API requests must maintain 60-second intervals between calls to the same endpoint to comply with Upbit regulations. This is MANDATORY and cannot be compromised.

### 🚨 Real-time API Architecture Rules (v2.1)
- **NO DATA STORAGE**: 절대로 캔들 데이터, 시장 데이터를 SQLite나 다른 저장소에 저장하지 않음
- **LIVE API ONLY**: 모든 신호 분석은 실시간 업비트 API 호출을 통해서만 수행
- **PUBLIC API SEPARATION**: 인증이 필요 없는 캔들 데이터 조회는 PublicUpbitAPI 클래스 사용
- **20-CANDLE ANALYSIS**: 신호 분석용 캔들 데이터는 실시간으로 20개만 조회하여 분석
- **6-STAGE VALIDATION**: 모든 매수 조건은 6단계 실시간 검증 과정을 거쳐야 함
- **NO CACHING**: 캔들 데이터나 분석 결과 캐싱 금지 - 매번 새로운 API 호출로 최신 데이터 사용
- **IMMEDIATE ANALYSIS**: API 호출 → 즉시 분석 → 즉시 결과 반환 (저장 단계 없음)

## 🚀 Enhanced MTFA Trading Strategy System (NEW)

### 코인별 최적 매수매도 전략 분석 시스템
**파일**: `enhanced_mtfa_notebook_cell.py`
**목적**: 각 코인별로 최대 수익률을 위한 개별 맞춤 매수매도 전략 도출

### 핵심 특징
- **💰 수익률 최대화 우선**: 모든 최적화는 수익률 극대화에 집중
- **🎯 코인별 개별 전략**: 189개 코인 각각에 최적화된 고유 파라미터
- **⚡ 2,520가지 조합 탐색**: 익절률(8) × 손절률(7) × 보유시간(9) × 신뢰도(5) = 전수 조합 테스트
- **🔒 6단계 강화 검증**: 음수 수익률 완전 차단, 최소수익률 1.4%, 승률 50%+, 거래횟수 5회+, 신뢰도 80%+, 위험대비수익 검증
- **🚀 성능 최적화**: 스마트 스킵으로 최대 70% 연산량 절감

### 매수매도 전략 파라미터
```python
# 그리드 서치 범위
TP_GRID_PCT = [0.005, 0.008, 0.010, 0.012, 0.015, 0.020, 0.025, 0.030]  # 익절률 8개
SL_GRID_PCT = [-0.002, -0.003, -0.004, -0.005, -0.006, -0.008, -0.010]  # 손절률 7개  
TTL_GRID_MIN = [5, 10, 15, 20, 30, 45, 60, 90, 120]  # 보유시간 9개 (분)
CONFIDENCE_GRID = [0.80, 0.85, 0.90, 0.95, 0.98]  # MTFA 신뢰도 임계값 5개
```

### 신뢰도 임계값 시스템
**신뢰도**: MTFA 4단계 분석으로 계산된 매수 신호의 확실성 (0-100%)
- **Level 1**: 15분봉 장기 추세 확인 (가중치 25%)
- **Level 2**: 5분봉 중기 모멘텀 확인 (가중치 30%)  
- **Level 3**: 1분봉 단기 진입 신호 (가중치 25%)
- **Level 4**: 시장 환경 체크 (가중치 20%)

**임계값 의미**:
- 90% 임계값 = "90% 이상 확실할 때만 매수"
- 각 코인별로 최적 임계값이 다름 (백테스팅으로 도출)

### 실제 사용 예시
```python
# 자동화 프로그램 적용
if coin == "KRW-BTC":
    익절률 = 0.012        # 1.2% (Excel에서 도출된 최적값)
    손절률 = -0.004       # -0.4%
    보유시간 = 35분        # 35분
    신뢰도임계값 = 0.90    # 90%
    
    # 실시간 거래 로직
    current_confidence = calculate_mtfa_confidence()
    if current_confidence >= 0.90:  # 신뢰도가 임계값 이상
        매수실행()
```

### Excel 출력 결과 구조
**시트명**: `코인별_매수매도_전략`
**컬럼들**:
- 최적_익절률: 이 코인의 최고 수익률을 위한 익절 기준 (예: 1.2%)
- 최적_손절률: 리스크 관리를 위한 손절 기준 (예: -0.4%)  
- 최적_보유시간_분: 최대 보유 시간 (예: 35분)
- 최적_신뢰도: MTFA 매수 신호 임계값 (예: 90%)
- 매수조건: "MTFA 90% 신뢰도 이상"
- 익절조건: "매수가 대비 +1.2% 도달시"
- 손절조건: "매수가 대비 -0.4% 도달시" 
- 시간제한: "매수 후 최대 35분 보유"

### 사용 방법
```bash
# Jupyter Notebook에서 실행
1. enhanced_mtfa_notebook_cell.py 전체 내용을 새 셀에 복사
2. 실행하면 MTFA_수익률_보장_최종결과.xlsx 파일 생성
3. Excel에서 각 코인별 최적 매수매도 전략 확인
4. 자동화 프로그램에 파라미터 바로 적용

# 예상 실행 시간: 2-3시간 (189개 코인 × 2,520조합 최적화)
```

### 🚨 중요 주의사항
- **전체 데이터 사용**: 마지막 데이터까지 완전 활용 (range(20, len(df) - 1))
- **모든 코인 분석**: 50개 이상 데이터가 있는 모든 코인 대상
- **제한사항 없음**: 인위적인 데이터 제한 완전 해제
- **수익률 보장**: 음수 수익률 코인은 결과에서 완전 제외
- **실용성 우선**: 자동화 프로그램에 바로 적용 가능한 구체적 파라미터 제공

### 핵심 가치
이 시스템은 "각 코인마다 다른 개성에 맞는 최적 매수매도 조건"을 찾아서 **자동화 프로그램의 수익률을 극대화**하는 것이 목적입니다. 단순한 분석이 아닌 **실제 적용 가능한 구체적 매매 전략**을 제공합니다.