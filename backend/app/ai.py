import httpx
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from .standards import get_standard_tree

router = APIRouter(prefix="/api/ai", tags=["ai"])

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.1:8b"

_SYSTEM_PROMPT_CACHE: Optional[str] = None  # 重啟後自動重建


def _build_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is not None:
        return _SYSTEM_PROMPT_CACHE

    tree = get_standard_tree()

    lines = [
        "你是工業環境測試法規顧問，專注於溫箱測試。",
        "只能用繁體中文回答，禁止簡體中文。繁體範例：設備、測試、標準、循環、穩態。",
        "回答簡潔不重複，推薦時標注法規正式版本號（例如 IEC 60068-2-1:2007）。",
        "",
        "本系統支援的測試條件：",
    ]

    for std_key, std_data in tree.items():
        test_names = []
        for ver_data in std_data["versions"].values():
            for test_data in ver_data["tests"].values():
                test_names.append(test_data["name"])
        lines.append(f"{std_key}：{'、'.join(test_names)}")

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
    """組裝送給 Ollama 的 messages，history 為前端傳入的乾淨字串。"""
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
