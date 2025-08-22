"""
🚀 Teamprime Mobile API Module

⚠️ 중요 안전 규칙:
1. 이 모듈은 기존 웹 시스템과 완전히 분리되어 있습니다.
2. 기존 core/ 모듈의 데이터는 읽기 전용으로만 접근합니다.
3. 기존 거래 엔진이나 데이터베이스를 수정하지 않습니다.
4. 독립된 포트(8002)에서 실행됩니다.

📱 모바일 API 모듈 구조:
- api/: 모바일 전용 API 엔드포인트
- services/: 데이터 어댑터 및 비즈니스 로직
- models/: 모바일 전용 데이터 모델
- mobile_main.py: 모바일 API 전용 서버

🛡️ 기존 시스템 보호:
모든 함수와 클래스는 기존 시스템의 데이터를 읽기만 하고,
절대로 수정하거나 변경하지 않습니다.
"""

__version__ = "1.0.0"
__author__ = "Teamprime Mobile Team"

# 모바일 API 버전 정보
MOBILE_API_VERSION = "v1"
MOBILE_API_PORT = 8002

# 기존 시스템과의 호환성 정보
CORE_SYSTEM_COMPATIBLE = True
READONLY_ACCESS_ONLY = True

# 안전성 플래그
SAFE_MODE = True  # 항상 True로 유지하여 기존 시스템 보호