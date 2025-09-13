"""
새로운 메인 대시보드 - 비즈니스 관리 시스템
- 수익/손실 상단 표시
- 업무 관리 중간 표시
- VIP 암호화폐 거래 하단 표시
"""

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

async def business_main_dashboard(request: Request):
    """새로운 비즈니스 관리 메인 대시보드"""
    
    # 사용자 인증 확인
    from core.auth.middleware import get_current_user
    current_user = await get_current_user(request)
    
    if not current_user:
        return RedirectResponse(url="/login")
    
    username = current_user.get('username', '사용자')
    user_role = current_user.get('role', 'user')
    user_id = current_user.get('id')
    user_email = current_user.get('email', '')
    
    # DB의 실제 role 값 사용 (이미 owner로 업데이트됨)
    display_role = user_role.upper()
    
    # VIP 권한 확인 (owner와 prime만 VIP 접근)
    has_vip_access = user_role in ["owner", "prime"]  
    can_promote = user_role == "owner"  # Owner만 사용자 승급 가능
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Teamprime - 비즈니스 관리 시스템</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            /* CSS Custom Properties (Material Design 3 Colors) */
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
                --md-elevation-4: 0 6px 10px 4px var(--md-shadow);
                --md-elevation-5: 0 8px 12px 6px var(--md-shadow);
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
                -webkit-tap-highlight-color: transparent;
                overscroll-behavior: contain;
            }}
            
            /* 모바일 앱바 */
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
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            
            .app-bar.scrolled {{
                height: 56px;
                backdrop-filter: blur(30px);
                -webkit-backdrop-filter: blur(30px);
            }}
            
            .app-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
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
            
            /* 모바일 메인 컨텐츠 */
            .main-content {{
                padding: 16px 16px 100px 16px; /* 하단 탭바 공간 확보 */
                max-width: 428px;
                margin: 0 auto;
                width: 100%;
                min-height: calc(100vh - 64px);
            }}
            
            @media (min-width: 768px) {{
                .main-content {{
                    max-width: 800px;
                    padding: 24px 24px 100px 24px; /* 하단 탭바 공간 확보 */
                }}
            }}
            
            /* 히어로 카드 */
            .hero-card {{
                background: linear-gradient(135deg, var(--md-primary) 0%, var(--md-secondary) 100%);
                border-radius: 24px;
                padding: 24px;
                margin-bottom: 24px;
                box-shadow: var(--md-elevation-4);
                color: var(--md-on-primary);
                position: relative;
                overflow: hidden;
                transform: translateZ(0);
                transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            }}
            
            .hero-card:active {{
                transform: scale(0.98);
            }}
            
            .hero-card::before {{
                content: '';
                position: absolute;
                top: -50%;
                right: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 50%);
                transform: rotate(45deg);
                pointer-events: none;
            }}
            
            .hero-title {{
                font-size: 16px;
                font-weight: 500;
                opacity: 0.9;
                margin-bottom: 8px;
                position: relative;
                z-index: 1;
            }}
            
            .hero-value {{
                font-size: 36px;
                font-weight: 700;
                margin-bottom: 4px;
                position: relative;
                z-index: 1;
                line-height: 1.1;
            }}
            
            .hero-subtitle {{
                font-size: 14px;
                opacity: 0.8;
                position: relative;
                z-index: 1;
            }}
            
            /* 가로 스크롤 슬라이더 */
            .slider-section {{
                margin-bottom: 24px;
            }}
            
            .slider-title {{
                color: white;
                font-size: 20px;
                font-weight: 600;
                margin-bottom: 16px;
                padding: 0 4px;
            }}
            
            .slider-container {{
                display: flex;
                gap: 16px;
                overflow-x: auto;
                padding: 0 4px 16px 4px;
                scroll-snap-type: x mandatory;
                scrollbar-width: none;
                -ms-overflow-style: none;
            }}
            
            .slider-container::-webkit-scrollbar {{
                display: none;
            }}
            
            .slider-card {{
                min-width: 160px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                padding: 20px;
                box-shadow: var(--md-elevation-3);
                scroll-snap-align: start;
                flex-shrink: 0;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                cursor: pointer;
            }}
            
            .slider-card:active {{
                transform: scale(0.95);
            }}
            
            .slider-card:hover {{
                transform: translateY(-2px);
                box-shadow: var(--md-elevation-4);
            }}
            
            .profit-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
                cursor: pointer;
            }}
            
            .profit-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 12px 35px rgba(0,0,0,0.15);
            }}
            
            .card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            
            .card-title {{
                font-size: 16px;
                font-weight: 600;
                color: #666;
            }}
            
            .card-icon {{
                font-size: 24px;
            }}
            
            .card-value {{
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .positive {{
                color: #4caf50;
            }}
            
            .negative {{
                color: #f44336;
            }}
            
            .neutral {{
                color: #2196f3;
            }}
            
            .card-subtitle {{
                font-size: 14px;
                color: #888;
            }}
            
            /* 업무 관리 섹션 (중간) */
            .tasks-section {{
                margin-bottom: 30px;
            }}
            
            .tasks-overview {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
            }}
            
            .tasks-list {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }}
            
            .task-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 0;
                border-bottom: 1px solid #eee;
            }}
            
            .task-item:last-child {{
                border-bottom: none;
            }}
            
            .task-info {{
                flex: 1;
            }}
            
            .task-title {{
                font-weight: 600;
                margin-bottom: 5px;
            }}
            
            .task-category {{
                font-size: 12px;
                color: #666;
                background: #f5f5f5;
                padding: 2px 8px;
                border-radius: 10px;
                display: inline-block;
            }}
            
            .task-status {{
                padding: 6px 12px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: 500;
            }}
            
            .status-대기 {{ background: #fff3cd; color: #856404; }}
            .status-진행중 {{ background: #d4edda; color: #155724; }}
            .status-완료 {{ background: #d1ecf1; color: #0c5460; }}
            .status-보류 {{ background: #f8d7da; color: #721c24; }}
            
            .tasks-stats {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }}
            
            .stat-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .stat-label {{
                font-weight: 500;
            }}
            
            .stat-value {{
                font-weight: 700;
                font-size: 18px;
                color: #667eea;
            }}
            
            /* 암호화폐 거래 현황 섹션 */
            .vip-section {{
                margin-top: 30px;
            }}
            
            .crypto-dashboard-container {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }}
            
            .crypto-dashboard-container:hover {{
                transform: translateY(-3px);
                box-shadow: 0 12px 35px rgba(0,0,0,0.25);
            }}
            
            .crypto-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.2);
                padding-bottom: 15px;
            }}
            
            .crypto-title {{
                font-size: 24px;
                font-weight: 700;
                margin: 0;
            }}
            
            .trading-status-badge {{
                background: rgba(255,255,255,0.2);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                backdrop-filter: blur(5px);
            }}
            
            .trading-status-badge.running {{
                background: rgba(76, 175, 80, 0.8);
            }}
            
            .trading-status-badge.stopped {{
                background: rgba(244, 67, 54, 0.8);
            }}
            
            .crypto-stats {{
                margin: 20px 0;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }}
            
            .stat-box {{
                background: rgba(255,255,255,0.1);
                padding: 20px 15px;
                border-radius: 12px;
                backdrop-filter: blur(5px);
                text-align: center;
            }}
            
            .stat-label {{
                font-size: 13px;
                opacity: 0.8;
                margin-bottom: 8px;
                font-weight: 500;
            }}
            
            .stat-value {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 5px;
            }}
            
            .stat-change {{
                font-size: 12px;
                opacity: 0.9;
            }}
            
            .positive {{ color: #4caf50; }}
            .negative {{ color: #f44336; }}
            .neutral {{ color: #2196f3; }}
            
            .positions-list {{
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
                padding: 15px;
                backdrop-filter: blur(5px);
            }}
            
            .position-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            
            .position-item:last-child {{
                border-bottom: none;
            }}
            
            .position-coin {{
                font-weight: 600;
            }}
            
            .position-pnl {{
                font-weight: 600;
                font-size: 14px;
            }}
            
            .crypto-actions {{
                text-align: center;
                margin-top: 20px;
            }}
            
            .crypto-btn {{
                background: rgba(255,255,255,0.9);
                color: #333;
                border: none;
                padding: 12px 30px;
                border-radius: 25px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .crypto-btn:hover {{
                background: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            /* 액션 버튼들 */
            .action-buttons {{
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 30px;
            }}
            
            .action-btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }}
            
            .btn-primary {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .btn-secondary {{
                background: rgba(255, 255, 255, 0.9);
                color: #333;
                border: 1px solid #ddd;
            }}
            
            .btn-success {{
                background: linear-gradient(45deg, #4caf50, #45a049);
                color: white;
            }}
            
            .btn-create {{
                background: linear-gradient(45deg, #ff6b6b, #ee5a52);
                color: white;
                border: none;
                cursor: pointer;
            }}
            
            .action-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
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
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 28px;
                cursor: pointer;
                color: #aaa;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .close-btn:hover {{
                color: #000;
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
            }}
            
            .quick-form-textarea {{
                width: 100%;
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                resize: vertical;
                min-height: 100px;
            }}
            
            .quick-form-actions {{
                display: flex;
                gap: 10px;
                justify-content: flex-end;
                margin-top: 25px;
            }}
            
            .quick-btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }}
            
            .quick-btn-cancel {{
                background: #f5f5f5;
                color: #666;
            }}
            
            .quick-btn-cancel:hover {{
                background: #e0e0e0;
            }}
            
            .quick-btn-save {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .quick-btn-save:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            .quick-btn-save:disabled {{
                background: #ccc;
                cursor: not-allowed;
                transform: none;
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
            
            /* 토스트 알림 애니메이션 */
            @keyframes slideIn {{
                from {{
                    transform: translateX(100%);
                    opacity: 0;
                }}
                to {{
                    transform: translateX(0);
                    opacity: 1;
                }}
            }}
            
            @keyframes slideOut {{
                from {{
                    transform: translateX(0);
                    opacity: 1;
                }}
                to {{
                    transform: translateX(100%);
                    opacity: 0;
                }}
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
                background-color: white;
                margin: 10% auto;
                padding: 0;
                border-radius: 15px;
                width: 90%;
                max-width: 400px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                overflow: hidden;
            }}
            
            .menu-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 25px;
                background: linear-gradient(45deg, var(--md-primary), var(--md-secondary));
                color: var(--md-on-primary);
            }}
            
            .menu-title {{
                font-size: 20px;
                font-weight: 600;
                margin: 0;
            }}
            
            .menu-header .close-btn {{
                color: var(--md-on-primary);
                font-size: 24px;
            }}
            
            .menu-items {{
                padding: 15px 0;
            }}
            
            .menu-item {{
                display: flex;
                align-items: center;
                padding: 15px 25px;
                text-decoration: none;
                color: var(--md-on-surface);
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                border: none;
                background: none;
                width: 100%;
                cursor: pointer;
            }}
            
            .menu-item:hover {{
                background: var(--md-surface-variant);
            }}
            
            .menu-item.logout:hover {{
                background: rgba(244, 67, 54, 0.08);
                color: #f44336;
            }}
            
            .menu-icon {{
                font-size: 20px;
                margin-right: 15px;
                width: 24px;
                text-align: center;
            }}
            
            .menu-text {{
                font-size: 16px;
                font-weight: 500;
            }}
            
            /* 지출 내역 등록 모달 */
            .expense-modal {{
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }}
            
            .expense-content {{
                background-color: white;
                margin: 5% auto;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 600px;
                max-height: 85vh;
                overflow-y: auto;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            
            .expense-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f0f0f0;
            }}
            
            .expense-title {{
                font-size: 24px;
                font-weight: 700;
                color: #333;
                margin: 0;
            }}
            
            .form-section {{
                margin-bottom: 25px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }}
            
            .section-title {{
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin: 0 0 15px 0;
                border-bottom: 1px solid #dee2e6;
                padding-bottom: 8px;
            }}
            
            .task-selection-row {{
                display: flex;
                gap: 10px;
                align-items: end;
            }}
            
            .flex-grow {{
                flex: 1;
            }}
            
            .search-container {{
                display: flex;
                gap: 5px;
            }}
            
            .search-input {{
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                width: 120px;
            }}
            
            .search-btn {{
                padding: 8px 12px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }}
            
            .search-btn:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            }}
            
            .form-group {{
                margin-bottom: 15px;
            }}
            
            .form-label {{
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #333;
                font-size: 14px;
            }}
            
            .form-input, .form-textarea {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.2s;
                box-sizing: border-box;
            }}
            
            .form-input:focus, .form-textarea:focus {{
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }}
            
            .radio-group {{
                display: flex;
                gap: 15px;
                margin-top: 5px;
            }}
            
            .radio-option {{
                display: flex;
                align-items: center;
                padding: 10px 15px;
                border: 2px solid #ddd;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                background: white;
                flex: 1;
                justify-content: center;
            }}
            
            .radio-option:hover {{
                border-color: #667eea;
                background: rgba(102, 126, 234, 0.05);
            }}
            
            .radio-option input[type="radio"] {{
                display: none;
            }}
            
            .radio-option input[type="radio"]:checked + .radio-text {{
                font-weight: 600;
            }}
            
            .profit-option:has(input[type="radio"]:checked) {{
                background: rgba(76, 175, 80, 0.1);
                border-color: #4CAF50;
            }}
            
            .profit-option:has(input[type="radio"]:checked) .radio-text {{
                color: #2E7D32;
            }}
            
            .expense-option:has(input[type="radio"]:checked) {{
                background: rgba(244, 67, 54, 0.1);
                border-color: #f44336;
            }}
            
            .expense-option:has(input[type="radio"]:checked) .radio-text {{
                color: #C62828;
            }}
            
            .radio-text {{
                font-size: 14px;
                font-weight: 500;
            }}
            
            .amount-korean {{
                margin-top: 5px;
                padding: 6px 8px;
                background: #f8f9fa;
                border-radius: 4px;
                font-size: 12px;
                color: #666;
                min-height: 16px;
                font-family: 'Malgun Gothic', sans-serif;
            }}
            
            .form-row {{
                display: flex;
                gap: 15px;
            }}
            
            .flex-1 {{
                flex: 1;
            }}
            
            .flex-2 {{
                flex: 2;
            }}
            
            .category-note {{
                margin-top: 5px;
                padding: 8px;
                background: #e3f2fd;
                border-radius: 6px;
                border-left: 3px solid #2196f3;
            }}
            
            .category-note small {{
                color: #1976d2;
                font-weight: 500;
            }}
            
            .form-actions {{
                display: flex;
                gap: 10px;
                justify-content: flex-end;
                margin-top: 25px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            
            .expense-btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                min-width: 100px;
            }}
            
            .expense-btn-cancel {{
                background: #f5f5f5;
                color: #666;
            }}
            
            .expense-btn-cancel:hover {{
                background: #e0e0e0;
            }}
            
            .expense-btn-save {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }}
            
            .expense-btn-save:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }}
            
            .expense-btn-save:disabled {{
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }}

            /* 반응형 디자인 */
            @media (max-width: 768px) {{
                .main-content {{
                    padding: 20px 15px;
                }}
                
                .profit-cards {{
                    grid-template-columns: 1fr;
                }}
                
                .tasks-overview {{
                    grid-template-columns: 1fr;
                }}
                
                .vip-features {{
                    grid-template-columns: 1fr;
                }}
                
                .action-buttons {{
                    flex-direction: column;
                }}
                
                .quick-task-content {{
                    margin: 5% auto;
                    width: 95%;
                    padding: 20px;
                }}
                
                .expense-content {{
                    margin: 5% auto;
                    padding: 20px;
                    width: 95%;
                }}
                
                .task-selection-row {{
                    flex-direction: column;
                    gap: 15px;
                }}
                
                .search-input {{
                    width: 100%;
                }}
                
                .form-row {{
                    flex-direction: column;
                    gap: 10px;
                }}
            }}
        </style>
    </head>
    <body>
        <!-- 앱바 -->
        <div class="app-bar">
            <div class="app-title">Teamprime 비즈니스</div>
            <div class="user-info">
                <span class="user-name">{username}</span>
                <span class="user-role">{display_role}</span>
                <div class="user-menu">
                    <button class="menu-btn" onclick="toggleMenu()">☰</button>
                    <div class="dropdown-menu" id="userDropdown">
                        <a href="/profile" class="dropdown-item">👤 프로필</a>
                        <a href="/settings" class="dropdown-item">⚙️ 설정</a>
                        <div class="dropdown-divider"></div>
                        <button class="dropdown-item" onclick="logout()">🚪 로그아웃</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 메인 컨텐츠 -->
        <div class="main-content">
            <!-- 히어로 카드 (순이익) -->
            <div class="hero-card" onclick="viewProfitLoss()">
                <div class="hero-title">순이익</div>
                <div class="hero-value" id="netProfit">0원</div>
                <div class="hero-subtitle">수익 - 지출 = 순이익</div>
            </div>
            
            <!-- 슬라이더 섹션 -->
            <div class="slider-section">
                <div class="slider-title">재무 현황</div>
                <div class="slider-container">
                    <div class="slider-card" onclick="viewIncomes()">
                        <div class="card-header">
                            <span class="card-title">총 수익</span>
                            <span class="card-icon">💰</span>
                        </div>
                        <div class="card-value positive" id="totalIncome">0원</div>
                        <div class="card-subtitle">이번 달</div>
                    </div>
                    
                    <div class="slider-card" onclick="viewExpenses()">
                        <div class="card-header">
                            <span class="card-title">총 지출</span>
                            <span class="card-icon">💳</span>
                        </div>
                        <div class="card-value negative" id="totalExpense">0원</div>
                        <div class="card-subtitle">이번 달</div>
                    </div>
                    
                    <div class="slider-card" onclick="viewTasks()">
                        <div class="card-header">
                            <span class="card-title">진행 업무</span>
                            <span class="card-icon">📋</span>
                        </div>
                        <div class="card-value neutral" id="inProgressTasks">-</div>
                        <div class="card-subtitle">진행중</div>
                    </div>
                    
                    <div class="slider-card" onclick="viewTasks()">
                        <div class="card-header">
                            <span class="card-title">완료 업무</span>
                            <span class="card-icon">✅</span>
                        </div>
                        <div class="card-value positive" id="completedTasks">-</div>
                        <div class="card-subtitle">완료됨</div>
                    </div>
                </div>
            </div>
            
            <!-- 최근 활동 (컴팩트) -->
            <div class="slider-section">
                <div class="slider-title">최근 활동</div>
                <div class="slider-card" style="min-width: calc(100% - 8px);">
                    <div id="recentTasks">
                        <div class="loading">
                            <div class="spinner"></div>
                            업무 목록을 불러오는 중...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- VIP 거래 섹션 (권한 있는 사용자만 표시) -->
            {'<div class="vip-section"><div class="crypto-dashboard-container"><div class="crypto-header"><h3 class="crypto-title">💰 암호화폐 거래 현황</h3><div class="trading-status-badge" id="tradingStatusBadge">확인 중...</div></div><div class="crypto-stats" id="cryptoStats"><div class="loading"><div class="spinner"></div>거래 데이터를 불러오는 중...</div></div><div class="crypto-actions"><button class="crypto-btn" onclick="goToCrypto()">거래 대시보드</button></div></div></div>' if has_vip_access else ''}
            
        </div>
        
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

        <!-- 하단 탭바 네비게이션 (3개 버튼) -->
        <div class="bottom-nav">
            <div class="nav-item active" id="homeTab" onclick="navigateToHome()">
                <div class="nav-icon">🏠</div>
                <div class="nav-label">홈</div>
            </div>
            <div class="nav-item" id="taskTab" onclick="selectTab('task')">
                <div class="nav-icon">📝</div>
                <div class="nav-label">업무</div>
            </div>
            <div class="nav-item" id="profitTab" onclick="selectTab('profit')">
                <div class="nav-icon">💰</div>
                <div class="nav-label">손익</div>
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
                    <a href="/legacy-dashboard" class="menu-item">
                        <div class="menu-icon">🏠</div>
                        <div class="menu-text">대시보드 (기존)</div>
                    </a>
                    {'<a href="/users" class="menu-item"><div class="menu-icon">👥</div><div class="menu-text">사용자 관리</div></a>' if can_promote else ''}
                    <a href="/profile" class="menu-item">
                        <div class="menu-icon">👤</div>
                        <div class="menu-text">프로필</div>
                    </a>
                    <a href="#" class="menu-item">
                        <div class="menu-icon">📋</div>
                        <div class="menu-text">자산 목록</div>
                    </a>
                    <a href="/logout" class="menu-item logout">
                        <div class="menu-icon">🚪</div>
                        <div class="menu-text">로그아웃</div>
                    </a>
                </div>
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
        
        <!-- 지출 내역 등록 모달 -->
        <div class="expense-modal" id="expenseModal">
            <div class="expense-content">
                <div class="expense-header">
                    <h3 class="expense-title">💳 지출 내역 등록</h3>
                    <button class="close-btn" onclick="hideExpenseModal()">&times;</button>
                </div>
                <form id="expenseForm">
                    <!-- 업무 연동 섹션 -->
                    <div class="form-section">
                        <h4 class="section-title">업무 연동</h4>
                        <div class="task-selection-row">
                            <div class="form-group flex-grow">
                                <label class="form-label">연결 업무 선택</label>
                                <select class="form-input" id="expenseTaskSelect">
                                    <option value="">업무를 선택하세요</option>
                                </select>
                            </div>
                            <div class="search-container">
                                <input type="text" class="search-input" id="taskSearchInput" placeholder="업무명 검색">
                                <button type="button" class="search-btn" onclick="searchTasks()">🔍</button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 지출 정보 섹션 -->
                    <div class="form-section">
                        <h4 class="section-title">지출 정보</h4>
                        <div class="form-group">
                            <label class="form-label">카테고리 *</label>
                            <select class="form-input" id="expenseCategory" onchange="handleCategoryChange()" required>
                                <option value="">카테고리를 선택하세요</option>
                                <option value="자산">자산</option>
                                <option value="소모품">소모품</option>
                                <option value="식비">식비</option>
                                <option value="교통">교통</option>
                                <option value="출장">출장</option>
                                <option value="통신">통신</option>
                                <option value="소프트웨어">소프트웨어</option>
                                <option value="급여">급여</option>
                                <option value="인센티브">인센티브</option>
                                <option value="교육/세미나">교육/세미나</option>
                                <option value="관리비">관리비</option>
                                <option value="인건비">인건비</option>
                                <option value="용역">용역</option>
                                <option value="세금">세금</option>
                                <option value="기타">기타</option>
                                <option value="일반">일반</option>
                            </select>
                            <div class="category-note" id="categoryNote" style="display: none;">
                                <small>"일반" 카테고리는 업무 연동 없이 등록 가능합니다.</small>
                            </div>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group flex-2">
                                <label class="form-label">지출 제목 *</label>
                                <input type="text" class="form-input" id="expenseTitle" 
                                       placeholder="지출 제목을 입력하세요" maxlength="200" required>
                            </div>
                            <div class="form-group flex-1">
                                <label class="form-label">지출 금액 *</label>
                                <input type="number" class="form-input" id="expenseAmount" 
                                       placeholder="0" min="1" step="1" required>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">지출 일시</label>
                            <input type="datetime-local" class="form-input" id="expenseDate">
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">상세 설명</label>
                            <textarea class="form-textarea" id="expenseDescription" 
                                      placeholder="지출에 대한 상세 설명을 입력하세요 (선택사항)" rows="3"></textarea>
                        </div>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="expense-btn expense-btn-cancel" onclick="hideExpenseModal()">
                            취소
                        </button>
                        <button type="button" class="expense-btn expense-btn-save" onclick="saveExpense()">
                            등록하기
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- 손익 등록 모달 -->
        <div class="expense-modal" id="profitModal">
            <div class="expense-content">
                <div class="expense-header">
                    <h3 class="expense-title">💰 손익 등록</h3>
                    <button class="close-btn" onclick="hideProfitModal()">&times;</button>
                </div>
                <form id="profitForm">
                    <!-- 업무 연동 섹션 -->
                    <div class="form-section">
                        <h4 class="section-title">업무 연동</h4>
                        <div class="task-selection-row">
                            <div class="form-group flex-grow">
                                <label class="form-label">연결 업무 선택</label>
                                <select class="form-input" id="profitTaskSelect">
                                    <option value="">업무를 선택하세요</option>
                                </select>
                            </div>
                            <div class="search-container">
                                <input type="text" class="search-input" id="profitTaskSearchInput" placeholder="업무명 검색">
                                <button type="button" class="search-btn" onclick="searchProfitTasks()">🔍</button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 손익 정보 섹션 -->
                    <div class="form-section">
                        <h4 class="section-title">손익 정보</h4>
                        <div class="form-group">
                            <label class="form-label">손익 유형 *</label>
                            <div class="radio-group">
                                <label class="radio-option profit-option">
                                    <input type="radio" name="profitType" value="수익" id="profitTypeIncome" onchange="handleProfitTypeChange()">
                                    <span class="radio-text">💰 수익</span>
                                </label>
                                <label class="radio-option expense-option">
                                    <input type="radio" name="profitType" value="지출" id="profitTypeExpense" checked onchange="handleProfitTypeChange()">
                                    <span class="radio-text">💳 지출</span>
                                </label>
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">지출 종류 *</label>
                            <select class="form-input" id="profitCategory" onchange="handleProfitCategoryChange()" required>
                                <option value="">지출 종류를 선택하세요</option>
                                <option value="자산">자산</option>
                                <option value="식비">식비</option>
                                <option value="교통비">교통비</option>
                                <option value="업무추진비">업무추진비</option>
                                <option value="출장비">출장비</option>
                                <option value="인건비">인건비</option>
                                <option value="급여">급여</option>
                                <option value="인센티브">인센티브</option>
                                <option value="일반">일반</option>
                            </select>
                            <div class="category-note" id="profitCategoryNote" style="display: none;">
                                <small>"일반" 카테고리는 업무 연동 없이 등록 가능합니다.</small>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">설명 *</label>
                            <textarea class="form-textarea" id="profitDescription" 
                                      placeholder="손익에 대한 설명을 입력하세요" rows="3" required></textarea>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group flex-2">
                                <label class="form-label">손익 제목 *</label>
                                <input type="text" class="form-input" id="profitTitle" 
                                       placeholder="손익 제목을 입력하세요" maxlength="200" required>
                            </div>
                            <div class="form-group flex-1">
                                <label class="form-label">손익 금액 *</label>
                                <input type="text" class="form-input" id="profitAmount" 
                                       placeholder="0" inputmode="numeric" required 
                                       oninput="formatAmountInput(this)" onkeypress="return isNumberKey(event)">
                                <div class="amount-korean" id="profitAmountKorean"></div>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">손익 일시</label>
                            <input type="datetime-local" class="form-input" id="profitDate">
                        </div>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" class="expense-btn expense-btn-cancel" onclick="hideProfitModal()">
                            취소
                        </button>
                        <button type="button" class="expense-btn expense-btn-save" onclick="saveProfit()">
                            등록하기
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <script>
            // 페이지 로드 시 데이터 초기화
            document.addEventListener('DOMContentLoaded', function() {{
                loadDashboardData();
            }});
            
            // 대시보드 데이터 로딩
            async function loadDashboardData() {{
                try {{
                    // 재무 현황 로딩
                    await loadFinancialData();
                    
                    // 업무 현황 로딩
                    await loadTasksData();
                    
                    // 암호화폐 거래 현황 로딩 (VIP 권한 확인)
                    const hasVipAccess = {str(has_vip_access).lower()};
                    if (hasVipAccess) {{
                        await loadCryptoData();
                    }}
                    
                }} catch (error) {{
                    console.error('대시보드 데이터 로딩 실패:', error);
                }}
            }}
            
            // 재무 데이터 로딩
            async function loadFinancialData() {{
                try {{
                    const response = await fetch('/api/business/dashboard-stats');
                    const data = await response.json();
                    
                    if (data.success) {{
                        const summary = data.summary;
                        
                        // 수익 표시
                        document.getElementById('totalIncome').textContent = 
                            summary.total_incomes.toLocaleString() + '원';
                        
                        // 지출 표시
                        document.getElementById('totalExpense').textContent = 
                            summary.total_expenses.toLocaleString() + '원';
                        
                        // 순이익 표시 및 색상 설정
                        const netProfitElement = document.getElementById('netProfit');
                        const netProfit = summary.net_profit;
                        netProfitElement.textContent = netProfit.toLocaleString() + '원';
                        
                        if (netProfit > 0) {{
                            netProfitElement.className = 'card-value positive';
                        }} else if (netProfit < 0) {{
                            netProfitElement.className = 'card-value negative';
                        }} else {{
                            netProfitElement.className = 'card-value neutral';
                        }}
                    }}
                }} catch (error) {{
                    console.error('재무 데이터 로딩 실패:', error);
                    document.getElementById('totalIncome').textContent = '데이터 로드 실패';
                    document.getElementById('totalExpense').textContent = '데이터 로드 실패';
                    document.getElementById('netProfit').textContent = '데이터 로드 실패';
                }}
            }}
            
            // 업무 데이터 로딩
            async function loadTasksData() {{
                try {{
                    const response = await fetch('/api/business/tasks?limit=5');
                    const data = await response.json();
                    
                    if (data.success) {{
                        const tasks = data.tasks;
                        const tasksContainer = document.getElementById('recentTasks');
                        
                        if (tasks.length === 0) {{
                            tasksContainer.innerHTML = '<p style="text-align: center; color: #888;">등록된 업무가 없습니다.</p>';
                        }} else {{
                            tasksContainer.innerHTML = tasks.map(task => `
                                <div class="task-item">
                                    <div class="task-info">
                                        <div class="task-title">${{task.title}}</div>
                                        <span class="task-category">${{task.category}}</span>
                                    </div>
                                    <span class="task-status status-${{task.status}}">${{task.status}}</span>
                                </div>
                            `).join('');
                        }}
                        
                        // 통계 업데이트
                        updateTaskStats(data);
                    }}
                }} catch (error) {{
                    console.error('업무 데이터 로딩 실패:', error);
                    document.getElementById('recentTasks').innerHTML = 
                        '<p style="text-align: center; color: #f44336;">업무 데이터를 불러올 수 없습니다.</p>';
                }}
            }}
            
            // 업무 통계 업데이트 (슬라이더 카드용)
            function updateTaskStats(data) {{
                const total = data.pagination.total;
                const tasks = data.tasks;
                
                // 전체 업무 통계를 위해 API 다시 호출 (전체 데이터 필요)
                fetch('/api/business/tasks').then(response => response.json()).then(fullData => {{
                    if (fullData.success) {{
                        const allTasks = fullData.tasks;
                        
                        // 상태별 카운트 (전체 데이터 기준)
                        const statusCounts = allTasks.reduce((acc, task) => {{
                            acc[task.status] = (acc[task.status] || 0) + 1;
                            return acc;
                        }}, {{}});
                        
                        const inProgress = statusCounts['진행중'] || 0;
                        const completed = statusCounts['완료'] || 0;
                        
                        // 슬라이더 카드 업데이트
                        const inProgressElement = document.getElementById('inProgressTasks');
                        const completedElement = document.getElementById('completedTasks');
                        
                        if (inProgressElement) inProgressElement.textContent = inProgress;
                        if (completedElement) completedElement.textContent = completed;
                    }}
                }}).catch(error => {{
                    console.error('전체 업무 통계 로딩 실패:', error);
                }});
            }}
            
            // 암호화폐 거래 데이터 로딩 (실제 API 데이터만 사용)
            async function loadCryptoData() {{
                try {{
                    const response = await fetch('/api/trading-status');
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}
                    
                    const data = await response.json();
                    
                    if (data.error) {{
                        console.error('거래 상태 조회 실패:', data.error);
                        updateCryptoUI(null, data.error);
                        return;
                    }}
                    
                    updateCryptoUI(data);
                    
                }} catch (error) {{
                    console.error('암호화폐 데이터 로딩 실패:', error);
                    updateCryptoUI(null, error.message);
                }}
            }}
            
            // 암호화폐 UI 업데이트
            function updateCryptoUI(data, errorMessage = null) {{
                const statusBadge = document.getElementById('tradingStatusBadge');
                const cryptoStats = document.getElementById('cryptoStats');
                
                if (errorMessage || !data) {{
                    statusBadge.textContent = '연결 실패';
                    statusBadge.className = 'trading-status-badge stopped';
                    cryptoStats.innerHTML = `<div style="text-align: center; color: rgba(255,255,255,0.7); padding: 20px;">
                        거래 데이터를 불러올 수 없습니다.<br>
                        <small>${{errorMessage || '알 수 없는 오류'}}</small>
                    </div>`;
                    return;
                }}
                
                // 거래 상태 업데이트
                const isRunning = data.is_running || false;
                statusBadge.textContent = isRunning ? '거래 중' : '중지됨';
                statusBadge.className = `trading-status-badge ${{isRunning ? 'running' : 'stopped'}}`;
                
                // 포지션 및 수익 데이터 계산
                const positions = data.positions || {{}};
                const positionCount = Object.keys(positions).length;
                const availableBudget = data.available_budget || 0;
                const dailyTrades = data.daily_trades || 0;
                
                // 총 미실현 손익 계산
                let totalUnrealizedPnl = 0;
                const positionsList = [];
                
                for (const [coin, position] of Object.entries(positions)) {{
                    const pnl = position.unrealized_pnl || 0;
                    totalUnrealizedPnl += pnl;
                    
                    positionsList.push({{
                        coin: coin.replace('KRW-', ''),
                        pnl: pnl,
                        amount: position.amount || 0,
                        currentPrice: position.current_price || 0
                    }});
                }}
                
                // 보유 코인 총 평가금액 계산
                const totalPositionValue = positionsList.reduce((sum, pos) => {{
                    return sum + (pos.amount * pos.currentPrice);
                }}, 0);
                
                const totalAssets = availableBudget + totalPositionValue;
                
                // HTML 업데이트
                cryptoStats.innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-label">오늘 손익</div>
                            <div class="stat-value ${{totalUnrealizedPnl >= 0 ? 'positive' : 'negative'}}">
                                ${{totalUnrealizedPnl >= 0 ? '+' : ''}}${{totalUnrealizedPnl.toLocaleString()}}원
                            </div>
                            <div class="stat-change">미실현 손익</div>
                        </div>
                        
                        <div class="stat-box">
                            <div class="stat-label">총 보유자산</div>
                            <div class="stat-value">${{totalAssets.toLocaleString()}}원</div>
                            <div class="stat-change">KRW: ${{availableBudget.toLocaleString()}} + 코인: ${{totalPositionValue.toLocaleString()}}</div>
                        </div>
                        
                        <div class="stat-box">
                            <div class="stat-label">활성 포지션</div>
                            <div class="stat-value">${{positionCount}}개</div>
                            <div class="stat-change">오늘 거래: ${{dailyTrades}}회</div>
                        </div>
                    </div>
                    
                    ${{positionCount > 0 ? `
                        <div class="positions-list">
                            <h4 style="margin: 0 0 15px 0; font-size: 16px; opacity: 0.9;">보유 포지션</h4>
                            ${{positionsList.map(pos => `
                                <div class="position-item">
                                    <div class="position-coin">${{pos.coin}}</div>
                                    <div class="position-pnl ${{pos.pnl >= 0 ? 'positive' : 'negative'}}">
                                        ${{pos.pnl >= 0 ? '+' : ''}}${{pos.pnl.toLocaleString()}}원
                                    </div>
                                </div>
                            `).join('')}}
                        </div>
                    ` : '<div style="text-align: center; opacity: 0.7; padding: 15px;">보유 중인 포지션이 없습니다</div>'}}
                `;
            }}
            
            // 네비게이션 함수들
            function viewIncomes() {{
                window.location.href = '/business/incomes';
            }}
            
            function viewExpenses() {{
                window.location.href = '/business/expenses';
            }}
            
            function viewProfitAnalysis() {{
                window.location.href = '/business/analytics';
            }}
            
            function goToCrypto() {{
                window.location.href = '/api-login';
            }}
            
            // 빠른 업무 등록 모달 표시
            function showQuickTaskModal() {{
                document.getElementById('quickTaskModal').style.display = 'block';
                
                // 오늘 날짜를 시작일 기본값으로 설정
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('quickTaskStartDate').value = today;
                
                document.getElementById('quickTaskTitle').focus();
            }}
            
            // 빠른 업무 등록 모달 숨기기
            function hideQuickTaskModal() {{
                document.getElementById('quickTaskModal').style.display = 'none';
                document.getElementById('quickTaskForm').reset();
            }}
            
            // 빠른 업무 저장
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
                        hideQuickTaskModal();
                        showToast('업무가 성공적으로 등록되었습니다!', 'success');
                        // 업무 현황 다시 로드
                        setTimeout(loadTasksData, 500);
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '업무 등록에 실패했습니다.'));
                    }}
                }} catch (error) {{
                    console.error('업무 등록 오류:', error);
                    alert('업무 등록 중 오류가 발생했습니다.');
                }} finally {{
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }}
            }}
            
            // 토스트 알림 표시
            function showToast(message, type = 'info') {{
                const toastDiv = document.createElement('div');
                toastDiv.className = `alert alert-${{type === 'success' ? 'success' : 'info'}} toast-notification`;
                toastDiv.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    min-width: 300px;
                    padding: 15px 20px;
                    background: ${{type === 'success' ? '#d4edda' : '#d1ecf1'}};
                    color: ${{type === 'success' ? '#155724' : '#0c5460'}};
                    border: 1px solid ${{type === 'success' ? '#c3e6cb' : '#bee5eb'}};
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    animation: slideIn 0.3s ease-out;
                `;
                toastDiv.textContent = message;
                
                document.body.appendChild(toastDiv);
                
                setTimeout(() => {{
                    toastDiv.style.animation = 'slideOut 0.3s ease-in';
                    setTimeout(() => toastDiv.remove(), 300);
                }}, 3000);
            }}
            
            // 모달 외부 클릭시 닫기
            window.addEventListener('click', function(event) {{
                const modal = document.getElementById('quickTaskModal');
                if (event.target === modal) {{
                    hideQuickTaskModal();
                }}
            }});
            
            // ESC 키로 모달 닫기
            document.addEventListener('keydown', function(event) {{
                if (event.key === 'Escape') {{
                    const modal = document.getElementById('quickTaskModal');
                    if (modal.style.display === 'block') {{
                        hideQuickTaskModal();
                    }}
                }}
            }});
            
            // showVipInfo 함수 제거됨 - 권한 없는 사용자는 VIP 섹션 자체를 볼 수 없음
            
            function toggleMenu() {{
                const dropdown = document.getElementById('userDropdown');
                dropdown.classList.toggle('show');
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
            
            async function logout() {{
                try {{
                    const response = await fetch('/api/auth/logout', {{
                        method: 'POST'
                    }});
                    
                    if (response.ok) {{
                        window.location.href = '/login';
                    }}
                }} catch (error) {{
                    console.error('로그아웃 실패:', error);
                }}
            }}
            
            // 자동 새로고침 (5분마다 전체 데이터, 1분마다 암호화폐 데이터)
            setInterval(loadDashboardData, 5 * 60 * 1000);
            
            // 암호화폐 데이터는 더 자주 업데이트 (1분마다)
            const hasVipAccess = {str(has_vip_access).lower()};
            if (hasVipAccess) {{
                setInterval(loadCryptoData, 60 * 1000);
            }}
            
            // 터치 최적화 및 제스처 기능
            let lastScrollTop = 0;
            const appBar = document.querySelector('.app-bar');
            
            // 스크롤 감지로 앱바 애니메이션
            window.addEventListener('scroll', function() {{
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                
                if (scrollTop > lastScrollTop && scrollTop > 100) {{
                    // 아래로 스크롤 - 앱바 축소
                    appBar.classList.add('scrolled');
                }} else {{
                    // 위로 스크롤 - 앱바 확장
                    appBar.classList.remove('scrolled');
                }}
                
                lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
            }});
            
            // Pull-to-refresh 기능
            let startY = 0;
            let currentY = 0;
            let pullToRefreshThreshold = 60;
            let isPulling = false;
            
            document.addEventListener('touchstart', function(e) {{
                startY = e.touches[0].pageY;
            }});
            
            document.addEventListener('touchmove', function(e) {{
                currentY = e.touches[0].pageY;
                
                if (window.scrollY === 0 && currentY > startY) {{
                    const pullDistance = currentY - startY;
                    isPulling = pullDistance > 10;
                    
                    if (pullDistance > pullToRefreshThreshold) {{
                        // 새로고침 준비 상태 표시
                        document.body.style.transform = `translateY(${{Math.min(pullDistance / 3, 20)}}px)`;
                        document.body.style.transition = 'none';
                    }}
                }}
            }});
            
            document.addEventListener('touchend', function(e) {{
                if (isPulling && (currentY - startY) > pullToRefreshThreshold) {{
                    // Pull-to-refresh 실행
                    document.body.style.transform = 'translateY(20px)';
                    document.body.style.transition = 'transform 0.3s ease';
                    
                    setTimeout(() => {{
                        loadDashboardData();
                        document.body.style.transform = 'translateY(0)';
                        
                        setTimeout(() => {{
                            document.body.style.transition = '';
                        }}, 300);
                    }}, 300);
                }} else {{
                    document.body.style.transform = 'translateY(0)';
                    document.body.style.transition = 'transform 0.3s ease';
                    setTimeout(() => {{
                        document.body.style.transition = '';
                    }}, 300);
                }}
                
                isPulling = false;
            }});
            
            // 햅틱 피드백 (iOS Safari)
            document.querySelectorAll('.slider-card, .hero-card, .nav-item').forEach(element => {{
                element.addEventListener('touchstart', function() {{
                    if (navigator.vibrate) {{
                        navigator.vibrate(10); // 가벼운 햅틱
                    }}
                }});
            }});
            
            // 탭 선택 및 서브 버튼 제어 시스템
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
                                  'navigateToTaskList()', 'showQuickTaskModal()');
                    updateTabState('task');
                }} else if (tabType === 'profit') {{
                    // 손익 탭 선택
                    showSubButtons('💰', '손익 목록', '💳', '손익 등록', 
                                  'navigateToProfitLoss()', 'showProfitModal()');
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
            
            // 네비게이션 함수들
            function navigateToHome() {{
                window.location.href = '/main-dashboard';
            }}
            
            function navigateToTaskList() {{
                window.location.href = '/task-list';
            }}
            
            function navigateToProfitLoss() {{
                window.location.href = '/profit-loss';
            }}
            
            function showMenuModal() {{
                document.getElementById('menuModal').style.display = 'block';
            }}
            
            function hideMenuModal() {{
                document.getElementById('menuModal').style.display = 'none';
            }}
            
            // === 지출 내역 모달 관련 함수들 ===
            function showExpenseModal() {{
                document.getElementById('expenseModal').style.display = 'block';
                
                // 현재 시간으로 초기화
                const now = new Date();
                const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
                document.getElementById('expenseDate').value = localDate.toISOString().slice(0, 16);
                
                // 활성 업무 목록 로드
                loadActiveTasks();
            }}
            
            function hideExpenseModal() {{
                document.getElementById('expenseModal').style.display = 'none';
                
                // 폼 초기화
                document.getElementById('expenseForm').reset();
                document.getElementById('categoryNote').style.display = 'none';
                document.getElementById('expenseTaskSelect').disabled = false;
            }}
            
            // 활성 업무 목록 로드
            async function loadActiveTasks() {{
                try {{
                    const response = await fetch('/api/business/tasks/active');
                    const data = await response.json();
                    
                    const select = document.getElementById('expenseTaskSelect');
                    select.innerHTML = '<option value="">업무를 선택하세요</option>';
                    
                    if (data.success && data.tasks) {{
                        data.tasks.forEach(task => {{
                            const option = document.createElement('option');
                            option.value = task.id;
                            option.textContent = `[${{task.category}}] ${{task.title}}`;
                            select.appendChild(option);
                        }});
                    }}
                }} catch (error) {{
                    console.error('활성 업무 로드 실패:', error);
                }}
            }}
            
            // 업무 검색
            async function searchTasks() {{
                const query = document.getElementById('taskSearchInput').value.trim();
                if (!query) {{
                    await loadActiveTasks();
                    return;
                }}
                
                try {{
                    const response = await fetch(`/api/business/tasks/search?query=${{encodeURIComponent(query)}}`);
                    const data = await response.json();
                    
                    const select = document.getElementById('expenseTaskSelect');
                    select.innerHTML = '<option value="">업무를 선택하세요</option>';
                    
                    if (data.success && data.tasks) {{
                        data.tasks.forEach(task => {{
                            const option = document.createElement('option');
                            option.value = task.id;
                            const statusText = task.status === '완료' ? ' (완료)' : '';
                            option.textContent = `[${{task.category}}] ${{task.title}}${{statusText}}`;
                            select.appendChild(option);
                        }});
                        
                        showToast(`${{data.tasks.length}}개의 업무를 찾았습니다.`, 'info');
                    }} else {{
                        showToast('검색 결과가 없습니다.', 'info');
                    }}
                }} catch (error) {{
                    console.error('업무 검색 실패:', error);
                    showToast('업무 검색 중 오류가 발생했습니다.', 'error');
                }}
            }}
            
            // 카테고리 변경 처리
            function handleCategoryChange() {{
                const category = document.getElementById('expenseCategory').value;
                const taskSelect = document.getElementById('expenseTaskSelect');
                const categoryNote = document.getElementById('categoryNote');
                
                if (category === '일반') {{
                    taskSelect.disabled = true;
                    taskSelect.value = '';
                    categoryNote.style.display = 'block';
                }} else {{
                    taskSelect.disabled = false;
                    categoryNote.style.display = 'none';
                }}
            }}
            
            // 지출 저장
            async function saveExpense() {{
                const saveBtn = document.querySelector('.expense-btn-save');
                const originalText = saveBtn.textContent;
                
                // 유효성 검사
                const taskId = document.getElementById('expenseTaskSelect').value;
                const category = document.getElementById('expenseCategory').value;
                const title = document.getElementById('expenseTitle').value.trim();
                const amount = document.getElementById('expenseAmount').value;
                const expenseDate = document.getElementById('expenseDate').value;
                const description = document.getElementById('expenseDescription').value.trim();
                
                if (!category) {{
                    alert('카테고리를 선택해주세요.');
                    return;
                }}
                
                if (!title) {{
                    alert('지출 제목을 입력해주세요.');
                    return;
                }}
                
                if (!amount || parseFloat(amount) <= 0) {{
                    alert('올바른 금액을 입력해주세요.');
                    return;
                }}
                
                if (!expenseDate) {{
                    alert('지출 일시를 선택해주세요.');
                    return;
                }}
                
                // 일반 카테고리가 아닌데 업무를 선택하지 않은 경우
                if (category !== '일반' && !taskId) {{
                    alert('이 카테고리는 업무 선택이 필요합니다.');
                    return;
                }}
                
                try {{
                    saveBtn.disabled = true;
                    saveBtn.textContent = '저장 중...';
                    
                    const expenseData = {{
                        task_id: taskId || null,
                        category,
                        amount: parseFloat(amount),
                        description: title,
                        expense_date: expenseDate.split('T')[0], // YYYY-MM-DD 형식
                        participants_internal: null,
                        participants_external: 0,
                        external_note: description || null
                    }};
                    
                    const response = await fetch('/api/business/expenses', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify(expenseData)
                    }});
                    
                    if (response.ok) {{
                        hideExpenseModal();
                        showToast('지출이 성공적으로 등록되었습니다!', 'success');
                        // 재무 현황 다시 로드
                        setTimeout(loadFinancialData, 500);
                    }} else {{
                        const error = await response.json();
                        alert('오류: ' + (error.detail || '지출 등록에 실패했습니다.'));
                    }}
                }} catch (error) {{
                    console.error('지출 등록 오류:', error);
                    alert('지출 등록 중 오류가 발생했습니다.');
                }} finally {{
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }}
            }}
            
            // 손익 등록 모달 관련 함수들
            function showProfitModal() {{
                document.getElementById('profitModal').style.display = 'block';
                
                // 현재 시간으로 초기화
                const now = new Date();
                const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
                document.getElementById('profitDate').value = localDate.toISOString().slice(0, 16);
                
                // 활성 업무 목록 로드 (손익용)
                loadActiveProfitTasks();
            }}
            
            function hideProfitModal() {{
                document.getElementById('profitModal').style.display = 'none';
                
                // 폼 초기화
                document.getElementById('profitForm').reset();
                document.getElementById('profitCategoryNote').style.display = 'none';
                document.getElementById('profitTaskSelect').disabled = false;
                
                // 추가 초기화
                document.getElementById('profitAmountKorean').textContent = '';
                document.getElementById('profitTypeExpense').checked = true; // 기본값을 지출로 설정
                
                // 카테고리 라벨을 지출로 초기화
                const categoryLabel = document.querySelector('#profitModal .form-group:nth-of-type(3) .form-label');
                categoryLabel.textContent = '지출 종류 *';
                const categorySelect = document.getElementById('profitCategory');
                categorySelect.getElementsByTagName('option')[0].textContent = '지출 종류를 선택하세요';
            }}
            
            // 활성 업무 목록 로드 (손익용)
            async function loadActiveProfitTasks() {{
                try {{
                    const response = await fetch('/api/business/tasks?status=대기,진행중&limit=50');
                    const data = await response.json();
                    
                    const select = document.getElementById('profitTaskSelect');
                    select.innerHTML = '<option value="">업무를 선택하세요</option>';
                    
                    if (data.success && data.tasks) {{
                        // 대기, 진행중 상태의 업무만 필터링
                        const activeTasks = data.tasks.filter(task => 
                            task.status === '대기' || task.status === '진행중'
                        );
                        
                        activeTasks.forEach(task => {{
                            const option = document.createElement('option');
                            option.value = task.id;
                            option.textContent = `${{task.title}} (${{task.category}})`;
                            select.appendChild(option);
                        }});
                    }}
                }} catch (error) {{
                    console.error('업무 목록 로딩 실패:', error);
                    // 에러 발생 시 사용자에게 알림
                    const select = document.getElementById('profitTaskSelect');
                    select.innerHTML = '<option value="">업무 목록을 불러올 수 없습니다</option>';
                }}
            }}
            
            // 손익 업무 검색
            function searchProfitTasks() {{
                const searchInput = document.getElementById('profitTaskSearchInput');
                const taskSelect = document.getElementById('profitTaskSelect');
                const searchTerm = searchInput.value.toLowerCase();
                
                Array.from(taskSelect.options).forEach(option => {{
                    if (option.value === '') return; // 첫 번째 옵션 제외
                    
                    const isMatch = option.textContent.toLowerCase().includes(searchTerm);
                    option.style.display = isMatch ? 'block' : 'none';
                }});
            }}
            
            // 숫자 입력만 허용하는 함수
            function isNumberKey(evt) {{
                var charCode = (evt.which) ? evt.which : evt.keyCode;
                if (charCode != 46 && charCode > 31 && (charCode < 48 || charCode > 57))
                    return false;
                return true;
            }}
            
            // 금액 입력 포맷팅 함수
            function formatAmountInput(input) {{
                // 숫자만 추출
                let value = input.value.replace(/[^0-9]/g, '');
                
                if (value === '') {{
                    input.value = '';
                    document.getElementById('profitAmountKorean').textContent = '';
                    return;
                }}
                
                // 쉼표 추가
                let formattedValue = parseInt(value).toLocaleString();
                input.value = formattedValue;
                
                // 한글 변환
                let koreanText = numberToKorean(parseInt(value));
                document.getElementById('profitAmountKorean').textContent = koreanText;
            }}
            
            // 숫자를 한글로 변환하는 함수
            function numberToKorean(num) {{
                if (num === 0) return '영원';
                
                const units = ['', '만', '억', '조', '경'];
                const digits = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구'];
                const tens = ['', '십', '이십', '삼십', '사십', '오십', '육십', '칠십', '팔십', '구십'];
                const hundreds = ['', '일백', '이백', '삼백', '사백', '오백', '육백', '칠백', '팔백', '구백'];
                const thousands = ['', '일천', '이천', '삼천', '사천', '오천', '육천', '칠천', '팔천', '구천'];
                
                let result = '';
                let unitIndex = 0;
                
                while (num > 0) {{
                    let part = num % 10000;
                    if (part > 0) {{
                        let partStr = '';
                        
                        // 천의 자리
                        if (Math.floor(part / 1000) > 0) {{
                            partStr += thousands[Math.floor(part / 1000)];
                        }}
                        
                        // 백의 자리
                        if (Math.floor((part % 1000) / 100) > 0) {{
                            partStr += hundreds[Math.floor((part % 1000) / 100)];
                        }}
                        
                        // 십의 자리
                        if (Math.floor((part % 100) / 10) > 0) {{
                            if (Math.floor((part % 100) / 10) === 1 && part >= 10) {{
                                partStr += '십';
                            }} else {{
                                partStr += tens[Math.floor((part % 100) / 10)];
                            }}
                        }}
                        
                        // 일의 자리
                        if (part % 10 > 0) {{
                            partStr += digits[part % 10];
                        }}
                        
                        result = partStr + units[unitIndex] + result;
                    }}
                    
                    num = Math.floor(num / 10000);
                    unitIndex++;
                }}
                
                return result + '원';
            }}
            
            // 손익 유형 변경 처리
            function handleProfitTypeChange() {{
                const profitType = document.querySelector('input[name="profitType"]:checked').value;
                const categoryLabel = document.querySelector('#profitModal .form-group:nth-of-type(3) .form-label');
                const categorySelect = document.getElementById('profitCategory');
                
                if (profitType === '수익') {{
                    categoryLabel.textContent = '수익 종류 *';
                    categorySelect.getElementsByTagName('option')[0].textContent = '수익 종류를 선택하세요';
                }} else {{
                    categoryLabel.textContent = '지출 종류 *';
                    categorySelect.getElementsByTagName('option')[0].textContent = '지출 종류를 선택하세요';
                }}
            }}
            
            // 손익 카테고리 변경 처리
            function handleProfitCategoryChange() {{
                const category = document.getElementById('profitCategory').value;
                const taskSelect = document.getElementById('profitTaskSelect');
                const categoryNote = document.getElementById('profitCategoryNote');
                
                if (category === '일반') {{
                    taskSelect.disabled = true;
                    taskSelect.value = '';
                    categoryNote.style.display = 'block';
                }} else {{
                    taskSelect.disabled = false;
                    categoryNote.style.display = 'none';
                }}
            }}
            
            // 손익 저장
            async function saveProfit() {{
                const saveBtn = document.querySelector('#profitModal .expense-btn-save');
                const originalText = saveBtn.textContent;
                
                // 유효성 검사
                const profitType = document.querySelector('input[name="profitType"]:checked');
                const taskId = document.getElementById('profitTaskSelect').value;
                const category = document.getElementById('profitCategory').value;
                const title = document.getElementById('profitTitle').value.trim();
                const amountInput = document.getElementById('profitAmount').value;
                const profitDate = document.getElementById('profitDate').value;
                const description = document.getElementById('profitDescription').value.trim();
                
                // 손익 유형 체크
                if (!profitType) {{
                    alert('손익 유형을 선택해주세요.');
                    return;
                }}
                
                if (!category) {{
                    const categoryType = profitType.value === '수익' ? '수익 종류' : '지출 종류';
                    alert(`${{categoryType}}를 선택해주세요.`);
                    return;
                }}
                
                if (!title) {{
                    alert('손익 제목을 입력해주세요.');
                    return;
                }}
                
                // 금액 검증 (쉼표 제거 후 숫자 변환)
                if (!amountInput) {{
                    alert('손익 금액을 입력해주세요.');
                    return;
                }}
                
                const cleanAmount = amountInput.replace(/,/g, '');
                const amount = parseFloat(cleanAmount);
                
                if (isNaN(amount) || amount <= 0) {{
                    alert('올바른 금액을 입력해주세요.');
                    return;
                }}
                
                if (!profitDate) {{
                    alert('손익 일시를 선택해주세요.');
                    return;
                }}
                
                if (!description) {{
                    alert('설명을 입력해주세요.');
                    return;
                }}
                
                // 일반 카테고리가 아닌데 업무를 선택하지 않은 경우
                if (category !== '일반' && !taskId) {{
                    alert('이 카테고리는 업무 선택이 필요합니다.');
                    return;
                }}
                
                try {{
                    saveBtn.disabled = true;
                    saveBtn.textContent = '저장 중...';
                    
                    // 수익/지출에 따른 금액 부호 설정
                    const finalAmount = profitType.value === '수익' ? amount : -amount;
                    
                    const profitData = {{
                        task_id: taskId || null,
                        type: profitType.value,
                        category,
                        amount: finalAmount,
                        title: title,
                        description: description,
                        profit_date: profitDate.split('T')[0], // YYYY-MM-DD 형식
                        raw_amount: cleanAmount // 원본 금액 (쉼표 제거된)
                    }};
                    
                    console.log('손익 등록 데이터:', profitData);
                    
                    // TODO: 실제 API 엔드포인트가 구현되면 사용
                    // const response = await fetch('/api/business/profits', {{
                    //     method: 'POST',
                    //     headers: {{
                    //         'Content-Type': 'application/json'
                    //     }},
                    //     body: JSON.stringify(profitData)
                    // }});
                    
                    // 임시로 성공 처리 (실제 API가 준비되면 주석 해제)
                    hideProfitModal();
                    const typeText = profitType.value === '수익' ? '수익' : '지출';
                    showToast(`${{typeText}}이 성공적으로 등록되었습니다!`, 'success');
                    // 재무 현황 다시 로드
                    setTimeout(loadFinancialData, 500);
                    
                }} catch (error) {{
                    console.error('손익 등록 오류:', error);
                    alert('손익 등록 중 오류가 발생했습니다.');
                }} finally {{
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }}
            }}
            
            // 모달 외부 클릭시 닫기
            window.addEventListener('click', function(event) {{
                const menuModal = document.getElementById('menuModal');
                if (event.target === menuModal) {{
                    hideMenuModal();
                }}
                
                const quickTaskModal = document.getElementById('quickTaskModal');
                if (event.target === quickTaskModal) {{
                    hideQuickTaskModal();
                }}
                
                const expenseModal = document.getElementById('expenseModal');
                if (event.target === expenseModal) {{
                    hideExpenseModal();
                }}
                
                const profitModal = document.getElementById('profitModal');
                if (event.target === profitModal) {{
                    hideProfitModal();
                }}
            }});
            
            // ESC 키로 모달 닫기
            document.addEventListener('keydown', function(event) {{
                if (event.key === 'Escape') {{
                    const quickTaskModal = document.getElementById('quickTaskModal');
                    const expenseModal = document.getElementById('expenseModal');
                    const profitModal = document.getElementById('profitModal');
                    const menuModal = document.getElementById('menuModal');
                    
                    if (expenseModal.style.display === 'block') {{
                        hideExpenseModal();
                    }} else if (profitModal.style.display === 'block') {{
                        hideProfitModal();
                    }} else if (quickTaskModal.style.display === 'block') {{
                        hideQuickTaskModal();
                    }} else if (menuModal.style.display === 'block') {{
                        hideMenuModal();
                    }}
                }}
            }});
            
            // 슬라이더 터치 제스처 개선
            const sliderContainers = document.querySelectorAll('.slider-container');
            sliderContainers.forEach(container => {{
                let startX = 0;
                let scrollLeft = 0;
                
                container.addEventListener('touchstart', function(e) {{
                    startX = e.touches[0].pageX - container.offsetLeft;
                    scrollLeft = container.scrollLeft;
                }});
                
                container.addEventListener('touchmove', function(e) {{
                    if (!startX) return;
                    e.preventDefault();
                    
                    const x = e.touches[0].pageX - container.offsetLeft;
                    const walk = (x - startX) * 2;
                    container.scrollLeft = scrollLeft - walk;
                }});
                
                container.addEventListener('touchend', function() {{
                    startX = 0;
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html_content)