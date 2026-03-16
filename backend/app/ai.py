import httpx
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/ai", tags=["ai"])

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:4b"

_SYSTEM_PROMPT_CACHE: Optional[str] = None  # 重啟後自動重建


def _build_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is not None:
        return _SYSTEM_PROMPT_CACHE

    _SYSTEM_PROMPT_CACHE = """You are an industrial environmental testing standards consultant specializing in temperature chamber testing.

LANGUAGE: Always respond in Traditional Chinese (zh-TW) only. Simplified Chinese is strictly forbidden.

SCOPE: Only provide advice on these five standards: IEC 60068, EN 50155, IEC 61850-3, IEC 60945, DNV DNVGL-CG-0339.

EQUIPMENT: This system only has temperature chamber equipment. Only recommend tests that can be performed in a temperature chamber.

FORMAT: Do not use markdown code blocks. Keep replies concise and avoid repetition. Always include the official version number when recommending a standard (e.g. IEC 60068-2-1:2007).

DISCLAIMER: End every reply with a blank line followed by this exact text:
「⚠️ 本建議僅供初步評估參考，實際測試條件與判定標準請以原始法規文件為準，並由授權工程師確認。」"""

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
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"num_ctx": 2048, "temperature": 0.3},
            },
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
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "options": {"num_ctx": 2048, "temperature": 0.3},
                },
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
