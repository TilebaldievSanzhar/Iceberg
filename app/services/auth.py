from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate, Token
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, user_data: UserCreate) -> User:
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            User.email == user_data.email
        ).first()
        if existing_user:
            raise ValueError("User with this email already exists")

        # Create new user
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            name=user_data.name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_tokens(self, user: User) -> Token:
        return Token(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    def refresh_tokens(self, refresh_token: str) -> Optional[Token]:
        payload = verify_token(refresh_token, token_type="refresh")
        if payload is None:
            return None

        user = self.db.query(User).filter(User.id == payload.sub).first()
        if user is None:
            return None

        return self.create_tokens(user)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def update_user(self, user: User, name: Optional[str] = None, password: Optional[str] = None) -> User:
        if name:
            user.name = name
        if password:
            user.password_hash = get_password_hash(password)
        self.db.commit()
        self.db.refresh(user)
        return user
