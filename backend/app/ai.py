import os
import json
import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from .rag import (
    retrieve,
    match_std_keys,
    extract_temperatures,
    retrieve_multi,
    retrieve_by_std,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])

GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}"

_SYSTEM_PROMPT = """你是工業環境測試法規顧問，專注於溫箱測試。只能用繁體中文回答，禁止簡體中文。

【核心原則】
1. 只根據【參考資料】區塊的內容回答，禁止引用資料以外的任何標準版本號、測試名稱或數值參數。
2. 若參考資料中找不到相關條目，回覆「查無此資料」，不要追問或猜測。
3. 禁止自行計算總測試時間。列出各條件的停留時間與循環次數，說明「總時間需依測試順序自行加總」。

【回答方式】
- 使用者說「低溫開關機」→ 找通電且有低溫的測試條件
- 使用者說「純高溫」→ 找只有高溫目標、無低溫的測試條件
- 使用者說「高溫高濕」→ 找有濕度設定的測試條件
- 使用者說「溫度循環」→ 找有 cycles 且同時有高低溫的測試條件
- 使用者沒有指定標準 → 列出參考資料中所有符合的條目，依標準分組呈現
- 使用者已在對話中指定過標準 → 優先回答該標準的條目，不需再追問
- 回答要直接、具體，標注法規正式版本號（例如 IEC 60068-2-1:2007）
- 格式用分組條列，每條附上關鍵參數（溫度、時間、循環、通電狀態）
- 回答結尾固定加：⚠️ 本建議僅供初步評估參考，實際條件請以原始法規文件為準。"""

_COMPARE_KEYWORDS = ["和", "與", "vs", "比較", "差異", "不同"]

# 測試類型關鍵字對應篩選條件
_TEST_TYPE_HINTS = {
    "低溫開關機": {"power_on": True, "has_low": True},
    "低溫工作": {"power_on": True, "has_low": True},
    "低溫儲存": {"power_on": False, "has_low": True},
    "純高溫": {"has_low": False, "has_high": True, "no_humidity": True},
    "乾熱": {"has_low": False, "has_high": True, "no_humidity": True},
    "高溫高濕": {"has_humidity": True},
    "濕熱": {"has_humidity": True},
    "溫度循環": {"has_cycles": True, "has_low": True, "has_high": True},
    "熱衝擊": {"has_cycles": True, "has_low": True, "has_high": True},
}


def _get_api_key() -> str:
    return os.environ["GEMINI_API_KEY"]


class QueryRequest(BaseModel):
    message: str
    history: Optional[list] = []


class QueryResponse(BaseModel):
    reply: str


def _filter_chunks_by_hints(chunks: list[dict], hints: dict) -> list[dict]:
    """根據測試類型關鍵字篩選 chunk。"""
    results = []
    for c in chunks:
        raw = c.get("raw", {})
        if hints.get("power_on") is not None:
            if raw.get("power_on") != hints["power_on"]:
                continue
        if hints.get("has_low") and raw.get("low_temperature") is None:
            continue
        if (
            hints.get("has_high")
            and raw.get("high_temperature") is None
            and raw.get("target_temperature") is None
        ):
            continue
        if hints.get("no_humidity") and raw.get("humidity_rh_percent") is not None:
            continue
        if hints.get("has_humidity") and raw.get("humidity_rh_percent") is None:
            continue
        if hints.get("has_cycles") and (
            raw.get("cycles") is None or raw.get("cycles", 1) <= 1
        ):
            continue
        results.append(c)
    return results


def _extract_test_type_hints(msg: str) -> dict:
    """從訊息中抽取測試類型關鍵字，合併對應的篩選條件。"""
    merged = {}
    for keyword, hints in _TEST_TYPE_HINTS.items():
        if keyword in msg:
            merged.update(hints)
    return merged


def _extract_std_from_history(history: list) -> list[str]:
    """從對話歷史中抽取曾提及的標準。"""
    all_text = " ".join(
        m.get("content", "") for m in history if m.get("role") == "user"
    )
    from .rag import match_std_keys

    return match_std_keys(all_text)


