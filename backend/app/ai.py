import httpx
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from .standards import get_standard_tree

router = APIRouter(prefix="/api/ai", tags=["ai"])

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"

_SYSTEM_PROMPT_CACHE: Optional[str] = None


def _build_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is not None:
        return _SYSTEM_PROMPT_CACHE

    tree = get_standard_tree()
    lines = [
        "你是一位專業的工業環境測試法規顧問。",
        "【語言規則】無論使用者用任何語言提問，你的所有回覆必須100%使用繁體中文（Traditional Chinese）。",
        "【語言規則】絕對禁止使用簡體中文（Simplified Chinese）。繁體中文範例：台灣、設備、標準、測試、循環。",
        "【格式規則】不可使用 markdown 的 code block（```）語法。",
        "【格式規則】條列時直接使用 - 或數字，不要加 plaintext、json 等標籤。",
        "【內容規則】只能從以下清單中推薦測試標準，不可推薦清單以外的標準。",
        "【免責規則】每次回覆的最後，必須單獨空一行後加上以下免責聲明，一字不差：",
        "「⚠️ 本建議僅供初步評估參考，實際測試條件與判定標準請以原始法規文件為準，並由授權工程師確認。」",
        "【免責規則】若回覆中推薦了特定法規或測試條件，必須在推薦處同時標注該法規的正式版本號（例如：IEC 60068-2-1:2007），提醒使用者回查原文確認細節。",
        "請根據使用者描述的產品與需求，推薦最適合的法規、版本與測試條件，並說明推薦理由。",
        "",
        "=== 支援的環境測試標準 ===",
    ]

    for std_key, std_data in tree.items():
        lines.append(f"\n【{std_data['label']}】{std_data.get('description', '')}")
        for ver_key, ver_data in std_data["versions"].items():
            lines.append(
                f"  版本：{ver_data['label']} — {ver_data.get('description', '')}"
            )
            for test_key, test_data in ver_data["tests"].items():
                lines.append(f"    - {test_data['name']}")

    _SYSTEM_PROMPT_CACHE = "\n".join(lines)
    return _SYSTEM_PROMPT_CACHE


async def _warmup_ollama():
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                },
            )
        print(f"✅ Ollama warm-up 完成（{OLLAMA_MODEL}）")
    except Exception as e:
        print(f"⚠️  Ollama warm-up 失敗（服務可能尚未啟動）：{e}")


class QueryRequest(BaseModel):
    message: str
    history: Optional[list] = []


class QueryResponse(BaseModel):
    reply: str


def _build_messages(req: QueryRequest) -> list:
    """
    組裝送給 Ollama 的 messages。
    fix: 前端已在 message 加入 TC_PREFIX，後端不再重複加前綴，避免雙重前綴。
    history 內容也是前端傳入的乾淨字串，直接使用。
    """
    messages = [{"role": "system", "content": _build_system_prompt()}]
    for h in req.history:
        messages.append(h)
    messages.append({"role": "user", "content": req.message})
    return messages


@router.post("/standards-query", response_model=QueryResponse)
async def standards_query(req: QueryRequest):
    messages = _build_messages(req)
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        data = response.json()
    reply = data["message"]["content"]
    return QueryResponse(reply=reply)


@router.post("/standards-query-stream")
async def standards_query_stream(req: QueryRequest):
    messages = _build_messages(req)

    async def generate():
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            pass

    return StreamingResponse(generate(), media_type="text/plain")
