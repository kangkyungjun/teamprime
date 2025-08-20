# 업비트 자동거래 시스템 v2.0 - 모듈화 버전

## 🏗️ 새로운 아키텍처

기존의 9,800라인 단일 파일을 기능별 모듈로 완전히 재구성했습니다.

## 📁 프로젝트 구조

```
teamprime/
├── main.py                    # 메인 애플리케이션 (200라인)
├── config.py                  # 시스템 설정
├── database.py               # 데이터베이스 연결
├── api_client.py             # API 클라이언트
├── data_analysis.py          # 데이터 분석 (임시)
│
└── core/                     # 핵심 모듈들
    ├── models/               # 데이터 모델
    │   ├── trading.py        # Position, TradingState
    │   └── response.py       # API 응답 모델
    │
    ├── services/             # 비즈니스 로직
    │   ├── trading_engine.py # 멀티코인 거래 엔진
    │   └── optimizer.py      # 자동 최적화 시스템
    │
    ├── api/                  # FastAPI 라우터
    │   ├── trading.py        # 거래 관련 엔드포인트
    │   ├── analysis.py       # 분석 관련 엔드포인트
    │   └── system.py         # 시스템 관련 엔드포인트
    │
    └── utils/                # 유틸리티 함수
        └── datetime_utils.py # 날짜/시간 처리
```

## 🚀 주요 개선사항

### 1. **가독성 향상**
- 9,800라인 → 모듈당 100-300라인
- 기능별 명확한 분리
- 체계적인 파일 구조

### 2. **유지보수성**
- 독립적인 모듈 수정 가능
- 명확한 의존성 관계
- 테스트 작성 용이

### 3. **재사용성**
- 모듈 간 명확한 인터페이스
- 다른 프로젝트에서 재사용 가능
- 확장성 고려한 설계

## 📦 핵심 모듈 설명

### `core.models`
거래 시스템의 핵심 데이터 구조
- `Position`: 거래 포지션 정보
- `TradingState`: 거래 상태 관리
- `CandleOut`: API 응답 모델

### `core.services`
핵심 비즈니스 로직
- `MultiCoinTradingEngine`: 멀티코인 동시 거래
- `WeeklyOptimizer`: 자동 최적화 시스템
- `AutoOptimizationScheduler`: 스케줄링

### `core.api`
REST API 엔드포인트
- `trading_router`: 거래 관련 API
- `analysis_router`: 분석 관련 API  
- `system_router`: 시스템 관리 API

### `core.utils`
공통 유틸리티 함수
- 날짜/시간 처리
- 데이터 변환
- 공통 헬퍼 함수

## 🔧 사용법

### 기본 실행
```bash
python main.py
```

### 개발 모드 (자동 리로드)
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 모듈별 테스트
```python
# 모델 테스트
from core.models import Position, TradingState

# 서비스 테스트  
from core.services import trading_engine, auto_scheduler

# API 테스트
from core.api import trading_router
```

## 📊 API 엔드포인트

### 거래 관련
- `POST /api/start-trading` - 자동거래 시작
- `POST /api/stop-trading` - 자동거래 중지
- `GET /api/trading-status` - 거래 상태 조회

### 분석 관련
- `GET /volume-surge-analysis` - 거래량 급증 분석
- `GET /backtest-performance` - 백테스트 성과
- `GET /multi-coin-analysis` - 멀티코인 분석

### 시스템 관련
- `GET /health` - 헬스 체크
- `GET /api/system-status` - 시스템 상태
- `POST /api/run-manual-optimization` - 수동 최적화

## 🔄 마이그레이션 가이드

### 기존 코드에서 모듈 사용
```python
# Before (기존)
from main import MultiCoinTradingEngine, trading_state

# After (새 구조)
from core.services import trading_engine, trading_state
```

### Import 경로 변경
```python
# 모델 import
from core.models import Position, TradingState, CandleOut

# 서비스 import
from core.services import trading_engine, auto_scheduler

# API 라우터 import
from core.api import trading_router, analysis_router, system_router

# 유틸리티 import
from core.utils import utc_now, parse_minutes_payload
```

## 🚨 중요 사항

### 1. **기존 기능 보존**
- 핵심 거래 알고리즘 그대로 유지
- 수익률 최적화 파라미터 보존
- 기존 API 호환성 유지

### 2. **점진적 마이그레이션**
- 일부 기능은 아직 기존 파일에 위치
- 단계적으로 모듈화 진행 예정
- 안정성 우선으로 이전

### 3. **테스트 필요**
- 각 모듈 독립 테스트
- 통합 테스트 실행
- 성능 검증 필요

## 🛠️ 개발 가이드

### 새 기능 추가
1. 적절한 모듈 디렉토리 선택
2. 인터페이스 정의
3. 테스트 코드 작성
4. 문서 업데이트

### 코딩 규칙
- 모듈당 300라인 이하 유지
- 명확한 import 경로 사용
- 타입 힌트 필수
- 로깅 적극 활용

## 📈 성능 비교

| 항목 | 기존 (단일파일) | 새 구조 (모듈화) |
|------|---------------|----------------|
| 코드 라인 | 9,800라인 | 200-300라인/모듈 |
| 가독성 | 낮음 | 높음 |
| 유지보수 | 어려움 | 쉬움 |
| 테스트 | 복잡 | 간단 |
| 확장성 | 제한적 | 높음 |

## 🎯 향후 계획

1. **Phase 2**: 데이터 분석 모듈 완전 분리
2. **Phase 3**: 백테스팅 시스템 모듈화
3. **Phase 4**: 프론트엔드 분리
4. **Phase 5**: 마이크로서비스 아키텍처