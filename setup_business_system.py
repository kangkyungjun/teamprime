#!/usr/bin/env python3
"""
비즈니스 관리 시스템 초기 설정 스크립트
- 데이터베이스 마이그레이션 실행
- Owner 계정 생성 및 확인
- 시스템 초기화
"""

import asyncio
import logging
from core.database.migration import run_migration, check_tables_exist
from core.auth.owner_system import owner_system

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def setup_business_system():
    """비즈니스 관리 시스템 전체 설정"""
    logger.info("🚀 비즈니스 관리 시스템 초기 설정 시작")
    
    try:
        # 1. 데이터베이스 마이그레이션 실행
        logger.info("📊 데이터베이스 마이그레이션 실행 중...")
        await run_migration()
        logger.info("✅ 데이터베이스 마이그레이션 완료")
        
        # 2. 테이블 존재 확인
        logger.info("🔍 데이터베이스 테이블 확인 중...")
        tables_exist = await check_tables_exist()
        if tables_exist:
            logger.info("✅ 모든 필수 테이블 확인 완료")
        else:
            logger.error("❌ 일부 테이블이 누락되었습니다")
            return False
        
        # 3. Owner 계정 설정
        logger.info("👑 Owner 계정 설정 중...")
        owner_created = await owner_system.ensure_owner_exists()
        if owner_created:
            logger.info(f"✅ Owner 계정 확인 완료: {owner_system.owner_email}")
        else:
            logger.error("❌ Owner 계정 설정 실패")
            return False
        
        # 4. 시스템 상태 확인
        logger.info("🔧 시스템 상태 확인 중...")
        owner_user = await owner_system.get_user_by_email(owner_system.owner_email)
        if owner_user:
            logger.info(f"✅ Owner 정보 확인:")
            logger.info(f"   - ID: {owner_user['id']}")
            logger.info(f"   - Username: {owner_user['username']}")
            logger.info(f"   - Email: {owner_user['email']}")
            logger.info(f"   - Role: {owner_user['role']}")
            logger.info(f"   - Active: {owner_user['is_active']}")
        
        # 5. 권한 확인
        if owner_user:
            permissions = owner_system.get_role_permissions(owner_user['role'])
            logger.info("✅ Owner 권한 매트릭스:")
            for perm, value in permissions.items():
                status = "✅" if value else "❌"
                logger.info(f"   - {perm}: {status}")
        
        logger.info("🎉 비즈니스 관리 시스템 초기 설정 완료!")
        logger.info("📝 다음 단계:")
        logger.info("   1. 웹 인터페이스에서 Owner 로그인")
        logger.info("   2. Prime 사용자 승급")
        logger.info("   3. 업무 및 지출 관리 시작")
        logger.info("   4. VIP 암호화폐 거래 서비스 이용")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 비즈니스 시스템 설정 실패: {str(e)}")
        return False

async def test_system_integration():
    """시스템 통합 테스트"""
    logger.info("🧪 시스템 통합 테스트 시작")
    
    try:
        # Owner 권한 확인
        owner_user = await owner_system.get_user_by_email(owner_system.owner_email)
        if not owner_user:
            logger.error("❌ Owner 사용자를 찾을 수 없습니다")
            return False
        
        user_id = owner_user['id']
        
        # VIP 접근 권한 테스트
        has_vip = await owner_system.has_vip_access(user_id)
        logger.info(f"VIP 접근 권한: {'✅' if has_vip else '❌'}")
        
        # 사용자 승급 권한 테스트
        can_promote = await owner_system.can_promote_users(user_id)
        logger.info(f"사용자 승급 권한: {'✅' if can_promote else '❌'}")
        
        # 역할 확인
        role = await owner_system.get_user_role(user_id)
        logger.info(f"사용자 역할: {role}")
        
        logger.info("✅ 시스템 통합 테스트 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ 시스템 통합 테스트 실패: {str(e)}")
        return False

if __name__ == "__main__":
    async def main():
        # 1. 비즈니스 시스템 설정
        setup_success = await setup_business_system()
        
        if setup_success:
            # 2. 시스템 통합 테스트
            test_success = await test_system_integration()
            
            if test_success:
                logger.info("🎊 모든 설정과 테스트가 성공적으로 완료되었습니다!")
                logger.info("🚀 이제 비즈니스 관리 시스템을 사용할 수 있습니다.")
            else:
                logger.error("⚠️ 일부 테스트에서 문제가 발견되었습니다.")
        else:
            logger.error("❌ 시스템 설정에 실패했습니다.")
    
    asyncio.run(main())