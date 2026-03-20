# 🧬 DQALab Digital Twin — AI Agent Context

給 AI 協作工具（Claude、Cursor、Copilot）閱讀的專案背景與開發規範。每個開發階段結束後更新「當前狀態快照」區塊即可，其餘部分不動。

---

## 當前狀態快照（2026-03-20）

### 雲端部署

| 服務 | 平台 | 網址 |
|------|------|------|
| 前端 | Vercel | https://dqa-lab-digital-twin-icvw-9m0ygc6ob.vercel.app |
| 後端 | Railway | https://dqa-lab-digital-twin-production.up.railway.app |

- Vercel：24 小時常駐
- Railway：Trial 方案，平常 offline。展示前 Dashboard → `⋮` → **Redeploy**，用完 → **Remove**
- 後端環境變數（Railway Dashboard → Variables）：`GEMINI_API_KEY`、`DEMO_PASSWORD`
- Gemini Embedding API 免費方案上限 1000 次/天；每次 Redeploy 消耗約 78 次。本地 `rag_cache.pkl` 重啟直接讀取不消耗配額，已加入 `.gitignore`
- LINE Webhook URL 同時只能指向一個端點（本地或雲端擇一）
- 推播出現 401：重開終端機再執行 `make dev`，避免舊 session 殘留環境變數

### 功能完成狀態

| 模組 | 狀態 | 關鍵說明 |
|------|------|----------|
| 物理模擬引擎 | ✅ | sim_phase 狀態機、多 cycle、重啟自動恢復 |
| 環境測試標準 | ✅ | 5 法規 78 條件，三層 STANDARD_TREE |
| SOP 執行 | ✅ | 三步驟選擇、SP+PV 波型、步驟鎖定、ISO 17025 CSV |
| 異常紀錄 | ✅ | EMERGENCY 防重複、記錄步驟進度 |
| RAG 知識庫 | ✅ | Gemini Embedding、in-memory、本地快取、語義標籤、query cache |
| AI 諮詢 | ✅ | 串流、Gemini 2.5 Flash-Lite、多輪對話、推論式回答、時間計算 |
| LINE Bot | ✅ | 推播、Flex Message、Quick Replies |
| 存取控制 | ✅ | X-Demo-Password、IP Rate Limiting、8h session |
| 儀表板 | ✅ | 六狀態、趨勢圖、倒數計時、設備切換即時更新 |
| 登入頁 | ✅ | offline fallback、Demo 密碼提示 |
| SOPPage 重構 | ✅ | 拆分為 7 個子元件，主頁面壓到 ~200 行（2026-03-20） |

### 待開發（依優先度）

1. **AI 治具管理助手**（`/api/ai/fixture-recommend`）
2. **AI 設備排程預估**（`/api/ai/schedule-estimate`）
3. **報告下載優化**：`saveExecution()` 成功後自動觸發下載（目前為 `window.open`，瀏覽器可能攔截彈出視窗，待改為 `<a download>` blob 方式）
4. **Phase 3**：RS-485 真實通訊、治具資料庫、JWT 認證

### 已知未修問題

| # | 問題 | 原因 |
|---|------|------|
| B4 | `dwell_counters` 秒單位 vs `generateSP` 分鐘單位，SP/PV 波形對不上 | 架構層問題，留待 Phase 3 |
| U7 | Dashboard 點卡片 vs SOPPage 點按鈕組切換設備，互動不一致 | 可接受差異，留待未來統一 |
| U8 | 報告下載用 `window.open`，瀏覽器可能攔截彈出視窗 | 留待後續改為 blob `<a download>` |

### SOPPage 重構說明（2026-03-20）

**拆分結構**：
```
src/
  components/sop/
    generateSP.js          # SP 波形計算（純函式，無 React）
    TempChart.jsx          # SP+PV 趨勢圖
    ConditionCard.jsx      # 測試條件摘要卡片
    SelectGroup.jsx        # 單一步驟選擇器（法規/版本/條件 共用）
    StepList.jsx           # SOP 步驟勾選清單 + 進度條
    ExecutionPanel.jsx     # 儲存執行紀錄 + 報告下載
    SafetyChecklist.jsx    # 上架驗證注意事項 + 啟動按鈕
  SOPPage.jsx              # 主頁面 ~200 行，只負責狀態與資料協調
  SOPPage.css              # 樣式不動
```

