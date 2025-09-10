"""
사용자 인증 관련 SQLAlchemy 모델 - 간소화 (보안 강화)
- User: 사용자 기본 정보만 저장 (API 키 저장 제거)
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database.mysql_connection import Base

class User(Base):
    """사용자 모델"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', nullable=False)  # 역할 추가
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    
    # 관계 설정 제거됨 - API 키와 세션 테이블 삭제
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """딕셔너리로 변환 (민감한 정보 제외)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,  # 역할 정보 추가
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }

# UserAPIKeys와 UserSession 모델 제거됨 - 보안 강화를 위해 API 키 저장하지 않음