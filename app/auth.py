# app/auth.py
from passlib.hash import bcrypt
from db import create_user, get_user_by_email

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)

def ensure_default_users():
    # crea utenti di esempio (solo se non esistono)
    admin = get_user_by_email("admin@example.com")
    if not admin:
        create_user("admin@example.com", hash_password("admin123"), name="Admin")
    user = get_user_by_email("user@example.com")
    if not user:
        create_user("user@example.com", hash_password("user123"), name="User")
