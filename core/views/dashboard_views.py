"""
대시보드 뷰 라우터
- 거래 대시보드
- MTFA 대시보드  
- 멀티 코인 대시보드
- 메인 대시보드 (비즈니스)
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)
dashboard_views_router = APIRouter()

@dashboard_views_router.get("/main-dashboard", response_class=HTMLResponse)
async def main_dashboard(request: Request):
    """비즈니스 관리 메인 대시보드로 리다이렉트"""
    from new_main_dashboard import business_main_dashboard
    return await business_main_dashboard(request)

@dashboard_views_router.get("/task-list", response_class=HTMLResponse)
async def task_list_page(request: Request):
    """업무 목록 페이지"""
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_role = current_user.get('role', 'user')
    
    # 실제 업무 목록을 표시하는 페이지
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>업무 목록 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root {{
                --md-primary: #1976d2;
                --md-secondary: #03dac6;
                --md-surface: #ffffff;
                --md-background: #f5f5f5;
                --md-elevation-1: 0 1px 3px rgba(0,0,0,0.12);
                --md-elevation-2: 0 2px 6px rgba(0,0,0,0.12);
                --md-elevation-3: 0 4px 12px rgba(0,0,0,0.15);
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 16px;
                padding-bottom: 100px; /* 하단 네비게이션 공간 확보 */
            }}
            
            .container {{
                max-width: 600px;
                margin: 0 auto;
            }}
            
            .header {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: var(--md-elevation-2);
            }}
            
            .header h1 {{
                margin: 0 0 8px 0;
                color: #333;
                font-size: 28px;
                font-weight: 700;
            }}
            
            .header .subtitle {{
                color: #666;
                margin: 0;
                font-size: 16px;
            }}
            
            .tasks-container {{
                display: flex;
                flex-direction: column;
                gap: 16px;
            }}
            
            .task-card {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                padding: 20px;
                box-shadow: var(--md-elevation-2);
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
                border-left: 4px solid var(--md-primary);
            }}
            
            .task-card:hover {{
                transform: translateY(-2px);
                box-shadow: var(--md-elevation-3);
            }}
            
            .task-header {{
                display: flex;
                justify-content: between;
                align-items: center;
                margin-bottom: 12px;
            }}
            
            .task-title {{
                font-size: 18px;
                font-weight: 600;
                color: #333;
                margin: 0;
                flex: 1;
            }}
            
            .task-status {{
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
            
            .status-pending {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .status-in-progress {{
                background: #cce5ff;
                color: #004085;
            }}
            
            .status-completed {{
                background: #d4edda;
                color: #155724;
            }}
            
            .task-description {{
                color: #666;
                font-size: 14px;
                margin-bottom: 12px;
                line-height: 1.4;
            }}
            
            .task-meta {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: #888;
            }}
            
            .task-date {{
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            
            .task-author {{
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            
            .task-priority {{
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            
            .priority-high {{
                color: #dc3545;
            }}
            
            .priority-medium {{
                color: #fd7e14;
            }}
            
            .priority-low {{
                color: #28a745;
            }}
            
            .loading {{
                text-align: center;
                padding: 40px;
                color: white;
            }}
            
            .empty-state {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                box-shadow: var(--md-elevation-2);
            }}
            
            .empty-state i {{
                font-size: 48px;
                color: #ccc;
                margin-bottom: 16px;
            }}
            
            .back-btn {{
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 56px;
                height: 56px;
                background: var(--md-primary);
                color: white;
                border: none;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                box-shadow: var(--md-elevation-3);
                cursor: pointer;
                transition: all 0.2s;
                text-decoration: none;
                z-index: 1000;
            }}
            
            .back-btn:hover {{
                transform: scale(1.1);
                color: white;
            }}
            
            /* Tabbar System */
            .app-bar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 60px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0 20px;
                z-index: 1000;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }}

            .app-bar .logo {{
                font-size: 20px;
                font-weight: bold;
                color: #333;
            }}

            .app-bar .menu-btn {{
                background: none;
                border: none;
                font-size: 24px;
                color: #333;
                cursor: pointer;
                padding: 8px;
                border-radius: 50%;
                transition: background-color 0.2s;
            }}

            .app-bar .menu-btn:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}

            .dropdown-menu {{
                position: fixed;
                top: 70px;
                right: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                padding: 8px 0;
                min-width: 180px;
                z-index: 1001;
                display: none;
            }}

            .dropdown-menu .menu-item {{
                padding: 12px 20px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            }}

            .dropdown-menu .menu-item:hover {{
                background-color: #f8f9fa;
            }}

            .dropdown-menu .menu-item:last-child {{
                border-bottom: none;
                color: #dc3545;
            }}

            .dropdown-menu .user-info {{
                padding: 15px 20px;
                border-bottom: 2px solid #e9ecef;
                background-color: #f8f9fa;
                border-radius: 12px 12px 0 0;
            }}

            .dropdown-menu .user-info .username {{
                font-weight: bold;
                color: #333;
                margin-bottom: 4px;
            }}

            .dropdown-menu .user-info .role {{
                font-size: 12px;
                color: #6c757d;
                text-transform: uppercase;
            }}

            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                display: flex;
                justify-content: space-around;
                align-items: center;
                z-index: 1000;
                box-shadow: 0 -2px 20px rgba(0, 0, 0, 0.1);
            }}

            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 8px 16px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                border-radius: 16px;
                position: relative;
                background: transparent;
                border: none;
                color: #666;
                font-family: inherit;
            }}

            .nav-item.active {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                transform: translateY(-4px);
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
            }}

            .nav-item:not(.active):hover {{
                background: rgba(102, 126, 234, 0.1);
                color: #667eea;
                transform: translateY(-2px);
            }}

            .nav-item i {{
                font-size: 20px;
                margin-bottom: 4px;
                transition: transform 0.3s ease;
            }}

            .nav-item.active i {{
                transform: scale(1.1);
            }}

            .nav-item span {{
                font-size: 12px;
                font-weight: 500;
                opacity: 0.9;
            }}

            .floating-sub-buttons {{
                position: fixed;
                bottom: 90px;
                left: 50%;
                transform: translateX(-50%);
                display: none;
                flex-direction: column;
                gap: 12px;
                z-index: 999;
                animation: slideUpFade 0.3s ease-out;
            }}

            @keyframes slideUpFade {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            .sub-button {{
                background: rgba(255, 255, 255, 0.95);
                border: none;
                border-radius: 16px;
                padding: 12px 20px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                backdrop-filter: blur(20px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                color: #333;
                font-weight: 500;
                font-size: 14px;
                min-width: 120px;
                text-align: center;
            }}

            .sub-button:hover {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
            }}

            /* 플로팅 서브 버튼 */
            .floating-sub-buttons {{
                position: fixed;
                bottom: 100px; /* 탭바(80px) 위쪽 20px */
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-radius: 25px;
                padding: 15px 25px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                z-index: 999;
                animation: slideUp 0.3s ease-out;
            }}
            
            .sub-button {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 15px 20px;
                border-radius: 18px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 70px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .sub-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .sub-button:active {{
                transform: translateY(-1px);
            }}
            
            .sub-icon {{
                font-size: 20px;
                margin-bottom: 4px;
            }}
            
            .sub-label {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid var(--md-outline);
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px; /* 하단 safe area 고려 */
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item:active {{
                transform: translateY(0);
                background: rgba(103, 80, 164, 0.12);
            }}
            
            .nav-item.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .nav-item.active:hover {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: var(--md-on-surface);
                text-align: center;
            }}

            /* 컨텐츠 영역 하단 패딩 (탭바 높이만큼) */
            .container {{
                padding-bottom: 100px;
            }}

            /* 태블릿 및 데스크톱에서 탭바 중앙 정렬 */
            @media (min-width: 768px) {{
                .bottom-nav {{
                    left: 50%;
                    transform: translateX(-50%);
                    width: 100%;
                    max-width: 800px;
                    border-radius: 20px 20px 0 0;
                }}
            }}

            /* 콘텐츠 영역 조정 (앱바 공간 확보) */
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
                padding: 80px 16px 100px 16px; /* 상단 앱바, 하단 탭바 공간 확보 */
            }}

            /* 필터/검색 영역 스타일 */
            .filter-search-section {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                padding: 20px;
                margin-bottom: 24px;
                box-shadow: var(--md-elevation-2);
                position: sticky;
                top: 16px;
                z-index: 100;
            }}
            
            .search-box {{
                position: relative;
                margin-bottom: 16px;
            }}
            
            .search-box input {{
                width: 100%;
                padding: 12px 16px 12px 45px;
                border: 2px solid #e0e0e0;
                border-radius: 25px;
                font-size: 16px;
                background: white;
                transition: all 0.2s;
            }}
            
            .search-box input:focus {{
                outline: none;
                border-color: var(--md-primary);
                box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
            }}
            
            .search-box i {{
                position: absolute;
                left: 16px;
                top: 50%;
                transform: translateY(-50%);
                color: #666;
                font-size: 16px;
            }}
            
            .filter-row {{
                display: flex;
                flex-direction: column;
                gap: 16px;
            }}
            
            .filter-group {{
                display: flex;
                flex-direction: column;
                gap: 8px;
            }}
            
            .filter-group label {{
                font-size: 14px;
                font-weight: 600;
                color: #333;
                margin: 0;
            }}
            
            .filter-buttons, .priority-filters {{
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            
            .filter-btn, .priority-btn {{
                padding: 8px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                background: white;
                color: #666;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
                white-space: nowrap;
            }}
            
            .filter-btn:hover, .priority-btn:hover {{
                border-color: var(--md-primary);
                color: var(--md-primary);
            }}
            
            .filter-btn.active, .priority-btn.active {{
                background: var(--md-primary);
                border-color: var(--md-primary);
                color: white;
            }}
            
            .author-select {{
                padding: 10px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                background: white;
                color: #333;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
                min-width: 150px;
            }}
            
            .author-select:focus {{
                outline: none;
                border-color: var(--md-primary);
                box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
            }}
            
            @media (min-width: 768px) {{
                .filter-row {{
                    flex-direction: row;
                    align-items: flex-start;
                }}
                
                .filter-group {{
                    flex: 1;
                    min-width: 0;
                }}
                
                .filter-search-section {{
                    top: 24px;
                }}
            }}
            
            /* 업무 상세보기 모달 스타일 */
            .task-detail-modal .modal-content {{
                border: none;
                border-radius: 20px;
                box-shadow: var(--md-elevation-3);
            }}
            
            .task-detail-modal .modal-header {{
                background: linear-gradient(135deg, var(--md-primary) 0%, #1565c0 100%);
                color: white;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: none;
            }}
            
            .task-detail-modal .modal-header .btn-close {{
                filter: invert(1);
            }}
            
            .task-detail-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            .task-detail-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                margin: 0;
                flex: 1;
            }}
            
            .task-detail-badges {{
                display: flex;
                gap: 8px;
            }}
            
            .task-detail-status, .task-detail-priority {{
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .task-detail-status.status-pending {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .task-detail-status.status-in-progress {{
                background: #cce5ff;
                color: #004085;
            }}
            
            .task-detail-status.status-completed {{
                background: #d4edda;
                color: #155724;
            }}
            
            .task-detail-priority.priority-high {{
                background: #f8d7da;
                color: #721c24;
            }}
            
            .task-detail-priority.priority-medium {{
                background: #fff3cd;
                color: #856404;
            }}
            
            .task-detail-priority.priority-low {{
                background: #d1ecf1;
                color: #0c5460;
            }}
            
            .task-detail-section {{
                margin-bottom: 24px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 16px;
                border-left: 4px solid var(--md-primary);
            }}
            
            .task-detail-section h6 {{
                color: var(--md-primary);
                font-weight: 600;
                margin-bottom: 12px;
                font-size: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .task-detail-description {{
                font-size: 16px;
                line-height: 1.6;
                color: #333;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            
            .task-meta-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 16px;
                margin-top: 16px;
            }}
            
            .task-meta-item {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px 16px;
                background: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }}
            
            .task-meta-item i {{
                width: 20px;
                text-align: center;
                color: var(--md-primary);
            }}
            
            .task-meta-label {{
                font-weight: 600;
                color: #666;
                min-width: 60px;
            }}
            
            .task-meta-value {{
                color: #333;
                flex: 1;
            }}
            
            .task-detail-empty {{
                text-align: center;
                padding: 40px 20px;
                color: #666;
            }}
            
            .task-detail-error {{
                text-align: center;
                padding: 40px 20px;
                color: #dc3545;
            }}
            
            @media (max-width: 768px) {{
                .task-detail-modal .modal-dialog {{
                    margin: 0.5rem;
                    max-width: calc(100% - 1rem);
                }}
                
                .task-detail-header {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 12px;
                }}
                
                .task-meta-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid var(--md-outline);
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px;
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item:active {{
                transform: translateY(0);
                background: rgba(103, 80, 164, 0.12);
            }}
            
            .nav-item.active {{
                background: rgba(103, 80, 164, 0.12);
                color: var(--md-primary);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: var(--md-on-surface);
                text-align: center;
            }}
            
            /* FAB 탭 (중앙) */
            .nav-fab {{
                background: linear-gradient(45deg, var(--md-primary), var(--md-secondary));
                border-radius: 20px;
                padding: 16px;
                transform: translateY(-8px);
                box-shadow: var(--md-elevation-3);
                min-width: 64px;
                height: 64px;
            }}
            
            .nav-fab:hover {{
                background: linear-gradient(45deg, var(--md-primary), var(--md-secondary));
                transform: translateY(-10px);
                box-shadow: var(--md-elevation-4);
            }}
            
            .nav-icon-fab {{
                font-size: 28px;
                color: var(--md-on-primary);
            }}
            
            /* 컨텐츠 영역 하단 패딩 (탭바 높이만큼) */
            body {{
                padding-bottom: 100px;
            }}
            
            /* 태블릿 및 데스크톱에서 탭바 중앙 정렬 */
            @media (min-width: 768px) {{
                .bottom-nav {{
                    left: 50%;
                    transform: translateX(-50%);
                    width: 100%;
                    max-width: 800px;
                    border-radius: 20px 20px 0 0;
                }}
            }}
            
            /* 빠른 업무 등록 모달 */
            .quick-task-modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }}
            
            .quick-task-content {{
                background-color: white;
                margin: 10% auto;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 500px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            
            .quick-task-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            .quick-task-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                margin: 0;
            }}
            
            .quick-form-group {{
                margin-bottom: 20px;
            }}
            
            .quick-form-label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #555;
            }}
            
            .quick-form-input {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }}
            
            .quick-form-input:focus {{
                outline: none;
                border-color: #667eea;
            }}
            
            .quick-form-select {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                box-sizing: border-box;
            }}
            
            .quick-form-textarea {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                resize: vertical;
                min-height: 100px;
                box-sizing: border-box;
            }}
            
            .quick-form-actions {{
                display: flex;
                gap: 10px;
                margin-top: 25px;
            }}
            
            .quick-btn {{
                flex: 1;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .quick-btn-cancel {{
                background-color: #f8f9fa;
                color: #6c757d;
                border: 2px solid #dee2e6;
            }}
            
            .quick-btn-cancel:hover {{
                background-color: #e9ecef;
                color: #5a6268;
            }}
            
            .quick-btn-save {{
                background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            
            .quick-btn-save:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}
            
            .quick-btn-save:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}
            
            /* 메뉴 모달 */
            .menu-modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }}
            
            .menu-content {{
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                background: white;
                border-radius: 20px 20px 0 0;
                max-height: 60vh;
                overflow-y: auto;
            }}
            
            .menu-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 24px;
                border-bottom: 1px solid var(--md-outline);
            }}
            
            .menu-title {{
                font-size: 20px;
                font-weight: 600;
                margin: 0;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 4px;
            }}
            
            .menu-items {{
                padding: 16px 0;
            }}
            
            .menu-item {{
                display: flex;
                align-items: center;
                padding: 16px 24px;
                text-decoration: none;
                color: var(--md-on-surface);
                transition: background-color 0.2s ease;
            }}
            
            .menu-item:hover {{
                background-color: var(--md-surface-variant);
                color: var(--md-on-surface);
            }}
            
            .menu-icon {{
                font-size: 20px;
                margin-right: 16px;
                min-width: 20px;
            }}
            
            .menu-text {{
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="logo">📋 업무 목록</div>
            <button class="menu-btn" onclick="toggleMenu()">☰</button>
        </div>

        <!-- 햄버거 메뉴 드롭다운 -->
        <div class="dropdown-menu" id="userDropdown">
            <div class="user-info">
                <div class="username">{username}</div>
                <div class="role">{user_role}</div>
            </div>
            <div class="menu-item" onclick="window.location.href='/profile'">👤 프로필</div>
            <div class="menu-item" onclick="window.location.href='/api-login'">🔑 API 설정</div>
            <div class="menu-item" onclick="window.location.href='/dashboard'">💰 거래 대시보드</div>
            <div class="menu-item" onclick="logout()">🚪 로그아웃</div>
        </div>

        <div class="container">
            
            <!-- 필터 및 검색 영역 -->
            <div class="filter-search-section">
                <div class="search-box">
                    <input type="text" placeholder="업무 제목이나 내용 검색..." id="searchInput">
                    <i class="fas fa-search"></i>
                </div>
                
                <div class="filter-row">
                    <div class="filter-group">
                        <label>상태</label>
                        <div class="filter-buttons">
                            <button class="filter-btn active" data-status="all">전체</button>
                            <button class="filter-btn" data-status="pending">대기</button>
                            <button class="filter-btn" data-status="in_progress">진행중</button>
                            <button class="filter-btn" data-status="completed">완료</button>
                        </div>
                    </div>
                    
                    <div class="filter-group">
                        <label>우선순위</label>
                        <div class="priority-filters">
                            <button class="priority-btn active" data-priority="all">전체</button>
                            <button class="priority-btn" data-priority="high">높음</button>
                            <button class="priority-btn" data-priority="medium">보통</button>
                            <button class="priority-btn" data-priority="low">낮음</button>
                        </div>
                    </div>
                    
                    <div class="filter-group">
                        <label>작성자</label>
                        <select id="authorFilter" class="author-select">
                            <option value="all">모든 작성자</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <div id="tasksContainer" class="tasks-container">
                <div class="loading">
                    <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                    <p>업무 목록을 불러오는 중...</p>
                </div>
            </div>
        </div>
        
        <!-- 업무 상세보기 모달 -->
        <div class="modal fade" id="taskDetailModal" tabindex="-1" aria-labelledby="taskDetailModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content task-detail-modal">
                    <div class="modal-header">
                        <h5 class="modal-title" id="taskDetailModalLabel">
                            <i class="fas fa-tasks me-2"></i>업무 상세
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="taskDetailContent">
                        <!-- 동적으로 업무 상세 정보가 표시됩니다 -->
                        <div class="text-center p-4">
                            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                            <p>업무 정보를 불러오는 중...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <!-- Action buttons for authorized users -->
                        <div id="taskActionButtons" class="me-auto" style="display: none;">
                            <button type="button" class="btn btn-warning me-2" onclick="editTask()">
                                <i class="fas fa-edit me-1"></i>수정
                            </button>
                            <button type="button" class="btn btn-danger me-2" onclick="deleteTask()">
                                <i class="fas fa-trash me-1"></i>삭제
                            </button>
                        </div>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i>닫기
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Edit Task Modal -->
        <div class="modal fade" id="editTaskModal" tabindex="-1" aria-labelledby="editTaskModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="editTaskModalLabel">
                            <i class="fas fa-edit me-2"></i>업무 수정
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editTaskForm">
                            <div class="mb-3">
                                <label for="editTaskTitle" class="form-label">
                                    <i class="fas fa-heading me-1"></i>제목 <span class="text-danger">*</span>
                                </label>
                                <input type="text" class="form-control" id="editTaskTitle" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="editTaskDescription" class="form-label">
                                    <i class="fas fa-align-left me-1"></i>설명
                                </label>
                                <textarea class="form-control" id="editTaskDescription" rows="4"></textarea>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="editTaskStatus" class="form-label">
                                        <i class="fas fa-flag me-1"></i>상태
                                    </label>
                                    <select class="form-select" id="editTaskStatus">
                                        <option value="대기">대기</option>
                                        <option value="진행중">진행중</option>
                                        <option value="완료">완료</option>
                                        <option value="보류">보류</option>
                                        <option value="취소">취소</option>
                                    </select>
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label for="editTaskPriority" class="form-label">
                                        <i class="fas fa-exclamation-circle me-1"></i>우선순위
                                    </label>
                                    <select class="form-select" id="editTaskPriority">
                                        <option value="low">낮음</option>
                                        <option value="medium">보통</option>
                                        <option value="high">높음</option>
                                        <option value="urgent">긴급</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="editTaskDueDate" class="form-label">
                                    <i class="fas fa-calendar-times me-1"></i>마감일
                                </label>
                                <input type="datetime-local" class="form-control" id="editTaskDueDate">
                            </div>
                            
                            <div class="mb-3">
                                <label for="editTaskAssignee" class="form-label">
                                    <i class="fas fa-user-check me-1"></i>담당자
                                </label>
                                <input type="text" class="form-control" id="editTaskAssignee" placeholder="담당자 이름">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-1"></i>취소
                        </button>
                        <button type="button" class="btn btn-primary" onclick="saveTaskChanges()">
                            <i class="fas fa-save me-1"></i>저장
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 하단 탭바 네비게이션 -->
        <div class="bottom-nav">
            <div class="nav-item active" onclick="navigateToTaskList()">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무 목록</div>
            </div>
            <div class="nav-item nav-fab" onclick="showQuickTaskModal()">
                <div class="nav-icon-fab">➕</div>
            </div>
            <div class="nav-item" onclick="navigateToProfitLoss()">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
            <div class="nav-item" onclick="showMenuModal()">
                <div class="nav-icon">☰</div>
                <div class="nav-label">메뉴</div>
            </div>
        </div>
        
        <!-- 빠른 업무 등록 모달 -->
        <div class="quick-task-modal" id="quickTaskModal">
            <div class="quick-task-content">
                <div class="quick-task-header">
                    <h3 class="quick-task-title">➕ 빠른 업무 등록</h3>
                    <button class="close-btn" onclick="hideQuickTaskModal()">&times;</button>
                </div>
                <form id="quickTaskForm">
                    <div class="quick-form-group">
                        <label class="quick-form-label">업무 제목 *</label>
                        <input type="text" class="quick-form-input" id="quickTaskTitle" 
                               placeholder="업무 제목을 입력하세요" maxlength="200" required>
                    </div>
                    <div class="quick-form-group">
                        <label class="quick-form-label">분야</label>
                        <select class="quick-form-select" id="quickTaskCategory">
                            <option value="기타">기타</option>
                            <option value="기획">기획</option>
                            <option value="개발">개발</option>
                            <option value="디자인">디자인</option>
                            <option value="운영">운영</option>
                            <option value="영업">영업</option>
                            <option value="고객지원">고객지원</option>
                            <option value="회계">회계</option>
                            <option value="법무">법무</option>
                            <option value="교육">교육</option>
                            <option value="유지보수">유지보수</option>
                        </select>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="quick-form-group">
                            <label class="quick-form-label">시작일</label>
                            <input type="date" class="quick-form-input" id="quickTaskStartDate">
                        </div>
                        <div class="quick-form-group">
                            <label class="quick-form-label">마감일</label>
                            <input type="date" class="quick-form-input" id="quickTaskEndDate">
                        </div>
                    </div>
                    <div class="quick-form-group">
                        <label class="quick-form-label">간단한 설명</label>
                        <textarea class="quick-form-textarea" id="quickTaskDescription" 
                                  placeholder="업무에 대한 간단한 설명을 입력하세요 (선택사항)"></textarea>
                    </div>
                    <div class="quick-form-actions">
                        <button type="button" class="quick-btn quick-btn-cancel" onclick="hideQuickTaskModal()">
                            취소
                        </button>
                        <button type="button" class="quick-btn quick-btn-save" onclick="saveQuickTask()">
                            등록하기
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- 메뉴 모달 -->
        <div class="menu-modal" id="menuModal">
            <div class="menu-content">
                <div class="menu-header">
                    <h3 class="menu-title">메뉴</h3>
                    <button class="close-btn" onclick="hideMenuModal()">&times;</button>
                </div>
                <div class="menu-items">
                    <a href="/main-dashboard" class="menu-item">
                        <div class="menu-icon">🏠</div>
                        <div class="menu-text">메인 대시보드</div>
                    </a>
                    <a href="/legacy-dashboard" class="menu-item">
                        <div class="menu-icon">📊</div>
                        <div class="menu-text">거래 대시보드</div>
                    </a>
                    {f'<a href="/users" class="menu-item"><div class="menu-icon">👥</div><div class="menu-text">사용자 관리</div></a>' if user_role in ['owner', 'prime'] else ''}
                    <a href="/profile" class="menu-item">
                        <div class="menu-icon">👤</div>
                        <div class="menu-text">프로필</div>
                    </a>
                    <div class="menu-item" onclick="logout()">
                        <div class="menu-icon">🚪</div>
                        <div class="menu-text">로그아웃</div>
                    </div>
                </div>
            </div>
        </div>
        
        <a href="/main-dashboard" class="back-btn" title="대시보드로 돌아가기" style="display: none;">
            <i class="fas fa-home"></i>
        </a>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // 전역 변수
            let allTasks = [];
            let filteredTasks = [];
            let allAuthors = new Set();
            let searchTimeout = null;
            
            // 현재 사용자 정보
            const currentUser = {{
                username: '{username}',
                role: '{user_role}',
                userId: {current_user.get('id', 'null')}
            }};
            
            document.addEventListener('DOMContentLoaded', function() {{
                loadTasks();
                initializeFilters();
            }});
            
            async function loadTasks() {{
                try {{
                    const response = await fetch('/api/business/tasks');
                    const data = await response.json();
                    
                    if (data.success && data.tasks && data.tasks.length > 0) {{
                        allTasks = data.tasks;
                        extractAuthorsFromTasks();
                        populateAuthorFilter();
                        filteredTasks = [...allTasks];
                        displayTasks(filteredTasks);
                    }} else {{
                        showEmptyState();
                    }}
                }} catch (error) {{
                    console.error('업무 목록 로딩 실패:', error);
                    showErrorState();
                }}
            }}
            
            function extractAuthorsFromTasks() {{
                allAuthors.clear();
                allTasks.forEach(task => {{
                    const author = task.author_name || task.created_by || task.username || '작성자 미상';
                    allAuthors.add(author);
                }});
            }}
            
            function populateAuthorFilter() {{
                const authorSelect = document.getElementById('authorFilter');
                // 기존 옵션들 제거 (첫 번째 "모든 작성자" 옵션 제외)
                while (authorSelect.children.length > 1) {{
                    authorSelect.removeChild(authorSelect.lastChild);
                }}
                
                // 작성자 옵션 추가
                Array.from(allAuthors).sort().forEach(author => {{
                    const option = document.createElement('option');
                    option.value = author;
                    option.textContent = author;
                    authorSelect.appendChild(option);
                }});
            }}
            
            function initializeFilters() {{
                // 검색창 이벤트
                const searchInput = document.getElementById('searchInput');
                searchInput.addEventListener('input', handleSearchInput);
                
                // 상태 필터 버튼들
                const filterBtns = document.querySelectorAll('.filter-btn');
                filterBtns.forEach(btn => {{
                    btn.addEventListener('click', function() {{
                        filterBtns.forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        filterTasks();
                    }});
                }});
                
                // 우선순위 필터 버튼들
                const priorityBtns = document.querySelectorAll('.priority-btn');
                priorityBtns.forEach(btn => {{
                    btn.addEventListener('click', function() {{
                        priorityBtns.forEach(b => b.classList.remove('active'));
                        this.classList.add('active');
                        filterTasks();
                    }});
                }});
                
                // 작성자 필터
                const authorSelect = document.getElementById('authorFilter');
                authorSelect.addEventListener('change', filterTasks);
            }}
            
            function handleSearchInput() {{
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {{
                    filterTasks();
                }}, 300); // 300ms 디바운싱
            }}
            
            function filterTasks() {{
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                const activeStatus = document.querySelector('.filter-btn.active').dataset.status;
                const activePriority = document.querySelector('.priority-btn.active').dataset.priority;
                const selectedAuthor = document.getElementById('authorFilter').value;
                
                filteredTasks = allTasks.filter(task => {{
                    // 검색어 필터링
                    const matchesSearch = searchTerm === '' || 
                        (task.title && task.title.toLowerCase().includes(searchTerm)) ||
                        (task.description && task.description.toLowerCase().includes(searchTerm));
                    
                    // 상태 필터링
                    const matchesStatus = activeStatus === 'all' || task.status === activeStatus;
                    
                    // 우선순위 필터링
                    const matchesPriority = activePriority === 'all' || 
                        (task.priority || 'medium') === activePriority;
                    
                    // 작성자 필터링
                    const taskAuthor = task.author_name || task.created_by || task.username || '작성자 미상';
                    const matchesAuthor = selectedAuthor === 'all' || taskAuthor === selectedAuthor;
                    
                    return matchesSearch && matchesStatus && matchesPriority && matchesAuthor;
                }});
                
                displayTasks(filteredTasks);
            }}
            
            function displayTasks(tasks) {{
                const container = document.getElementById('tasksContainer');
                
                if (!tasks || tasks.length === 0) {{
                    showEmptyState();
                    return;
                }}
                
                const tasksHtml = tasks.map(task => {{
                    const statusClass = getStatusClass(task.status);
                    const statusText = getStatusText(task.status);
                    const priorityClass = getPriorityClass(task.priority);
                    const priorityIcon = getPriorityIcon(task.priority);
                    
                    return `
                        <div class="task-card" onclick="viewTaskDetail(${{task.id}})">
                            <div class="task-header">
                                <h3 class="task-title">${{task.title || '제목 없음'}}</h3>
                                <span class="task-status ${{statusClass}}">${{statusText}}</span>
                            </div>
                            <div class="task-description">
                                ${{task.description || '설명이 없습니다.'}}
                            </div>
                            <div class="task-meta">
                                <div class="task-date">
                                    <i class="fas fa-calendar-alt"></i>
                                    <span>${{formatDate(task.created_at)}}</span>
                                </div>
                                <div class="task-author">
                                    <i class="fas fa-user"></i>
                                    <span>${{task.author_name || task.created_by || task.username || '작성자 미상'}}</span>
                                </div>
                                <div class="task-priority ${{priorityClass}}">
                                    <i class="${{priorityIcon}}"></i>
                                    <span>${{task.priority || '보통'}}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
                
                container.innerHTML = tasksHtml;
            }}
            
            function getStatusClass(status) {{
                switch(status) {{
                    case 'completed': return 'status-completed';
                    case 'in_progress': return 'status-in-progress';
                    default: return 'status-pending';
                }}
            }}
            
            function getStatusText(status) {{
                switch(status) {{
                    case 'completed': return '완료';
                    case 'in_progress': return '진행중';
                    default: return '대기';
                }}
            }}
            
            function getPriorityClass(priority) {{
                switch(priority) {{
                    case 'high': return 'priority-high';
                    case 'low': return 'priority-low';
                    default: return 'priority-medium';
                }}
            }}
            
            function getPriorityIcon(priority) {{
                switch(priority) {{
                    case 'high': return 'fas fa-exclamation-circle';
                    case 'low': return 'fas fa-minus-circle';
                    default: return 'fas fa-circle';
                }}
            }}
            
            function formatDate(dateString) {{
                if (!dateString) return '날짜 없음';
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR', {{
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                }});
            }}
            
            async function viewTaskDetail(taskId) {{
                try {{
                    showTaskDetailLoading();
                    showTaskDetailModal();
                    
                    const response = await fetch(`/api/business/tasks/${{taskId}}`);
                    const data = await response.json();
                    
                    if (data.success && data.task) {{
                        displayTaskDetail(data.task);
                    }} else {{
                        showTaskDetailError('업무 정보를 찾을 수 없습니다.');
                    }}
                }} catch (error) {{
                    console.error('업무 상세 로딩 실패:', error);
                    showTaskDetailError('업무 정보를 불러오는데 실패했습니다.');
                }}
            }}
            
            function showTaskDetailModal() {{
                const modal = new bootstrap.Modal(document.getElementById('taskDetailModal'));
                modal.show();
            }}
            
            function showTaskDetailLoading() {{
                const content = document.getElementById('taskDetailContent');
                content.innerHTML = `
                    <div class="text-center p-4">
                        <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                        <p>업무 정보를 불러오는 중...</p>
                    </div>
                `;
            }}
            
            function showTaskDetailError(message) {{
                const content = document.getElementById('taskDetailContent');
                content.innerHTML = `
                    <div class="task-detail-error">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                        <h5>오류 발생</h5>
                        <p>${{message}}</p>
                    </div>
                `;
            }}
            
            // 현재 작업 저장 (수정/삭제용)
            let currentTask = null;
            
            function displayTaskDetail(task) {{
                currentTask = task; // 현재 작업 저장
                
                const content = document.getElementById('taskDetailContent');
                
                // 상태 및 우선순위 배지 생성
                const statusBadge = getStatusBadgeHtml(task.status);
                const priorityBadge = getPriorityBadgeHtml(task.priority || 'medium');
                
                content.innerHTML = `
                    <div class="task-detail-header">
                        <h2 class="task-detail-title">${{task.title || '제목 없음'}}</h2>
                        <div class="task-detail-badges">
                            ${{statusBadge}}
                            ${{priorityBadge}}
                        </div>
                    </div>
                    
                    <div class="task-detail-section">
                        <h6><i class="fas fa-align-left"></i>업무 설명</h6>
                        <div class="task-detail-description">
                            ${{task.description || '설명이 없습니다.'}}
                        </div>
                    </div>
                    
                    <div class="task-detail-section">
                        <h6><i class="fas fa-info-circle"></i>상세 정보</h6>
                        <div class="task-meta-grid">
                            <div class="task-meta-item">
                                <i class="fas fa-calendar-plus"></i>
                                <span class="task-meta-label">생성일:</span>
                                <span class="task-meta-value">${{formatTaskDetailDate(task.created_at)}}</span>
                            </div>
                            <div class="task-meta-item">
                                <i class="fas fa-user-edit"></i>
                                <span class="task-meta-label">작성자:</span>
                                <span class="task-meta-value">${{task.creator_name || task.created_by || '작성자 미상'}}</span>
                            </div>
                            ${{task.assignee_name ? `
                                <div class="task-meta-item">
                                    <i class="fas fa-user-check"></i>
                                    <span class="task-meta-label">담당자:</span>
                                    <span class="task-meta-value">${{task.assignee_name}}</span>
                                </div>
                            ` : ''}}
                            ${{task.due_date ? `
                                <div class="task-meta-item">
                                    <i class="fas fa-calendar-times"></i>
                                    <span class="task-meta-label">마감일:</span>
                                    <span class="task-meta-value">${{formatTaskDetailDate(task.due_date)}}</span>
                                </div>
                            ` : ''}}
                            ${{task.updated_at ? `
                                <div class="task-meta-item">
                                    <i class="fas fa-clock"></i>
                                    <span class="task-meta-label">최종수정:</span>
                                    <span class="task-meta-value">${{formatTaskDetailDate(task.updated_at)}}</span>
                                </div>
                            ` : ''}}
                            <div class="task-meta-item">
                                <i class="fas fa-hashtag"></i>
                                <span class="task-meta-label">업무 ID:</span>
                                <span class="task-meta-value">#${{task.id}}</span>
                            </div>
                        </div>
                    </div>
                `;
                
                // 권한 확인 후 액션 버튼 표시/숨김
                const actionButtons = document.getElementById('taskActionButtons');
                if (hasEditPermission(task)) {{
                    actionButtons.style.display = 'block';
                }} else {{
                    actionButtons.style.display = 'none';
                }}
            }}
            
            // 편집 권한 확인 함수
            function hasEditPermission(task) {{
                // Owner나 Prime은 모든 작업을 편집 가능
                if (currentUser.role === 'owner' || currentUser.role === 'prime') {{
                    return true;
                }}
                
                // 작성자 본인인 경우 편집 가능
                const taskAuthor = task.created_by || task.creator_name || '';
                const taskCreatorId = task.creator_id || task.created_by_id || null;
                
                // 사용자명으로 비교하거나 ID로 비교
                return taskAuthor === currentUser.username || 
                       taskCreatorId === currentUser.userId;
            }}
            
            function getStatusBadgeHtml(status) {{
                const statusText = getStatusText(status);
                const statusClass = getStatusClass(status);
                return `<span class="task-detail-status ${{statusClass}}">${{statusText}}</span>`;
            }}
            
            function getPriorityBadgeHtml(priority) {{
                const priorityText = getPriorityText(priority);
                const priorityClass = getPriorityClass(priority);
                return `<span class="task-detail-priority ${{priorityClass}}">${{priorityText}}</span>`;
            }}
            
            function getPriorityText(priority) {{
                switch(priority) {{
                    case 'high': return '높음';
                    case 'low': return '낮음';
                    default: return '보통';
                }}
            }}
            
            function formatTaskDetailDate(dateString) {{
                if (!dateString) return '날짜 없음';
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR', {{
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    weekday: 'short',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
            }}
            
            function showEmptyState() {{
                const container = document.getElementById('tasksContainer');
                
                // 필터링 중인지 확인
                const searchTerm = document.getElementById('searchInput').value;
                const activeStatus = document.querySelector('.filter-btn.active').dataset.status;
                const activePriority = document.querySelector('.priority-btn.active').dataset.priority;
                const selectedAuthor = document.getElementById('authorFilter').value;
                
                const isFiltering = searchTerm || activeStatus !== 'all' || activePriority !== 'all' || selectedAuthor !== 'all';
                
                if (isFiltering) {{
                    // 필터링 결과가 없을 때
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-search"></i>
                            <h3>검색 결과가 없습니다</h3>
                            <p>다른 검색어나 필터 조건을 사용해보세요.</p>
                            <button class="btn btn-outline-primary mt-2" onclick="clearFilters()">필터 초기화</button>
                        </div>
                    `;
                }} else {{
                    // 업무가 전혀 없을 때
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-clipboard-list"></i>
                            <h3>등록된 업무가 없습니다</h3>
                            <p>하단의 ➕ 버튼을 눌러 새로운 업무를 등록해보세요!</p>
                        </div>
                    `;
                }}
            }}
            
            function clearFilters() {{
                // 검색창 초기화
                document.getElementById('searchInput').value = '';
                
                // 상태 필터 초기화
                document.querySelectorAll('.filter-btn').forEach(btn => {{
                    btn.classList.remove('active');
                    if (btn.dataset.status === 'all') {{
                        btn.classList.add('active');
                    }}
                }});
                
                // 우선순위 필터 초기화
                document.querySelectorAll('.priority-btn').forEach(btn => {{
                    btn.classList.remove('active');
                    if (btn.dataset.priority === 'all') {{
                        btn.classList.add('active');
                    }}
                }});
                
                // 작성자 필터 초기화
                document.getElementById('authorFilter').value = 'all';
                
                // 필터 적용
                filterTasks();
            }}
            
            function showErrorState() {{
                const container = document.getElementById('tasksContainer');
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle text-warning"></i>
                        <h3>업무 목록을 불러올 수 없습니다</h3>
                        <p>잠시 후 다시 시도해주세요.</p>
                    </div>
                `;
            }}
            
            // 업무 수정 함수
            function editTask() {{
                if (!currentTask) {{
                    alert('수정할 업무를 선택해주세요.');
                    return;
                }}
                
                // 폼에 현재 데이터 채우기
                document.getElementById('editTaskTitle').value = currentTask.title || '';
                document.getElementById('editTaskDescription').value = currentTask.description || '';
                document.getElementById('editTaskStatus').value = currentTask.status || '대기';
                document.getElementById('editTaskPriority').value = currentTask.priority || 'medium';
                document.getElementById('editTaskAssignee').value = currentTask.assignee_name || '';
                
                // 마감일 처리 (ISO 형식으로 변환)
                if (currentTask.due_date) {{
                    const dueDate = new Date(currentTask.due_date);
                    if (!isNaN(dueDate.getTime())) {{
                        // datetime-local input 형식에 맞게 변환 (YYYY-MM-DDTHH:MM)
                        const year = dueDate.getFullYear();
                        const month = String(dueDate.getMonth() + 1).padStart(2, '0');
                        const day = String(dueDate.getDate()).padStart(2, '0');
                        const hours = String(dueDate.getHours()).padStart(2, '0');
                        const minutes = String(dueDate.getMinutes()).padStart(2, '0');
                        document.getElementById('editTaskDueDate').value = `${{year}}-${{month}}-${{day}}T${{hours}}:${{minutes}}`;
                    }}
                }}
                
                // 수정 모달 표시
                const editModal = new bootstrap.Modal(document.getElementById('editTaskModal'));
                editModal.show();
            }}
            
            // 업무 저장 함수
            async function saveTaskChanges() {{
                if (!currentTask) {{
                    alert('저장할 업무를 찾을 수 없습니다.');
                    return;
                }}
                
                const form = document.getElementById('editTaskForm');
                if (!form.checkValidity()) {{
                    form.reportValidity();
                    return;
                }}
                
                const formData = {{
                    title: document.getElementById('editTaskTitle').value.trim(),
                    description: document.getElementById('editTaskDescription').value.trim(),
                    status: document.getElementById('editTaskStatus').value
                }};
                
                // 담당자 처리 - 현재는 이름만 저장하므로 assignee_id는 null로 설정
                const assigneeName = document.getElementById('editTaskAssignee').value.trim();
                if (assigneeName) {{
                    // TODO: 실제로는 사용자 검색하여 assignee_id를 설정해야 함
                    formData.assignee_id = null; // 일단 null로 설정
                }}
                
                // 마감일 처리 - API는 end_date를 기대
                const dueDateValue = document.getElementById('editTaskDueDate').value;
                if (dueDateValue) {{
                    const endDate = new Date(dueDateValue).toISOString().split('T')[0];
                    formData.end_date = endDate;
                }}
                
                try {{
                    const response = await fetch(`/api/business/tasks/${{currentTask.id}}`, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(formData)
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        // 수정 성공
                        alert('업무가 성공적으로 수정되었습니다.');
                        
                        // 모달 닫기
                        const editModal = bootstrap.Modal.getInstance(document.getElementById('editTaskModal'));
                        editModal.hide();
                        
                        // 상세 모달도 닫기
                        const detailModal = bootstrap.Modal.getInstance(document.getElementById('taskDetailModal'));
                        detailModal.hide();
                        
                        // 목록 새로고침
                        loadTasks();
                    }} else {{
                        alert(result.message || '업무 수정에 실패했습니다.');
                    }}
                }} catch (error) {{
                    console.error('업무 수정 오류:', error);
                    alert('업무 수정 중 오류가 발생했습니다.');
                }}
            }}
            
            // 업무 삭제 함수
            async function deleteTask() {{
                if (!currentTask) {{
                    alert('삭제할 업무를 선택해주세요.');
                    return;
                }}
                
                if (!confirm(`업무 "${{currentTask.title}}"를 정말로 삭제하시겠습니까?\\n\\n이 작업은 되돌릴 수 없습니다.`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/api/business/tasks/${{currentTask.id}}`, {{
                        method: 'DELETE'
                    }});
                    
                    const result = await response.json();
                    
                    if (result.success) {{
                        // 삭제 성공
                        alert('업무가 성공적으로 삭제되었습니다.');
                        
                        // 상세 모달 닫기
                        const detailModal = bootstrap.Modal.getInstance(document.getElementById('taskDetailModal'));
                        detailModal.hide();
                        
                        // 목록 새로고침
                        loadTasks();
                    }} else {{
                        alert(result.message || '업무 삭제에 실패했습니다.');
                    }}
                }} catch (error) {{
                    console.error('업무 삭제 오류:', error);
                    alert('업무 삭제 중 오류가 발생했습니다.');
                }}
            }}
            
            // 탭 네비게이션 함수들
            function navigateToTaskList() {{
                // 이미 업무 목록 페이지에 있으므로 아무것도 하지 않음
                console.log('이미 업무 목록 페이지입니다');
            }}
            
            function navigateToProfitLoss() {{
                window.location.href = '/main-dashboard';
            }}
            
            // 빠른 업무 등록 모달 관련 함수들
            function showQuickTaskModal() {{
                const modal = document.getElementById('quickTaskModal');
                modal.style.display = 'block';
                // 폼 리셋
                document.getElementById('quickTaskForm').reset();
            }}
            
            function hideQuickTaskModal() {{
                const modal = document.getElementById('quickTaskModal');
                modal.style.display = 'none';
            }}
            
            async function saveQuickTask() {{
                const title = document.getElementById('quickTaskTitle').value.trim();
                const startDate = document.getElementById('quickTaskStartDate').value;
                const endDate = document.getElementById('quickTaskEndDate').value;
                
                if (!title) {{
                    alert('업무 제목을 입력해주세요.');
                    document.getElementById('quickTaskTitle').focus();
                    return;
                }}
                
                if (title.length > 200) {{
                    alert('업무 제목은 200자를 초과할 수 없습니다.');
                    document.getElementById('quickTaskTitle').focus();
                    return;
                }}
                
                // 날짜 유효성 검사
                if (startDate && endDate && new Date(startDate) > new Date(endDate)) {{
                    alert('시작일은 마감일보다 늦을 수 없습니다.');
                    document.getElementById('quickTaskStartDate').focus();
                    return;
                }}
                
                const taskData = {{
                    title: title,
                    category: document.getElementById('quickTaskCategory').value,
                    description: document.getElementById('quickTaskDescription').value.trim(),
                    start_date: startDate || null,
                    end_date: endDate || null
                }};
                
                const saveBtn = document.querySelector('.quick-btn-save');
                const originalText = saveBtn.textContent;
                saveBtn.disabled = true;
                saveBtn.textContent = '등록 중...';
                
                try {{
                    const response = await fetch('/api/business/tasks', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(taskData)
                    }});
                    
                    if (response.ok) {{
                        const result = await response.json();
                        alert('✅ 업무가 성공적으로 등록되었습니다!');
                        hideQuickTaskModal();
                        loadTasks();
                        
                        // 폼 리셋
                        document.getElementById('quickTaskForm').reset();
                    }} else {{
                        const errorData = await response.json();
                        alert('❌ ' + (errorData.detail || '업무 등록에 실패했습니다.'));
                    }}
                }} catch (error) {{
                    console.error('업무 등록 오류:', error);
                    alert('❌ 서버 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
                }} finally {{
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }}
            }}
            
            // 메뉴 모달 관련 함수들
            function showMenuModal() {{
                const modal = document.getElementById('menuModal');
                modal.style.display = 'block';
            }}
            
            function hideMenuModal() {{
                const modal = document.getElementById('menuModal');
                modal.style.display = 'none';
            }}
            
            function logout() {{
                if (confirm('정말로 로그아웃 하시겠습니까?')) {{
                    window.location.href = '/api/auth/logout';
                }}
            }}
            
            // 모달 배경 클릭시 닫기
            document.addEventListener('click', function(event) {{
                const quickTaskModal = document.getElementById('quickTaskModal');
                const menuModal = document.getElementById('menuModal');
                
                if (event.target === quickTaskModal) {{
                    hideQuickTaskModal();
                }}
                
                if (event.target === menuModal) {{
                    hideMenuModal();
                }}
            }});

            // 탭 선택 및 서브 버튼 제어 시스템
            let currentTab = 'task'; // 업무 페이지이므로 기본적으로 task 탭 활성화

            function selectTab(tabType) {{
                // 이미 선택된 탭을 다시 누르면 서브 버튼 숨김
                if (currentTab === tabType) {{
                    hideSubButtons();
                    return;
                }}
                
                currentTab = tabType;
                
                if (tabType === 'task') {{
                    // 업무 탭 선택
                    showSubButtons('📋', '업무 목록', '➕', '업무 등록', 
                                  'refreshTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    // 손익 탭 선택
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showExpenseModal()');
                    updateTabState('profit');
                }}
            }}
            
            function showSubButtons(icon1, label1, icon2, label2, action1, action2) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const button1 = document.getElementById('subButton1');
                const button2 = document.getElementById('subButton2');
                const icon1El = document.getElementById('subIcon1');
                const label1El = document.getElementById('subLabel1');
                const icon2El = document.getElementById('subIcon2');
                const label2El = document.getElementById('subLabel2');
                
                // 서브 버튼 내용 설정
                icon1El.textContent = icon1;
                label1El.textContent = label1;
                icon2El.textContent = icon2;
                label2El.textContent = label2;
                
                // 클릭 이벤트 설정
                button1.onclick = () => eval(action1);
                button2.onclick = () => eval(action2);
                
                // 애니메이션과 함께 표시
                subButtons.style.display = 'flex';
                setTimeout(() => {{
                    subButtons.style.animation = 'slideUp 0.3s ease-out';
                }}, 10);
            }}
            
            function hideSubButtons() {{
                const subButtons = document.getElementById('floatingSubButtons');
                subButtons.style.display = 'none';
                currentTab = null;
                updateTabState(null);
            }}
            
            function updateTabState(activeTab) {{
                // 모든 탭에서 active 클래스 제거
                document.getElementById('taskTab').classList.remove('active');
                document.getElementById('profitTab').classList.remove('active');
                
                // 선택된 탭에 active 클래스 추가
                if (activeTab === 'task') {{
                    document.getElementById('taskTab').classList.add('active');
                }} else if (activeTab === 'profit') {{
                    document.getElementById('profitTab').classList.add('active');
                }}
            }}

            function navigateToTaskList() {{
                window.location.href = '/task-list';
            }}
            
            function refreshTaskList() {{
                // 업무 목록으로 이동 (다른 페이지에서)
                window.location.href = '/task-list';
            }}

            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}

            function showExpenseModal() {{
                // 손익 등록 모달 (향후 구현)
                alert('손익 등록 기능은 손익 페이지에서 이용하세요');
            }}

            // 햄버거 메뉴 토글 함수
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                const isVisible = dropdown.style.display === 'block';
                dropdown.style.display = isVisible ? 'none' : 'block';
                
                if (!isVisible) {{
                    setTimeout(() => {{
                        document.addEventListener('click', closeMenuOnOutsideClick);
                    }}, 100);
                }}
            }}

            function closeMenuOnOutsideClick(event) {{
                const dropdown = document.getElementById('userDropdown');
                const menuBtn = document.querySelector('.menu-btn');
                
                if (!dropdown.contains(event.target) && !menuBtn.contains(event.target)) {{
                    dropdown.style.display = 'none';
                    document.removeEventListener('click', closeMenuOnOutsideClick);
                }}
            }}

            // 로그아웃 함수
            function logout() {{
                if (confirm('정말로 로그아웃 하시겠습니까?')) {{
                    window.location.href = '/api/auth/logout';
                }}
            }}

            // 화면 다른 곳 클릭 시 서브 버튼 숨김
            document.addEventListener('click', function(event) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const bottomNav = document.querySelector('.bottom-nav');
                
                if (currentTab && subButtons.style.display === 'flex') {{
                    // 서브 버튼이나 탭바가 아닌 곳을 클릭한 경우
                    if (!subButtons.contains(event.target) && !bottomNav.contains(event.target)) {{
                        hideSubButtons();
                    }}
                }}
            }});

            // 페이지 로드시 업무 탭을 활성 상태로 설정
            document.addEventListener('DOMContentLoaded', function() {{
                updateTabState('task'); // 업무 페이지이므로 task 탭 활성화
            }});
        </script>

        <!-- 플로팅 서브 버튼 (탭바 위쪽) -->
        <div class="floating-sub-buttons" id="floatingSubButtons" style="display: none;">
            <div class="sub-button" id="subButton1" onclick="">
                <div class="sub-icon" id="subIcon1">📋</div>
                <div class="sub-label" id="subLabel1">목록</div>
            </div>
            <div class="sub-button" id="subButton2" onclick="">
                <div class="sub-icon" id="subIcon2">➕</div>
                <div class="sub-label" id="subLabel2">등록</div>
            </div>
        </div>

        <!-- 하단 탭바 네비게이션 (2개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item active" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@dashboard_views_router.get("/profit-loss", response_class=HTMLResponse)
async def profit_loss_page(request: Request):
    """손익 관리 통합 페이지 (지출/수익/분석 통합)"""
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_role = current_user.get('role', 'user')
    
    # 실제 손익 관리 페이지 템플릿
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>손익 관리 - Teamprime</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root {{
                --md-primary: #6750A4;
                --md-on-primary: #FFFFFF;
                --md-primary-container: #E9DDFF;
                --md-on-primary-container: #22005D;
                --md-secondary: #625B71;
                --md-on-secondary: #FFFFFF;
                --md-surface: #FFFBFF;
                --md-on-surface: #1C1B1E;
                --md-surface-variant: #E7E0EC;
                --md-outline: #79747E;
                --md-background: #FFFBFF;
                --md-shadow: rgba(0, 0, 0, 0.15);
                --md-elevation-1: 0 1px 2px var(--md-shadow);
                --md-elevation-2: 0 1px 3px 1px var(--md-shadow);
                --md-elevation-3: 0 4px 8px 3px var(--md-shadow);
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Roboto', 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: var(--md-on-surface);
                padding-bottom: 20px;
            }}
            
            .app-bar {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                padding: 0 20px;
                height: 64px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: var(--md-elevation-2);
                position: sticky;
                top: 0;
                z-index: 1000;
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
            }}
            
            .back-btn {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 14px;
            }}
            
            .back-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}

            /* Tabbar System Additions */
            .app-bar .menu-btn {{
                background: none;
                border: none;
                font-size: 24px;
                color: #333;
                cursor: pointer;
                padding: 8px;
                border-radius: 50%;
                transition: background-color 0.2s;
            }}

            .app-bar .menu-btn:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}

            .dropdown-menu {{
                position: fixed;
                top: 74px;
                right: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                padding: 8px 0;
                min-width: 180px;
                z-index: 1001;
                display: none;
            }}

            .dropdown-menu .menu-item {{
                padding: 12px 20px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            }}

            .dropdown-menu .menu-item:hover {{
                background-color: #f8f9fa;
            }}

            .dropdown-menu .menu-item:last-child {{
                border-bottom: none;
                color: #dc3545;
            }}

            .dropdown-menu .user-info {{
                padding: 15px 20px;
                border-bottom: 2px solid #e9ecef;
                background-color: #f8f9fa;
                border-radius: 12px 12px 0 0;
            }}

            .dropdown-menu .user-info .username {{
                font-weight: bold;
                color: #333;
                margin-bottom: 4px;
            }}

            .dropdown-menu .user-info .role {{
                font-size: 12px;
                color: #6c757d;
                text-transform: uppercase;
            }}

            /* 플로팅 서브 버튼 */
            .floating-sub-buttons {{
                position: fixed;
                bottom: 100px; /* 탭바(80px) 위쪽 20px */
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-radius: 25px;
                padding: 15px 25px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                z-index: 999;
                animation: slideUp 0.3s ease-out;
            }}
            
            .sub-button {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 15px 20px;
                border-radius: 18px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 70px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .sub-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .sub-button:active {{
                transform: translateY(-1px);
            }}
            
            .sub-icon {{
                font-size: 20px;
                margin-bottom: 4px;
            }}
            
            .sub-label {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid var(--md-outline);
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px; /* 하단 safe area 고려 */
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item:active {{
                transform: translateY(0);
                background: rgba(103, 80, 164, 0.12);
            }}
            
            .nav-item.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .nav-item.active:hover {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: var(--md-on-surface);
                text-align: center;
            }}

            /* 태블릿 및 데스크톱에서 탭바 중앙 정렬 */
            @media (min-width: 768px) {{
                .bottom-nav {{
                    left: 50%;
                    transform: translateX(-50%);
                    width: 100%;
                    max-width: 800px;
                    border-radius: 20px 20px 0 0;
                }}
            }}
            
            .main-content {{
                padding: 20px 20px 100px 20px; /* 하단 탭바 공간 확보 */
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            /* 요약 카드 */
            .summary-section {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .summary-card {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 16px;
                padding: 24px;
                box-shadow: var(--md-elevation-2);
                text-align: center;
            }}
            
            .summary-icon {{
                font-size: 32px;
                margin-bottom: 12px;
            }}
            
            .summary-title {{
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .summary-amount {{
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 4px;
            }}
            
            .income {{
                color: #4caf50;
            }}
            
            .expense {{
                color: #f44336;
            }}
            
            .profit {{
                color: #2196f3;
            }}
            
            /* 필터 섹션 */
            .filter-section {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: var(--md-elevation-1);
            }}
            
            .filter-title {{
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 15px;
            }}
            
            .filter-row {{
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
                align-items: center;
            }}
            
            .filter-group {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            
            .filter-label {{
                font-size: 12px;
                font-weight: 600;
                color: #666;
            }}
            
            .filter-select {{
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                min-width: 120px;
            }}
            
            .filter-btn {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }}
            
            .filter-btn:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }}
            
            /* 리스트 섹션 */
            .list-section {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 16px;
                padding: 20px;
                box-shadow: var(--md-elevation-1);
            }}
            
            .list-title {{
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .list-container {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            
            .list-item {{
                background: #f8f9fa;
                border-radius: 12px;
                padding: 16px;
                border-left: 4px solid #ddd;
                transition: all 0.2s;
                cursor: pointer;
            }}
            
            .list-item:hover {{
                background: #e9ecef;
                transform: translateX(4px);
            }}
            
            .list-item.expense {{
                border-left-color: #f44336;
            }}
            
            .list-item.income {{
                border-left-color: #4caf50;
            }}
            
            .item-header {{
                display: flex;
                justify-content: between;
                align-items: flex-start;
                margin-bottom: 8px;
            }}
            
            .item-title {{
                font-weight: 600;
                font-size: 16px;
                color: #333;
            }}
            
            .item-amount {{
                font-weight: 700;
                font-size: 18px;
                margin-left: auto;
            }}
            
            .item-meta {{
                display: flex;
                gap: 15px;
                font-size: 14px;
                color: #666;
                margin-top: 8px;
            }}
            
            .meta-item {{
                display: flex;
                align-items: center;
                gap: 4px;
            }}
            
            .task-tag {{
                background: #e3f2fd;
                color: #1976d2;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            
            .category-tag {{
                background: #fff3e0;
                color: #f57c00;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            
            /* 로딩 상태 */
            .loading {{
                text-align: center;
                padding: 40px;
                color: #666;
            }}
            
            .spinner {{
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            .empty-state {{
                text-align: center;
                padding: 60px 20px;
                color: #666;
            }}
            
            .empty-icon {{
                font-size: 64px;
                margin-bottom: 20px;
                opacity: 0.5;
            }}
            
            /* 반응형 디자인 */
            @media (max-width: 768px) {{
                .main-content {{
                    padding: 15px;
                }}
                
                .summary-section {{
                    grid-template-columns: 1fr;
                }}
                
                .filter-row {{
                    flex-direction: column;
                    align-items: stretch;
                }}
                
                .filter-group {{
                    width: 100%;
                }}
                
                .item-header {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 8px;
                }}
                
                .item-amount {{
                    margin-left: 0;
                }}
                
                .item-meta {{
                    flex-wrap: wrap;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="app-title">💰 손익 관리</div>
            <button class="menu-btn" onclick="toggleMenu()">☰</button>
        </div>

        <!-- 햄버거 메뉴 드롭다운 -->
        <div class="dropdown-menu" id="userDropdown">
            <div class="user-info">
                <div class="username">{username}</div>
                <div class="role">{user_role}</div>
            </div>
            <div class="menu-item" onclick="window.location.href='/profile'">👤 프로필</div>
            <div class="menu-item" onclick="window.location.href='/api-login'">🔑 API 설정</div>
            <div class="menu-item" onclick="window.location.href='/dashboard'">💰 거래 대시보드</div>
            <div class="menu-item" onclick="logout()">🚪 로그아웃</div>
        </div>
        
        <!-- 메인 컨텐츠 -->
        <div class="main-content">
            <!-- 요약 섹션 -->
            <div class="summary-section">
                <div class="summary-card">
                    <div class="summary-icon">💰</div>
                    <div class="summary-title">총 수익</div>
                    <div class="summary-amount income" id="totalIncome">₩0</div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">💳</div>
                    <div class="summary-title">총 지출</div>
                    <div class="summary-amount expense" id="totalExpense">₩0</div>
                </div>
                <div class="summary-card">
                    <div class="summary-icon">📊</div>
                    <div class="summary-title">순익</div>
                    <div class="summary-amount profit" id="netProfit">₩0</div>
                </div>
            </div>
            
            <!-- 필터 섹션 -->
            <div class="filter-section">
                <div class="filter-title">🔍 필터</div>
                <div class="filter-row">
                    <div class="filter-group">
                        <label class="filter-label">기간</label>
                        <select class="filter-select" id="periodFilter">
                            <option value="all">전체</option>
                            <option value="this_month">이번달</option>
                            <option value="last_month">지난달</option>
                            <option value="this_year">올해</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label class="filter-label">타입</label>
                        <select class="filter-select" id="typeFilter">
                            <option value="all">전체</option>
                            <option value="expense">지출만</option>
                            <option value="income">수익만</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label class="filter-label">업무</label>
                        <select class="filter-select" id="taskFilter">
                            <option value="all">전체</option>
                            <option value="general">일반</option>
                        </select>
                    </div>
                    <button class="filter-btn" onclick="applyFilters()">적용</button>
                </div>
            </div>
            
            <!-- 리스트 섹션 -->
            <div class="list-section">
                <div class="list-title">
                    📋 지출/수익 내역
                    <span id="itemCount" style="font-size: 14px; color: #666; font-weight: normal;">(0건)</span>
                </div>
                <div class="list-container" id="listContainer">
                    <div class="loading">
                        <div class="spinner"></div>
                        데이터를 불러오는 중...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                loadProfitLossData();
                loadTasksForFilter();
            }});
            
            // 손익 데이터 로드
            async function loadProfitLossData() {{
                try {{
                    // 요약 데이터 로드
                    await loadSummaryData();
                    
                    // 지출/수익 목록 로드
                    await loadTransactionsList();
                    
                }} catch (error) {{
                    console.error('손익 데이터 로딩 실패:', error);
                    showError('데이터 로딩에 실패했습니다.');
                }}
            }}
            
            // 요약 데이터 로드
            async function loadSummaryData() {{
                try {{
                    const response = await fetch('/api/business/dashboard-stats');
                    const data = await response.json();
                    
                    if (data.success && data.summary) {{
                        const summary = data.summary;
                        
                        document.getElementById('totalIncome').textContent = 
                            '₩' + summary.total_incomes.toLocaleString();
                        document.getElementById('totalExpense').textContent = 
                            '₩' + summary.total_expenses.toLocaleString();
                        document.getElementById('netProfit').textContent = 
                            '₩' + (summary.total_incomes - summary.total_expenses).toLocaleString();
                    }}
                }} catch (error) {{
                    console.error('요약 데이터 로드 실패:', error);
                }}
            }}
            
            // 거래 목록 로드
            async function loadTransactionsList() {{
                const container = document.getElementById('listContainer');
                
                try {{
                    // 지출 데이터 로드
                    const expenseResponse = await fetch('/api/business/expenses?limit=50');
                    const expenseData = await expenseResponse.json();
                    
                    // 수익 데이터 로드 (TODO: 수익 API 구현 후 활성화)
                    const incomes = [];
                    
                    const expenses = expenseData.success ? expenseData.expenses : [];
                    
                    // 데이터 병합 및 정렬
                    const transactions = [
                        ...expenses.map(exp => ({{
                            ...exp,
                            type: 'expense',
                            date: exp.expense_date,
                            title: exp.description
                        }})),
                        ...incomes.map(inc => ({{
                            ...inc,
                            type: 'income',
                            date: inc.income_date,
                            title: inc.title
                        }}))
                    ].sort((a, b) => new Date(b.date) - new Date(a.date));
                    
                    if (transactions.length === 0) {{
                        container.innerHTML = `
                            <div class="empty-state">
                                <div class="empty-icon">📊</div>
                                <h3>아직 등록된 지출/수익이 없습니다</h3>
                                <p>대시보드에서 지출 내역을 등록해보세요!</p>
                            </div>
                        `;
                        document.getElementById('itemCount').textContent = '(0건)';
                        return;
                    }}
                    
                    // 리스트 렌더링
                    container.innerHTML = transactions.map(item => `
                        <div class="list-item ${{item.type}}">
                            <div class="item-header">
                                <div class="item-title">${{item.title || item.description}}</div>
                                <div class="item-amount ${{item.type}}">
                                    ${{item.type === 'expense' ? '-' : '+'}}₩${{item.amount.toLocaleString()}}
                                </div>
                            </div>
                            <div class="item-meta">
                                <div class="meta-item">
                                    📅 ${{formatDate(item.date)}}
                                </div>
                                ${{item.task_title ? `<div class="meta-item"><span class="task-tag">${{item.task_title}}</span></div>` : ''}}
                                <div class="meta-item">
                                    <span class="category-tag">${{item.category}}</span>
                                </div>
                                ${{item.status ? `<div class="meta-item">📋 ${{item.status}}</div>` : ''}}
                            </div>
                        </div>
                    `).join('');
                    
                    document.getElementById('itemCount').textContent = `(${{transactions.length}}건)`;
                    
                }} catch (error) {{
                    console.error('거래 목록 로드 실패:', error);
                    container.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">❌</div>
                            <h3>데이터 로드 실패</h3>
                            <p>잠시 후 다시 시도해주세요.</p>
                        </div>
                    `;
                }}
            }}
            
            // 필터용 업무 목록 로드
            async function loadTasksForFilter() {{
                try {{
                    const response = await fetch('/api/business/tasks');
                    const data = await response.json();
                    
                    if (data.success && data.tasks) {{
                        const taskFilter = document.getElementById('taskFilter');
                        
                        data.tasks.forEach(task => {{
                            const option = document.createElement('option');
                            option.value = task.id;
                            option.textContent = `[${{task.category}}] ${{task.title}}`;
                            taskFilter.appendChild(option);
                        }});
                    }}
                }} catch (error) {{
                    console.error('업무 목록 로드 실패:', error);
                }}
            }}
            
            // 필터 적용
            function applyFilters() {{
                // TODO: 필터 기능 구현
                console.log('필터 적용 기능은 추후 구현 예정');
                loadTransactionsList();
            }}
            
            // 날짜 포맷팅
            function formatDate(dateString) {{
                const date = new Date(dateString);
                return date.toLocaleDateString('ko-KR', {{
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                }});
            }}
            
            // 에러 표시
            function showError(message) {{
                const container = document.getElementById('listContainer');
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">❌</div>
                        <h3>오류 발생</h3>
                        <p>${{message}}</p>
                    </div>
                `;
            }}

            // 탭 선택 및 서브 버튼 제어 시스템
            let currentTab = 'profit'; // 손익 페이지이므로 기본적으로 profit 탭 활성화

            function selectTab(tabType) {{
                // 이미 선택된 탭을 다시 누르면 서브 버튼 숨김
                if (currentTab === tabType) {{
                    hideSubButtons();
                    return;
                }}
                
                currentTab = tabType;
                
                if (tabType === 'task') {{
                    // 업무 탭 선택
                    showSubButtons('📋', '업무 목록', '➕', '업무 등록', 
                                  'refreshTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    // 손익 탭 선택
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showExpenseModal()');
                    updateTabState('profit');
                }}
            }}
            
            function showSubButtons(icon1, label1, icon2, label2, action1, action2) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const button1 = document.getElementById('subButton1');
                const button2 = document.getElementById('subButton2');
                const icon1El = document.getElementById('subIcon1');
                const label1El = document.getElementById('subLabel1');
                const icon2El = document.getElementById('subIcon2');
                const label2El = document.getElementById('subLabel2');
                
                // 서브 버튼 내용 설정
                icon1El.textContent = icon1;
                label1El.textContent = label1;
                icon2El.textContent = icon2;
                label2El.textContent = label2;
                
                // 클릭 이벤트 설정
                button1.onclick = () => eval(action1);
                button2.onclick = () => eval(action2);
                
                // 애니메이션과 함께 표시
                subButtons.style.display = 'flex';
                setTimeout(() => {{
                    subButtons.style.animation = 'slideUp 0.3s ease-out';
                }}, 10);
            }}
            
            function hideSubButtons() {{
                const subButtons = document.getElementById('floatingSubButtons');
                subButtons.style.display = 'none';
                currentTab = null;
                updateTabState(null);
            }}
            
            function updateTabState(activeTab) {{
                // 모든 탭에서 active 클래스 제거
                document.getElementById('taskTab').classList.remove('active');
                document.getElementById('profitTab').classList.remove('active');
                
                // 선택된 탭에 active 클래스 추가
                if (activeTab === 'task') {{
                    document.getElementById('taskTab').classList.add('active');
                }} else if (activeTab === 'profit') {{
                    document.getElementById('profitTab').classList.add('active');
                }}
            }}

            function navigateToTaskList() {{
                // 이미 task-list 페이지에 있으므로 업무 목록 새로고침
                loadTasks();
            }}
            
            function refreshTaskList() {{
                // 업무 목록 새로고침용 함수
                loadTasks();
            }}

            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}

            function showQuickTaskModal() {{
                const modal = document.getElementById('quickTaskModal');
                modal.style.display = 'block';
                // 폼 리셋
                document.getElementById('quickTaskForm').reset();
                
                // 오늘 날짜를 시작일 기본값으로 설정
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('quickTaskStartDate').value = today;
                
                document.getElementById('quickTaskTitle').focus();
            }}

            function showExpenseModal() {{
                // 손익 등록 모달 (향후 구현)
                alert('손익 등록 기능이 곧 추가될 예정입니다');
            }}

            // 햄버거 메뉴 토글 함수
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                const isVisible = dropdown.style.display === 'block';
                dropdown.style.display = isVisible ? 'none' : 'block';
                
                if (!isVisible) {{
                    setTimeout(() => {{
                        document.addEventListener('click', closeMenuOnOutsideClick);
                    }}, 100);
                }}
            }}

            function closeMenuOnOutsideClick(event) {{
                const dropdown = document.getElementById('userDropdown');
                const menuBtn = document.querySelector('.menu-btn');
                
                if (!dropdown.contains(event.target) && !menuBtn.contains(event.target)) {{
                    dropdown.style.display = 'none';
                    document.removeEventListener('click', closeMenuOnOutsideClick);
                }}
            }}

            // 로그아웃 함수
            function logout() {{
                if (confirm('정말로 로그아웃 하시겠습니까?')) {{
                    window.location.href = '/api/auth/logout';
                }}
            }}

            // 화면 다른 곳 클릭 시 서브 버튼 숨김
            document.addEventListener('click', function(event) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const bottomNav = document.querySelector('.bottom-nav');
                
                if (currentTab && subButtons.style.display === 'flex') {{
                    // 서브 버튼이나 탭바가 아닌 곳을 클릭한 경우
                    if (!subButtons.contains(event.target) && !bottomNav.contains(event.target)) {{
                        hideSubButtons();
                    }}
                }}
            }});

            // 페이지 로드시 손익 탭을 활성 상태로 설정
            document.addEventListener('DOMContentLoaded', function() {{
                updateTabState('profit'); // 손익 페이지이므로 profit 탭 활성화
            }});
        </script>

        <!-- 플로팅 서브 버튼 (탭바 위쪽) -->
        <div class="floating-sub-buttons" id="floatingSubButtons" style="display: none;">
            <div class="sub-button" id="subButton1" onclick="">
                <div class="sub-icon" id="subIcon1">📋</div>
                <div class="sub-label" id="subLabel1">목록</div>
            </div>
            <div class="sub-button" id="subButton2" onclick="">
                <div class="sub-icon" id="subIcon2">➕</div>
                <div class="sub-label" id="subLabel2">등록</div>
            </div>
        </div>

        <!-- 하단 탭바 네비게이션 (2개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item active" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@dashboard_views_router.get("/legacy-dashboard", response_class=HTMLResponse)
async def legacy_main_dashboard(request: Request):
    """기존 메인 대시보드 (백업용)"""
    
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_id = current_user.get('id')
    
    # 세션 관리자에서 사용자별 세션 정보를 가져옴
    from core.session.session_manager import session_manager
    
    # API 키 세션 확인 - 단순화된 버전
    api_connected = False
    try:
        session_info = session_manager.get_session(user_id)
        api_connected = session_info is not None
    except Exception:
        api_connected = False
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Teamprime - 업비트 자동거래 시스템 (Legacy)</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
            }}
            
            .app-bar {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 20px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .main-content {{
                padding: 30px 20px;
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .trading-status-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                cursor: pointer;
                transition: all 0.3s ease;
                height: 150px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            
            .trading-status-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.15);
            }}
            
            .status-info {{
                display: flex;
                flex-direction: column;
            }}
            
            .status-title {{
                font-size: 20px;
                font-weight: 600;
                color: #333;
                margin-bottom: 10px;
            }}
            
            .status-description {{
                font-size: 16px;
                color: #666;
                margin-bottom: 15px;
            }}
            
            .status-indicator {{
                display: flex;
                align-items: center;
                font-size: 14px;
                font-weight: 500;
            }}
            
            .status-dot {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            
            .status-connected {{ background-color: #4caf50; }}
            .status-disconnected {{ background-color: #ff9800; }}
            
            .status-arrow {{
                font-size: 24px;
                color: #1976d2;
            }}
        </style>
    </head>
    <body>
        <div class="app-bar">
            <a href="/main-dashboard" class="app-title">Teamprime (Legacy)</a>
        </div>
        
        <div class="main-content">
            <div class="trading-status-card" onclick="goToTradingDashboard()">
                <div class="status-info">
                    <div class="status-title">자동거래 시스템</div>
                    <div class="status-description">Upbit 암호화폐 자동거래 시스템에 접근하세요</div>
                    <div class="status-indicator">
                        <div class="status-dot {'status-connected' if api_connected else 'status-disconnected'}"></div>
                        <span>{'API 연결됨' if api_connected else 'API 연결 필요'}</span>
                    </div>
                </div>
                <div class="status-arrow">→</div>
            </div>
        </div>
        
        <script>
            function goToTradingDashboard() {{
                window.location.href = '/dashboard';
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@dashboard_views_router.get("/dashboard", response_class=HTMLResponse)  
async def trading_dashboard(request: Request):
    """실제 거래 대시보드 (API 키 검증 후 접근)"""
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    user_id = current_user.get('id')
    username = current_user.get('username', '사용자')
    
    # 세션 관리자에서 API 키 세션 확인
    from core.session.session_manager import session_manager
    session_info = session_manager.get_session(user_id)
    
    if not session_info:
        # API 키가 세션에 없으면 API 키 입력으로 리다이렉트
        return RedirectResponse(url="/api-login")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>🚀 업비트 자동거래 대시보드</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                color: #333;
            }}
            
            .app-bar {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 0 30px;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                text-decoration: none;
            }}
            
            .user-info {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            
            .user-name {{
                font-weight: 600;
                color: #333;
            }}
            
            .user-role {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
            
            .menu-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: background-color 0.2s;
            }}
            
            .menu-btn:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
            
            /* 드롭다운 메뉴 */
            .user-menu {{
                position: relative;
                display: inline-block;
            }}
            
            .dropdown-menu {{
                display: none;
                position: absolute;
                right: 0;
                top: 100%;
                background: white;
                min-width: 160px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border-radius: 12px;
                padding: 8px 0;
                z-index: 1000;
                margin-top: 8px;
            }}
            
            .dropdown-menu.show {{
                display: block;
            }}
            
            .dropdown-item {{
                display: block;
                width: 100%;
                padding: 12px 20px;
                text-decoration: none;
                color: #333;
                border: none;
                background: none;
                text-align: left;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            
            .dropdown-item:hover {{
                background-color: #f8f9fa;
            }}
            
            .dropdown-divider {{
                height: 1px;
                background-color: #e9ecef;
                margin: 8px 0;
            }}
            
            /* 플로팅 서브 버튼 */
            .floating-sub-buttons {{
                position: fixed;
                bottom: 100px; /* 탭바(80px) 위쪽 20px */
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-radius: 25px;
                padding: 15px 25px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.15);
                z-index: 999;
                animation: slideUp 0.3s ease-out;
            }}
            
            .sub-button {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 15px 20px;
                border-radius: 18px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                cursor: pointer;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 70px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .sub-button:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .sub-button:active {{
                transform: translateY(-1px);
            }}
            
            .sub-icon {{
                font-size: 20px;
                margin-bottom: 4px;
            }}
            
            .sub-label {{
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateX(-50%) translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }}
            }}

            /* 하단 탭바 네비게이션 */
            .bottom-nav {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 80px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border-top: 1px solid #e0e0e0;
                box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-around;
                z-index: 1000;
                padding: 8px 16px 20px 16px; /* 하단 safe area 고려 */
            }}
            
            .nav-item {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 8px 12px;
                border-radius: 12px;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                min-width: 60px;
            }}
            
            .nav-item:hover {{
                background: rgba(103, 80, 164, 0.08);
                transform: translateY(-1px);
            }}
            
            .nav-item:active {{
                transform: translateY(0);
                background: rgba(103, 80, 164, 0.12);
            }}
            
            .nav-item.active {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }}
            
            .nav-item.active:hover {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }}
            
            .nav-icon {{
                font-size: 22px;
                margin-bottom: 4px;
            }}
            
            .nav-label {{
                font-size: 11px;
                font-weight: 500;
                color: #333;
                text-align: center;
            }}
            
            /* 태블릿 및 데스크톱에서 탭바 중앙 정렬 */
            @media (min-width: 768px) {{
                .bottom-nav {{
                    left: 50%;
                    transform: translateX(-50%);
                    width: 100%;
                    max-width: 800px;
                    border-radius: 20px 20px 0 0;
                }}
            }}

            .main-content {{
                padding: 30px 30px 100px 30px; /* 하단 탭바 공간 확보 */
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .status-indicator {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 8px;
                margin: 10px 0;
            }}
            
            .status-dot {{
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #4caf50;
            }}
            
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .btn-secondary {{
                background: #6c757d;
                color: white;
            }}
            
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            .control-panel {{
                display: flex;
                gap: 15px;
                margin-top: 20px;
                flex-wrap: wrap;
            }}
            
            .welcome-section {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="app-bar">
            <a href="/main-dashboard" class="app-title">🚀 Teamprime 자동거래</a>
            <div class="user-info">
                <span class="user-name">👤 {username}</span>
                <span class="user-role">{current_user.get('role', 'user').upper()}</span>
                
                <div class="user-menu">
                    <button class="menu-btn" onclick="toggleMenu()" aria-label="사용자 메뉴">☰</button>
                    <div class="dropdown-menu" id="userDropdown">
                        <a href="/profile" class="dropdown-item">👤 프로필</a>
                        <a href="/settings" class="dropdown-item">⚙️ 설정</a>
                        <div class="dropdown-divider"></div>
                        <button class="dropdown-item" onclick="logout()">🚪 로그아웃</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="welcome-section">
                <h1>💰 업비트 자동거래 대시보드</h1>
                <p>안전하고 효율적인 자동거래 시스템에 오신 것을 환영합니다!</p>
                
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span>✅ API 키 인증 완료</span>
                </div>
                
                <div class="control-panel">
                    <button id="tradingToggleBtn" class="btn btn-primary" onclick="toggleTrading()">🟢 자동거래 시작</button>
                    <button class="btn btn-secondary" onclick="checkStatus()">📊 상태 확인</button>
                </div>
            </div>
            
            <!-- 기능 없는 UI 카드들 제거: 실제 작동하는 기능만 유지 -->
        </div>
        
        <script>
            function toggleDropdown() {{
                const dropdown = document.getElementById('userDropdown');
                dropdown.classList.toggle('show');
            }}
            
            // 드롭다운 외부 클릭시 닫기
            window.addEventListener('click', function(event) {{
                if (!event.target.matches('.menu-btn')) {{
                    const dropdowns = document.getElementsByClassName("dropdown-menu");
                    for (let i = 0; i < dropdowns.length; i++) {{
                        const openDropdown = dropdowns[i];
                        if (openDropdown.classList.contains('show')) {{
                            openDropdown.classList.remove('show');
                        }}
                    }}
                }}
            }});
            
            let isTrading = false; // 거래 상태 추적
            
            // 페이지 로드시 현재 거래 상태 확인
            window.addEventListener('load', function() {{
                updateTradingButtonStatus();
            }});
            
            function toggleTrading() {{
                const btn = document.getElementById('tradingToggleBtn');
                
                if (isTrading) {{
                    // 현재 거래 중이면 중지
                    btn.disabled = true;
                    btn.innerHTML = '🔄 중지 중...';
                    
                    fetch('/api/stop-trading', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                isTrading = false;
                                btn.innerHTML = '🟢 자동거래 시작';
                                btn.className = 'btn btn-primary';
                                alert('🔴 자동거래가 중지되었습니다!');
                            }} else {{
                                alert('❌ ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('❌ 네트워크 오류: ' + error);
                        }})
                        .finally(() => {{
                            btn.disabled = false;
                        }});
                }} else {{
                    // 현재 중지 상태면 시작
                    btn.disabled = true;
                    btn.innerHTML = '🔄 시작 중...';
                    
                    fetch('/api/start-trading', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                isTrading = true;
                                btn.innerHTML = '🔴 자동거래 중지';
                                btn.className = 'btn btn-secondary';
                                alert('✅ 자동거래가 시작되었습니다!');
                            }} else {{
                                alert('❌ ' + data.message);
                            }}
                        }})
                        .catch(error => {{
                            alert('❌ 네트워크 오류: ' + error);
                        }})
                        .finally(() => {{
                            btn.disabled = false;
                        }});
                }}
            }}
            
            function updateTradingButtonStatus() {{
                // 현재 거래 상태를 서버에서 확인하여 버튼 상태 동기화
                fetch('/api/trading-status')
                    .then(response => response.json())
                    .then(data => {{
                        const btn = document.getElementById('tradingToggleBtn');
                        if (data.is_running) {{
                            isTrading = true;
                            btn.innerHTML = '🔴 자동거래 중지';
                            btn.className = 'btn btn-secondary';
                        }} else {{
                            isTrading = false;
                            btn.innerHTML = '🟢 자동거래 시작';
                            btn.className = 'btn btn-primary';
                        }}
                    }})
                    .catch(error => {{
                        console.error('거래 상태 확인 실패:', error);
                    }});
            }}
            
            function checkStatus() {{
                fetch('/api/trading-status')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.is_running !== undefined) {{
                            const status = data.is_running ? '🟢 실행 중' : '🔴 중지됨';
                            const positions = Object.keys(data.positions || {{}}).length;
                            const budget = data.available_budget ? data.available_budget.toLocaleString() : '0';
                            alert(`📊 거래 상태: ${{status}}\n💼 현재 포지션: ${{positions}}개\n💰 사용 가능 예산: ${{budget}}원`);
                        }} else {{
                            alert('❌ 상태 확인 실패: ' + (data.error || data.message || '알 수 없는 오류'));
                        }}
                    }})
                    .catch(error => alert('❌ 네트워크 오류: ' + error));
            }}
            
            // === 탭바 관련 JavaScript 함수들 ===
            let currentTab = null;

            function selectTab(tabType) {{
                // 이미 선택된 탭을 다시 누르면 서브 버튼 숨김
                if (currentTab === tabType) {{
                    hideSubButtons();
                    return;
                }}
                
                currentTab = tabType;
                
                if (tabType === 'task') {{
                    // 업무 탭 선택
                    showSubButtons('📋', '업무 목록', '➕', '업무 등록', 
                                  'refreshTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    // 손익 탭 선택
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showExpenseModal()');
                    updateTabState('profit');
                }}
            }}
            
            function showSubButtons(icon1, label1, icon2, label2, action1, action2) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const button1 = document.getElementById('subButton1');
                const button2 = document.getElementById('subButton2');
                const icon1El = document.getElementById('subIcon1');
                const label1El = document.getElementById('subLabel1');
                const icon2El = document.getElementById('subIcon2');
                const label2El = document.getElementById('subLabel2');
                
                // 서브 버튼 내용 설정
                icon1El.textContent = icon1;
                label1El.textContent = label1;
                icon2El.textContent = icon2;
                label2El.textContent = label2;
                
                // 클릭 이벤트 설정
                button1.onclick = () => eval(action1);
                button2.onclick = () => eval(action2);
                
                // 애니메이션과 함께 표시
                subButtons.style.display = 'flex';
                setTimeout(() => {{
                    subButtons.style.animation = 'slideUp 0.3s ease-out';
                }}, 10);
            }}
            
            function hideSubButtons() {{
                const subButtons = document.getElementById('floatingSubButtons');
                subButtons.style.display = 'none';
                currentTab = null;
                updateTabState(null);
            }}
            
            function updateTabState(activeTab) {{
                // 모든 탭에서 active 클래스 제거
                document.getElementById('taskTab').classList.remove('active');
                document.getElementById('profitTab').classList.remove('active');
                
                // 선택된 탭에 active 클래스 추가
                if (activeTab === 'task') {{
                    document.getElementById('taskTab').classList.add('active');
                }} else if (activeTab === 'profit') {{
                    document.getElementById('profitTab').classList.add('active');
                }}
            }}
            
            // 화면 다른 곳 클릭 시 서브 버튼 숨김
            document.addEventListener('click', function(event) {{
                const subButtons = document.getElementById('floatingSubButtons');
                const bottomNav = document.querySelector('.bottom-nav');
                
                if (currentTab && subButtons.style.display === 'flex') {{
                    // 서브 버튼이나 탭바가 아닌 곳을 클릭한 경우
                    if (!subButtons.contains(event.target) && !bottomNav.contains(event.target)) {{
                        hideSubButtons();
                    }}
                }}
            }});
            
            // 기존 네비게이션 함수들 유지
            function navigateToTaskList() {{
                window.location.href = '/task-list';
            }}
            
            function refreshTaskList() {{
                // 업무 목록으로 이동 (다른 페이지에서)
                window.location.href = '/task-list';
            }}
            
            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}
            
            function showQuickTaskModal() {{
                alert('빠른 업무 등록 기능은 메인 대시보드에서 이용하실 수 있습니다.');
            }}
            
            function showExpenseModal() {{
                alert('손익 등록 기능은 손익 페이지에서 이용하실 수 있습니다.');
            }}
            
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                dropdown.classList.toggle('show');
            }}
            
            function logout() {{
                if (confirm('로그아웃 하시겠습니까?')) {{
                    window.location.href = '/logout';
                }}
            }}
            
            // 메뉴 외부 클릭 시 닫기
            window.onclick = function(event) {{
                if (!event.target.matches('.menu-btn')) {{
                    const dropdown = document.getElementById('userDropdown');
                    if (dropdown.classList.contains('show')) {{
                        dropdown.classList.remove('show');
                    }}
                }}
            }}
        </script>
        
        <!-- 플로팅 서브 버튼 (탭바 위쪽) -->
        <div class="floating-sub-buttons" id="floatingSubButtons" style="display: none;">
            <div class="sub-button" id="subButton1" onclick="">
                <div class="sub-icon" id="subIcon1">📋</div>
                <div class="sub-label" id="subLabel1">목록</div>
            </div>
            <div class="sub-button" id="subButton2" onclick="">
                <div class="sub-icon" id="subIcon2">➕</div>
                <div class="sub-label" id="subLabel2">등록</div>
            </div>
        </div>

        <!-- 하단 탭바 네비게이션 (2개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
            </div>
        </div>
        
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)

@dashboard_views_router.get("/mtfa-dashboard", response_class=HTMLResponse)
async def mtfa_dashboard():
    """MTFA 분석 대시보드 (임시 비활성화)"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>MTFA 대시보드</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
            .message { background: #fff3cd; padding: 30px; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="message">
            <h2>📊 MTFA 분석 대시보드</h2>
            <p>MTFA 대시보드는 임시 비활성화되었습니다.</p>
            <p><a href="/main-dashboard">메인 대시보드로 돌아가기</a></p>
        </div>
    </body>
    </html>
    """)

@dashboard_views_router.get("/multi-coin-dashboard", response_class=HTMLResponse)
async def multi_coin_dashboard():
    """멀티 코인 분석 대시보드"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>멀티 코인 대시보드</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; text-align: center; }
            .message { background: #d1ecf1; padding: 30px; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="message">
            <h2>💰 멀티 코인 분석 대시보드</h2>
            <p>멀티 코인 분석 대시보드는 임시 비활성화되었습니다.</p>
            <p><a href="/main-dashboard">메인 대시보드로 돌아가기</a></p>
        </div>
    </body>
    </html>
    """)