# backend/init_db.py
# ⚠️ 注意：此檔案僅供首次建立資料庫使用。
# 後續 DB 結構變更請使用 Alembic：
#   alembic revision --autogenerate -m "描述變更"
#   alembic upgrade head
#
# 密碼恢復：若忘記 admin 密碼，可設定 ADMIN_PASSWORD 環境變數後重新執行此腳本。
# 若未設定 ADMIN_PASSWORD，預設使用 "admin123" 作為恢復密碼。
import os
from app.models import Base, engine, SessionLocal, User
from app.auth import hash_password

print("正在建立資料表...")
Base.metadata.create_all(bind=engine)
print("✅ 資料表建立完成！")

# Use ADMIN_PASSWORD env var if set; fall back to the well-known recovery value.
_pwd = os.getenv("ADMIN_PASSWORD", "admin123")

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == "admin").first()
    if admin is None:
        db.add(User(
            username="admin",
            display_name="Admin",
            hashed_password=hash_password(_pwd),
            role="admin",
            is_active=True,
        ))
        db.commit()
        print("✅ Admin 帳號建立完成！")
    else:
        admin.hashed_password = hash_password(_pwd)
        admin.is_active = True
        db.commit()
        print("✅ Admin 帳號密碼已重設！")
finally:
    db.close()

