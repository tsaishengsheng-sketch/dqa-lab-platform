import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from .models import SessionLocal, ErrorLog

# 定義異常紀錄路由器
router = APIRouter(prefix="/api/errors", tags=["errors"])


class ErrorLogResponse(BaseModel):
    """異常紀錄的回應類別"""

    # 異常紀錄 ID
    id: int

    # 設備 ID
    device_id: str

    # 異常類型（例如急停、溫箱故障等）
    error_type: str

    # 當前正在執行的 SOP ID（選填）
    sop_id: Optional[str] = None

    # 當前正在執行的 SOP 名稱（選填）
    sop_name: Optional[str] = None

    # 當前溫度值（選填）
    temperature: Optional[float] = None

    # 當前濕度值（選填）
    humidity: Optional[float] = None

    # 附加注釋（選填）
    note: Optional[str] = None

    # 異常紀錄創建時間，自動序列化為 ISO 8601
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# 取得所有異常紀錄的路由器
@router.get("/", response_model=list[ErrorLogResponse])
def list_errors():
    """取得所有異常紀錄，最新在前"""

    # 連接資料庫
    with SessionLocal() as db:
        # 取得所有異常紀錄，按時間排序倒序
        logs = db.query(ErrorLog).order_by(ErrorLog.created_at.desc()).all()

        # 回傳異常紀錄列表
        return logs
