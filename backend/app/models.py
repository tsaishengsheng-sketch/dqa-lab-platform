from sqlalchemy import (
    create_engine,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column
import datetime
import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_db_url = os.getenv("DATABASE_URL")
SQLALCHEMY_DATABASE_URL = _db_url if _db_url else f"sqlite:///{BASE_DIR}/test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ---------- 使用者（多用戶權限）----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="engineer")
    # role: admin / keeper / engineer
    line_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    loan_limit: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


# ---------- 治具基本資料 ----------
class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interface_type: Mapped[str] = mapped_column(
        String, index=True
    )  # 介面類型（Ethernet/Fiber/USB...）
    form_factor: Mapped[str] = mapped_column(String)  # 型態
    size: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 長度/大小
    purpose: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 用途
    estimated_usage: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 預估使用量
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)  # 現有數量
    shortage: Mapped[int] = mapped_column(Integer, default=0)  # 缺貨數量
    # 使用率：1=每天, 2=週, 3=月, 4=季, 5=年
    usage_frequency: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 建議汰換時間：0.5年/1年/2年/3年/量測
    replacement_years: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keeper_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Lab Eng（保管人）
    deputy_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # Lab Sup（代理人）
    vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 廠商
    model_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 型號
    spec: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 規格
    lead_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 交期
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 費用
    loan_count: Mapped[int] = mapped_column(Integer, default=0)  # 借出次數累計
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    __table_args__ = (Index("ix_fixtures_interface_type", "interface_type"),)

    @property
    def available_quantity(self) -> int:
        """可借數 = 總數 - 借出中 - 損壞（由 API 層計算）"""
        return self.total_quantity


# ---------- 治具借出紀錄 ----------
class FixtureLoan(Base):
    __tablename__ = "fixture_loans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    borrower_name: Mapped[str] = mapped_column(String)  # 借用人姓名
    borrower_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # 綁定設備（KSON_CH01~05）
    project_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # 樣品/專案名稱
    quantity: Mapped[int] = mapped_column(Integer, default=1)  # 借出數量
    loan_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    due_date: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )  # 預計歸還日
    return_date: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )  # 實際歸還日
    # status: reserved/loaned/returned/damaged/lost/scrapped
    status: Mapped[str] = mapped_column(String, default="loaned", index=True)
    return_condition: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # 歸還狀態：normal/damaged/lost
    extension_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # 延期申請紀錄
    keeper_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # 保管人備註
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    __table_args__ = (
        Index("ix_fixture_loans_status", "status"),
        Index("ix_fixture_loans_due_date", "due_date"),
    )


# ---------- 採購紀錄 ----------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vendor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # status: pending/ordered/arrived/cancelled
    status: Mapped[str] = mapped_column(String, default="pending")
    ordered_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    arrived_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


# ---------- SOP 模板 ----------
class SopTemplate(Base):
    __tablename__ = "sop_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sop_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    test_type: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


# ---------- SOP 執行主表 ----------
class SopExecution(Base):
    __tablename__ = "sop_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sop_id: Mapped[str] = mapped_column(String, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    operator: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    test_started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    test_ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


# ---------- SOP 步驟記錄 ----------
class StepRecord(Base):
    __tablename__ = "step_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("sop_executions.id"), index=True
    )
    step_id: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    parameters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------- 裝置數據記錄 ----------
class DeviceData(Base):
    __tablename__ = "device_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_device_data_device_timestamp", "device_id", "timestamp"),
    )


# ---------- 設備狀態持久化 ----------
class DeviceState(Base):
    __tablename__ = "device_states"

    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="IDLE")
    temperature: Mapped[float] = mapped_column(Float, default=25.0)
    humidity: Mapped[float] = mapped_column(Float, default=55.0)
    running_sop_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    running_sop_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    standard_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active_sop_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


# ---------- 異常紀錄 ----------
class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String, index=True)
    error_type: Mapped[str] = mapped_column(String)
    sop_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sop_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


# ---------- 資料庫初始化 ----------
def init_db():
    Base.metadata.create_all(bind=engine)
