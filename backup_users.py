#!/usr/bin/env python3
"""사용자 데이터 백업 스크립트 - MySQL에서 JSON으로 백업"""

import asyncio
import json
import logging
from datetime import datetime
from core.database.mysql_connection import get_mysql_session
from core.auth.models import User
from sqlalchemy import select

async def backup_users():
    """현재 MySQL 사용자 데이터를 JSON으로 백업"""
    try:
        backup_data = {
            "backup_date": datetime.now().isoformat(),
            "backup_type": "mysql_users",
            "users": []
        }
        
        async with get_mysql_session() as session:
            # 모든 사용자 조회
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            print(f"📊 백업할 사용자 수: {len(users)}")
            
            for user in users:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "password_hash": user.password_hash,  # 암호화된 상태로 보존
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                    "is_active": user.is_active,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
                backup_data["users"].append(user_data)
                print(f"✅ 백업: {user.username} ({user.email})")
        
        # JSON 파일로 저장
        backup_filename = f"users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 백업 완료: {backup_filename}")
        print(f"📁 총 {len(backup_data['users'])}명의 사용자 데이터가 백업되었습니다.")
        
        return backup_filename
        
    except Exception as e:
        print(f"❌ 백업 실패: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(backup_users())