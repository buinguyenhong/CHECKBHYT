import hashlib
import os
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User

# Hashing mật khẩu bằng standard library (PBKDF2 SHA256) nhằm loại bỏ sự phụ thuộc vào bcrypt
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + key.hex()

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        salt_hex, key_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return new_key == key
    except Exception:
        return False

# Cookie-based session management
SESSION_COOKIE_NAME = "checkbh_session"

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Dependency lấy thông tin User hiện tại từ session cookie
    """
    username = request.cookies.get(SESSION_COOKIE_NAME)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập hệ thống"
        )
        
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không hợp lệ hoặc đã bị xóa"
        )
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency bắt buộc người dùng phải là Quản trị viên (Phòng IT)
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Chỉ dành cho phòng IT."
        )
    return user
