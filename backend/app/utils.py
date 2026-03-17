# 共用工具函式，供 main.py 與 sop.py 共同使用
# 抽離至此避免 sop.py → main.py 的 circular import

import datetime
from .models import SessionLocal, DeviceState


def _now_utc() -> datetime.datetime:
    """統一使用 UTC aware datetime"""
    return datetime.datetime.now(datetime.timezone.utc)


def _save_device_state(device_id: str, item: dict):
    """
    將目前設備狀態寫回 DB，供重啟後恢復使用
    :param device_id: 設備 ID
    :param item: 目前的設備狀態字典（包含 status、temperature、humidity 等）
    """
    with SessionLocal() as db:
        state = db.get(DeviceState, device_id)
        if state is None:
            # 如果設備狀態不存在，創建新紀錄
            state = DeviceState(device_id=device_id)
            db.add(state)

        # 更新設備狀態
        state.status = item.get("status", "IDLE")
        state.temperature = item.get("temperature", 25.0)
        state.humidity = item.get("humidity", 55.0)
        state.running_sop_id = item.get("running_sop_id")
        state.running_sop_name = item.get("running_sop_name")
        state.standard_id = item.get("standard_id")
        state.active_sop_json = item.get("active_sop_json")
        state.completed_steps = item.get("completed_steps", 0)

        # 記錄更新時間
        state.updated_at = _now_utc()

        # 提交變更
        db.commit()
