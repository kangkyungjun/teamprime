#!/usr/bin/env python3
"""사용자 데이터 복원 스크립트 - JSON에서 MySQL로 복원"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from core.database.mysql_connection import get_mysql_session
from core.auth.models import User
from sqlalchemy import select

async def restore_users(backup_filename):
    """JSON 백업 파일에서 MySQL로 사용자 데이터 복원"""
    try:
        # 백업 파일 읽기
        print(f"📁 백업 파일 로드: {backup_filename}")
        
        with open(backup_filename, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        print(f"📅 백업 날짜: {backup_data.get('backup_date')}")
        print(f"📊 복원할 사용자 수: {len(backup_data['users'])}")
        
        restored_count = 0
        skipped_count = 0
        
        async with get_mysql_session() as session:
            for user_data in backup_data['users']:
                try:
                    # 기존 사용자 확인 (중복 방지)
                    existing_user = await session.execute(
                        select(User).where(
                            (User.username == user_data['username']) | 
                            (User.email == user_data['email'])
                        )
                    )
                    
                    if existing_user.scalar_one_or_none():
                        print(f"⚠️  건너뜀: {user_data['username']} (이미 존재)")
                        skipped_count += 1
                        continue
                    
                    # 새 사용자 생성
                    new_user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        password_hash=user_data['password_hash'],
                        is_active=user_data.get('is_active', True)
                    )
                    
                    # 날짜 정보 복원 (가능한 경우)
                    if user_data.get('created_at'):
                        new_user.created_at = datetime.fromisoformat(user_data['created_at'])
                    if user_data.get('updated_at'):
                        new_user.updated_at = datetime.fromisoformat(user_data['updated_at'])
                    if user_data.get('last_login'):
                        new_user.last_login = datetime.fromisoformat(user_data['last_login'])
                    
                    session.add(new_user)
                    await session.commit()
                    
                    print(f"✅ 복원: {user_data['username']} ({user_data['email']})")
                    restored_count += 1
                    
                except Exception as e:
                    print(f"❌ {user_data['username']} 복원 실패: {str(e)}")
                    await session.rollback()
        
        print(f"\n🎉 복원 완료!")
        print(f"✅ 복원된 사용자: {restored_count}명")
        print(f"⚠️  건너뛴 사용자: {skipped_count}명")
        
        return restored_count
        
    except FileNotFoundError:
        print(f"❌ 백업 파일을 찾을 수 없습니다: {backup_filename}")
        return 0
    except Exception as e:
        print(f"❌ 복원 실패: {str(e)}")
        return 0

async def list_backup_files():
    """백업 파일 목록 표시"""
    import glob
    backup_files = glob.glob("users_backup_*.json")
    
    if backup_files:
        print("📁 사용 가능한 백업 파일:")
        for i, filename in enumerate(sorted(backup_files, reverse=True), 1):
            print(f"  {i}. {filename}")
        return backup_files
    else:
        print("❌ 백업 파일이 없습니다. 먼저 backup_users.py를 실행해주세요.")
        return []

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 파일명이 직접 제공된 경우
        backup_filename = sys.argv[1]
        asyncio.run(restore_users(backup_filename))
    else:
        # 대화형 모드
        print("🔄 사용자 데이터 복원 도구")
        print("=" * 50)
        
        backup_files = asyncio.run(list_backup_files())
        
        if backup_files:
            try:
                choice = input("\n복원할 백업 파일 번호를 입력하세요 (또는 전체 파일명): ")
                
                if choice.isdigit():
                    # 번호로 선택
                    file_index = int(choice) - 1
                    if 0 <= file_index < len(backup_files):
                        selected_file = sorted(backup_files, reverse=True)[file_index]
                    else:
                        print("❌ 잘못된 번호입니다.")
                        sys.exit(1)
                else:
                    # 파일명으로 선택
                    selected_file = choice
                
                print(f"\n선택된 파일: {selected_file}")
                confirm = input("복원을 진행하시겠습니까? (y/N): ")
                
                if confirm.lower() == 'y':
                    asyncio.run(restore_users(selected_file))
                else:
                    print("취소되었습니다.")
                    
            except KeyboardInterrupt:
                print("\n취소되었습니다.")
            except Exception as e:
                print(f"❌ 오류 발생: {str(e)}")