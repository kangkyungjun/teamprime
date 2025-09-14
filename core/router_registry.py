"""
라우터 자동 등록 시스템
- API 라우터와 View 라우터를 자동으로 검색하고 등록
- main.py의 반복적인 라우터 등록 코드 제거
- 새로운 라우터 추가 시 자동 감지
"""

import importlib
import logging
from typing import Dict, List, Tuple, Optional
from fastapi import FastAPI
from fastapi.routing import APIRouter

logger = logging.getLogger(__name__)

class RouterConfig:
    """라우터 설정 정보"""

    def __init__(self, module_path: str, router_name: str = "router",
                 prefix: str = "", tags: Optional[List[str]] = None):
        self.module_path = module_path
        self.router_name = router_name
        self.prefix = prefix
        self.tags = tags or []

class RouterRegistry:
    """라우터 자동 등록 관리"""

    def __init__(self):
        self.api_routers: Dict[str, RouterConfig] = {}
        self.view_routers: Dict[str, RouterConfig] = {}
        self._setup_default_routers()

    def _setup_default_routers(self):
        """기본 라우터 설정"""

        # API 라우터 설정
        api_configs = [
            # 기본 API 라우터들
            ("trading", RouterConfig("core.api.trading", "router", "", ["Trading"])),
            ("analysis", RouterConfig("core.api.analysis", "router", "", ["Analysis"])),
            ("system", RouterConfig("core.api.system", "router", "", ["System"])),

            # 전문화된 API 라우터들
            ("resilience", RouterConfig("core.api.resilience", "router", "/api/resilience", ["Resilience"])),
            ("monitoring", RouterConfig("core.api.monitoring", "router", "/api/monitoring", ["Monitoring"])),
            ("auth", RouterConfig("core.api.auth", "router", "", ["Authentication"])),
            ("ux", RouterConfig("core.api.ux", "router", "/api/ux", ["User Experience"])),
            ("account", RouterConfig("core.api.account", "router", "/api/account", ["Account"])),
            ("trading_history", RouterConfig("core.api.trading_history", "router", "/api/trading-history", ["Trading History"])),
            ("business", RouterConfig("core.api.business", "router", "", ["Business"])),
            ("users", RouterConfig("core.api.users", "router", "", ["Users"])),
            ("analytics", RouterConfig("core.api.analytics", "router", "", ["Analytics"])),
            ("reports", RouterConfig("core.api.reports", "router", "", ["Reports"])),
            ("realtime", RouterConfig("core.api.realtime", "router", "/api/realtime", ["Real-time"])),
            ("mtfa", RouterConfig("core.api.mtfa", "router", "", ["MTFA"])),
        ]

        for name, config in api_configs:
            self.api_routers[name] = config

        # View 라우터 설정 (기존 네이밍 사용)
        view_configs = [
            ("main_views", RouterConfig("core.views.main_views", "main_views_router", "", ["Views"])),
            ("dashboard_views", RouterConfig("core.views.dashboard_views", "dashboard_views_router", "", ["Dashboard Views"])),
            ("auth_views", RouterConfig("core.views.auth_views", "auth_views_router", "", ["Auth Views"])),
            ("task_views", RouterConfig("core.views.task_views", "task_views_router", "", ["Task Views"])),
            ("analytics_views", RouterConfig("core.views.analytics_views", "analytics_views_router", "", ["Analytics Views"])),
            ("reports_views", RouterConfig("core.views.reports_views", "reports_views_router", "", ["Reports Views"])),
        ]

        for name, config in view_configs:
            self.view_routers[name] = config

    def _load_router(self, config: RouterConfig) -> Tuple[Optional[APIRouter], str]:
        """라우터 동적 로드"""
        try:
            module = importlib.import_module(config.module_path)
            router = getattr(module, config.router_name, None)

            if router is None:
                return None, f"Router '{config.router_name}' not found in {config.module_path}"

            if not isinstance(router, APIRouter):
                return None, f"'{config.router_name}' is not an APIRouter instance in {config.module_path}"

            return router, ""

        except ImportError as e:
            return None, f"Failed to import {config.module_path}: {str(e)}"
        except Exception as e:
            return None, f"Error loading router from {config.module_path}: {str(e)}"

    def register_api_routers(self, app: FastAPI) -> Dict[str, bool]:
        """API 라우터들을 FastAPI 앱에 등록"""
        results = {}

        logger.info(f"🔄 API 라우터 등록 시작 ({len(self.api_routers)}개)")

        for name, config in self.api_routers.items():
            router, error = self._load_router(config)

            if router:
                try:
                    app.include_router(
                        router,
                        prefix=config.prefix,
                        tags=config.tags
                    )
                    logger.info(f"✅ API 라우터 등록 완료: {name} ({config.prefix or '/'})")
                    results[name] = True
                except Exception as e:
                    logger.error(f"❌ API 라우터 등록 실패: {name} - {str(e)}")
                    results[name] = False
            else:
                logger.warning(f"⚠️ API 라우터 로드 실패: {name} - {error}")
                results[name] = False

        success_count = sum(results.values())
        logger.info(f"✅ API 라우터 등록 완료: {success_count}/{len(self.api_routers)}개 성공")

        return results

    def register_view_routers(self, app: FastAPI) -> Dict[str, bool]:
        """View 라우터들을 FastAPI 앱에 등록"""
        results = {}

        logger.info(f"🔄 View 라우터 등록 시작 ({len(self.view_routers)}개)")

        for name, config in self.view_routers.items():
            router, error = self._load_router(config)

            if router:
                try:
                    app.include_router(
                        router,
                        prefix=config.prefix,
                        tags=config.tags
                    )
                    logger.info(f"✅ View 라우터 등록 완료: {name}")
                    results[name] = True
                except Exception as e:
                    logger.error(f"❌ View 라우터 등록 실패: {name} - {str(e)}")
                    results[name] = False
            else:
                logger.warning(f"⚠️ View 라우터 로드 실패: {name} - {error}")
                results[name] = False

        success_count = sum(results.values())
        logger.info(f"✅ View 라우터 등록 완료: {success_count}/{len(self.view_routers)}개 성공")

        return results

    def register_all_routers(self, app: FastAPI) -> Dict[str, Dict[str, bool]]:
        """모든 라우터를 등록"""
        logger.info("🚀 전체 라우터 등록 시작")

        results = {
            "api": self.register_api_routers(app),
            "views": self.register_view_routers(app)
        }

        total_api = len(results["api"])
        success_api = sum(results["api"].values())
        total_views = len(results["views"])
        success_views = sum(results["views"].values())

        logger.info(f"🎯 라우터 등록 완료 - API: {success_api}/{total_api}, Views: {success_views}/{total_views}")

        return results

    def add_custom_router(self, name: str, config: RouterConfig, router_type: str = "api"):
        """커스텀 라우터 추가"""
        if router_type == "api":
            self.api_routers[name] = config
        elif router_type == "view":
            self.view_routers[name] = config
        else:
            raise ValueError(f"Invalid router type: {router_type}. Must be 'api' or 'view'")

        logger.info(f"📝 커스텀 라우터 추가: {name} ({router_type})")

# 전역 라우터 레지스트리 인스턴스
router_registry = RouterRegistry()