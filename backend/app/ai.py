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

# fix: 模組載入時建立一次，避免每次 API 呼叫都重跑 get_standard_tree()
_SYSTEM_PROMPT_CACHE: Optional[str] = None


def _build_system_prompt() -> str:
    """
    將 STANDARD_TREE 摘要成文字，嵌入 system prompt。
    只列出法規、版本、測試條件名稱與關鍵參數，不列完整步驟。
    結果會快取在模組層級，只建立一次。
    """
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
                params = []
                if test_data.get("high_temperature"):
                    params.append(f"高溫 {test_data['high_temperature']}°C")
                if test_data.get("low_temperature"):
                    params.append(f"低溫 {test_data['low_temperature']}°C")
                if test_data.get("target_temperature"):
                    params.append(f"目標溫度 {test_data['target_temperature']}°C")
                if test_data.get("dwell_time_hours"):
                    params.append(f"停留 {test_data['dwell_time_hours']}h")
                if test_data.get("cycles"):
                    params.append(f"{test_data['cycles']} 循環")
                if test_data.get("humidity_rh_percent"):
                    params.append(f"濕度 {test_data['humidity_rh_percent']}%RH")
                param_str = "、".join(params) if params else ""
                lines.append(f"    - {test_data['name']}（{param_str}）")

    _SYSTEM_PROMPT_CACHE = "\n".join(lines)
    return _SYSTEM_PROMPT_CACHE


class QueryRequest(BaseModel):
    message: str
    history: Optional[list] = []


class QueryResponse(BaseModel):
    reply: str


@router.post("/standards-query", response_model=QueryResponse)
async def standards_query(req: QueryRequest):
    """
    法規諮詢助手：使用者描述產品與需求，LLM 推薦適合的法規與測試條件。
    """
    system_prompt = _build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    for h in req.history:
        messages.append(h)

    messages.append({"role": "user", "content": f"[請用繁體中文回覆] {req.message}"})

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()

    reply = data["message"]["content"]
    return QueryResponse(reply=reply)


@router.post("/standards-query-stream")
async def standards_query_stream(req: QueryRequest):
    """
    串流版法規諮詢，逐字回傳 Ollama 輸出。
    前端使用 fetch + ReadableStream 讀取。
    """
    system_prompt = _build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history:
        messages.append(h)
    messages.append({"role": "user", "content": f"[請用繁體中文回覆] {req.message}"})

    async def generate():
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
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
