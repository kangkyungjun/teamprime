#!/usr/bin/env python3
"""MySQL 사용자 데이터 확인 스크립트"""

import asyncio
import logging
from core.database.mysql_connection import get_mysql_session
from core.auth.models import User
from sqlalchemy import select

async def check_mysql_users():
    """MySQL에 등록된 사용자 확인"""
    try:
        async with get_mysql_session() as session:
            # 모든 사용자 조회
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            print(f"📊 MySQL에 등록된 사용자 수: {len(users)}")
            print("=" * 60)
            
            if users:
                for user in users:
                    print(f"ID: {user.id}")
                    print(f"사용자명: {user.username}")
                    print(f"이메일: {user.email}")
                    print(f"가입일: {user.created_at}")
                    print(f"마지막 로그인: {user.last_login}")
                    print(f"활성 상태: {user.is_active}")
                    print("-" * 40)
            else:
                print("등록된 사용자가 없습니다.")
                
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_mysql_users())