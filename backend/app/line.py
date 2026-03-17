import os
import hmac
import hashlib
import base64
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

# 定義 LINE 模組的路由器
router = APIRouter(prefix="/api/line", tags=["line"])


# LINE API 的 URL 和標記
LINE_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")


def _verify_signature(body: bytes, signature: str) -> bool:
    """驗證來自 LINE 的 Webhook 請求簽名，確保請求來源合法"""
    # 使用標記和請求體計算出簽名
    hash_ = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()

    # 將計算出的簽名編碼為 base64，與實際的簽名進行比較
    expected = base64.b64encode(hash_).decode("utf-8")

    return hmac.compare_digest(expected, signature)


async def push_message(text: str):
    """主動推播訊息給指定 User ID"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("[LINE] 未設定 TOKEN 或 USER_ID，跳過推播")
        return

    async with httpx.AsyncClient() as client:
        try:
            # 發送請求到 LINE API
            res = await client.post(
                LINE_API_URL,
                headers={
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": LINE_USER_ID,
                    "messages": [{"type": "text", "text": text}],
                },
                timeout=10.0,
            )

            # 如果回應不是 200，就打印出錯誤訊息
            if res.status_code != 200:
                print(f"[LINE] 推播失敗：{res.status_code} {res.text}")
        except Exception as e:
            # 如果發生例外就打印出錯誤訊息
            print(f"[LINE] 推播例外：{e}")


def _handle_command(text: str, cache: dict) -> str:
    """處理使用者傳來的指令，回傳回覆文字"""

    # 將輸入的文字轉成小寫，並去除空白
    cmd = text.strip().lower()

    # 查詢所有設備狀態
    if cmd in ("狀態", "status", "s"):
        lines = ["📊 設備狀態\n"]

        # 取得各個設備的狀態
        for device_id, item in cache.items():
            status = item.get("status", "OFFLINE")
            temp = item.get("temperature", 0.0)
            emoji = {
                "RUNNING": "🟢",
                "PAUSED": "🟡",
                "EMERGENCY": "🔴",
                "FINISHING": "🔵",
                "IDLE": "⚪",
                "OFFLINE": "⚫",
            }.get(status, "⚫")
            lines.append(f"{emoji} {device_id}: {status} | {temp:.1f}°C")

        return "\n".join(lines)

    # 查詢單一設備
    for device_id in cache:
        short = device_id.replace("KSON_", "").lower()
        if cmd in (device_id.lower(), short):
            item = cache[device_id]
            status = item.get("status", "OFFLINE")
            temp = item.get("temperature", 0.0)
            humi = item.get("humidity", 0.0)
            sop = item.get("running_sop_name", "—")
            return (
                f"📟 {device_id}\n"
                f"狀態：{status}\n"
                f"溫度：{temp:.1f} °C\n"
                f"濕度：{humi:.1f} %RH\n"
                f"執行中：{sop}"
            )

    # 說明
    if cmd in ("help", "?", "幫助", "h"):
        return (
            "📋 可用指令\n\n"
            "狀態 / status — 查詢所有設備\n"
            "CH01 ~ CH05 — 查詢單一設備\n"
            "help — 顯示此說明"
        )

    return "❓ 未知指令，輸入 help 查看可用指令。"


# LINE Webhook 的路由器
@router.post("/webhook")
async def webhook(request: Request):
    """接收 LINE Webhook 事件"""

    # 取得請求體和簽名
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    import json

    # fix: 簽名驗證——必須有簽名且驗證通過才繼續
    # LINE Verify 請求帶的是空 events，驗證通過後直接回 200 即可
    if LINE_CHANNEL_SECRET:
        if not signature or not _verify_signature(body, signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

    # 取得 LINE 事件的資料
    data = json.loads(body)

    # 取得應用程式的快取資料
    cache = request.app.state.AICM_CACHE

    for event in data.get("events", []):
        # 只處理文字訊息
        if event.get("type") != "message":
            continue

        if event.get("message", {}).get("type") != "text":
            continue

        # fix: 白名單驗證，只允許指定 User ID 操作
        sender_id = event.get("source", {}).get("userId", "")
        if LINE_USER_ID and sender_id != LINE_USER_ID:
            continue  # 非授權使用者，靜默忽略

        user_text = event["message"]["text"]
        reply_token = event.get("replyToken")
        reply_text = _handle_command(user_text, cache)

        # 用回覆 token 回應
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.line.me/v2/bot/message/reply",
                headers={
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "replyToken": reply_token,
                    "messages": [{"type": "text", "text": reply_text}],
                },
                timeout=10.0,
            )

    return JSONResponse(content={"status": "ok"})