**UX 變更**：
- 操作人員姓名移至「上架驗證注意事項」區塊頂部，啟動前必填（非必填但建議填）
- 啟動按鈕在 operator 欄位為空時顯示提示但不強制擋住（仍可啟動）
- `saveExecution()` 成功後自動呼叫 `window.open` 下載報告，同時顯示下載連結供備用
- 步驟改為**系統自動確認**設計備註：目前仍為手動勾選；自動確認（PV 到達 SP 觸發）為 Phase 3 後端 event 架構，前端 checkbox UI 保留但標注為暫時方案

---

## 技術規格

### 狀態機

```
IDLE → RUNNING ↔ PAUSED → FINISHING → IDLE
RUNNING/PAUSED → EMERGENCY（防重複觸發）

sim_phase: idle → ramp_to_low / ramp_to_high → dwell_high → ramp_to_low2 → dwell_low → ramp_to_ambient
```

### 存取控制

- Header：`X-Demo-Password`（值來自 `backend/.env` 的 `DEMO_PASSWORD`）
- 豁免路徑：`/api/line/webhook`、`/docs`、`/openapi.json`、`/api/latest`
- Rate limiting：錯誤 5 次封鎖 IP 10 分鐘，重啟清除
- Session：`demo_password` + `demo_login_at` 存 localStorage，8 小時後踢出

### 資料庫

| 表格 | 說明 |
|------|------|
| `device_data` | 歷史溫濕度，每 10 秒，composite index (device_id, timestamp) |
| `device_states` | 狀態持久化，含 sim_phase、sim_cycle、started_at |
| `sop_executions` | 執行主表，含 operator |
| `step_records` | 步驟完成狀態 |
| `error_logs` | 緊急停止事件，含 completed_steps、total_steps |

### 前端輪詢頻率

| 元件 | 頻率 |
|------|------|
| Dashboard 設備狀態 | 10s（隱藏時暫停） |
| Dashboard 執行紀錄 | 60s（隱藏時暫停） |
| SOPPage 設備狀態 | 3s（隱藏時暫停） |
| ErrorLog | 60s |

### AI 模組

- 推理：`gemini-2.5-flash-lite`，1000 次/天免費，temperature=0.3
- 向量：`gemini-embedding-001`，啟動時批次向量化（20 條/批，批次間等 5 秒），快取至 `rag_cache.pkl`
- RAG 強化：每個 chunk 含語義標籤（低溫開關機、純高溫、高溫高濕、溫度循環等），query embedding 有 LRU cache（64 筆）
- 查詢路由：指定標準 → `retrieve_by_std` + type_hints 篩選；跨標準比較 → `retrieve_multi`；有測試類型關鍵字 → 向量搜尋後篩選；其他 → top_k=20
- 歷史繼承：當前訊息未指定標準時，自動從 history 抓之前提過的標準
- 標準優先順序：未指定時預設推 IEC 60068，只有明確說鐵道/船舶/海事/變電站才推對應標準
- 時間計算：室溫統一 25°C，升降溫時間 = 溫差 ÷ 速率，多項測試逐項列小計再給總計
- 多輪對話：MAX_HISTORY = 4；localStorage key：`dqa_ai_chats_v2`
- 輸入：Enter 送出，Shift+Enter 換行

### 欄位命名規範

`dwell_time_hours`（非 `dwell_time`）、`humidity_rh_percent`（非 `humidity`）

### Alembic 注意事項

SQLite autogenerate 有時產生空的 `upgrade()`，需手動填入。若 `alembic upgrade head` 無動作，改用：
```bash
sqlite3 backend/test.db "ALTER TABLE table_name ADD COLUMN col_name INTEGER;"
```

---

## 常用指令

```bash
make install                   # 安裝所有依賴
python backend/init_db.py      # 首次初始化資料庫
make dev                       # 啟動全部服務（含 ngrok）
make clean                     # 清理殘留程序

# DB 結構變更（在 backend/ 目錄下）
alembic revision --autogenerate -m "描述"
alembic upgrade head
```