async def _build_context(msg: str, history: list = []) -> str:
    matched_stds = match_std_keys(msg)

    # 若當前訊息沒有指定標準，從歷史中找
    if not matched_stds and history:
        matched_stds = _extract_std_from_history(history)

    is_compare = any(k in msg for k in _COMPARE_KEYWORDS) and len(matched_stds) >= 2
    temps = extract_temperatures(msg)
    type_hints = _extract_test_type_hints(msg)

    hits: list[dict] = []
    seen_keys: set = set()

    def _add_hits(new_hits: list[dict]):
        for h in new_hits:
            uid = f"{h['std_key']}_{h['ver_key']}_{h['test_key']}"
            if uid not in seen_keys:
                seen_keys.add(uid)
                hits.append(h)

    if is_compare:
        queries = []
        for std in matched_stds:
            queries.append(f"{std} 高溫測試")
            queries.append(f"{std} 低溫測試")
            queries.append(f"{std} 測試條件")
        _add_hits(await retrieve_multi(queries, top_k_each=5))

    elif matched_stds:
        # 指定標準：直接全撈該標準，再用 type_hints 篩選
        raw_hits = retrieve_by_std(matched_stds)
        if type_hints:
            filtered = _filter_chunks_by_hints(raw_hits, type_hints)
            # 若篩選後太少（< 3），退回全撈避免漏掉
            _add_hits(filtered if len(filtered) >= 3 else raw_hits)
        else:
            _add_hits(raw_hits)

    elif type_hints:
        # 沒有指定標準但有測試類型關鍵字：向量搜尋後篩選
        raw_hits = await retrieve(msg, top_k=30)
        _add_hits(_filter_chunks_by_hints(raw_hits, type_hints))
        # 如果篩選後太少，退回向量搜尋結果
        if len(hits) < 3:
            hits.clear()
            seen_keys.clear()
            _add_hits(raw_hits[:20])

    elif temps:
        _add_hits(await retrieve(msg, top_k=20))

    else:
        _add_hits(await retrieve(msg, top_k=20))

    if hits:
        return "\n".join(f"- {h['text']}" for h in hits)
    return ""


def _build_gemini_payload(messages: list, system_prompt: str) -> dict:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1500,
        },
    }


@router.post("/standards-query", response_model=QueryResponse)
async def standards_query(req: QueryRequest):
    ref_block = await _build_context(req.message, req.history)
    if ref_block:
        system_content = f"{_SYSTEM_PROMPT}\n\n【參考資料】\n{ref_block}"
    else:
        system_content = (
            _SYSTEM_PROMPT + "\n\n【參考資料】查無相關資料，請直接回覆「查無此資料」。"
        )

    messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    payload = _build_gemini_payload(messages, system_content)
    api_key = _get_api_key()

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{GEMINI_URL}:generateContent?key={api_key}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    reply = data["candidates"][0]["content"]["parts"][0]["text"]
    return QueryResponse(reply=reply)


@router.post("/standards-query-stream")
async def standards_query_stream(req: QueryRequest):
    ref_block = await _build_context(req.message, req.history)
    if ref_block:
        system_content = f"{_SYSTEM_PROMPT}\n\n【參考資料】\n{ref_block}"
    else:
        system_content = (
            _SYSTEM_PROMPT + "\n\n【參考資料】查無相關資料，請直接回覆「查無此資料」。"
        )

    messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    payload = _build_gemini_payload(messages, system_content)
    api_key = _get_api_key()

    async def generate():
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{GEMINI_URL}:streamGenerateContent?alt=sse&key={api_key}",
                json=payload,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                            token = (
                                data.get("candidates", [{}])[0]
                                .get("content", {})
                                .get("parts", [{}])[0]
                                .get("text", "")
                            )
                            if token:
                                yield token
                        except Exception:
                            pass

    return StreamingResponse(generate(), media_type="text/plain")
