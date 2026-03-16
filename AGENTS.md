# 🧬 DQALab Digital Twin — AI Agent Context

給 AI 協作工具（Claude、Cursor、Copilot）閱讀的專案背景與開發規範。每個開發階段結束後更新「當前狀態快照」區塊即可，其餘理論部分不動。版本紀錄以 git log 為準，不另維護 CHANGELOG。

---

## 當前狀態快照（2026-03-16）

### 專案目錄結構

```
.
├── AGENTS.md
├── README.md
├── LICENSE
├── Makefile
├── dev_start.sh
├── backend
│   ├── alembic/
│   ├── alembic.ini
│   ├── init_db.py
│   ├── requirements.txt
│   └── app/
│       ├── ai.py
│       ├── errors.py
│       ├── line.py
│       ├── main.py
│       ├── models.py
│       ├── reports.py
│       ├── serial_reader.py
│       ├── sop.py
│       ├── utils.py
│       └── standards/
│           ├── __init__.py
│           ├── _base.py
│           ├── iec60068.py
│           ├── en50155.py
│           ├── iec61850.py
│           ├── iec60945.py
│           └── dnv.py
├── client
│   └── src/
│       ├── App.jsx
│       ├── Dashboard.jsx
│       ├── SOPPage.jsx
│       ├── SOPPage.css
│       ├── Errorlog.jsx
│       ├── AIPage.jsx
│       ├── main.jsx
│       └── ai/
│           ├── aiStorage.jsx
│           ├── useAIChat.jsx
│           ├── MessageBubble.jsx
│           ├── ChatArea.jsx
│           └── ChatSidebar.jsx
├── docs
│   └── templates/
│       └── QA_Test_Report_Template.docx
└── simulator
    └── main.py
```

### 已完成模組

| 模組 | 位置 | 說明 |
|------|------|------|
| 共用工具函式 | `backend/app/utils.py` | `_now_utc()`、`_save_device_state()`，避免 circular import |
| 物理模擬引擎 | `backend/app/main.py` | 升降溫斜率（含低溫先降後升）、每 10 秒寫 DB、PAUSED 不寫 DB |
| 設備狀態持久化 | `backend/app/main.py` + `models.py` | DeviceState 表、重啟後自動恢復狀態 |
| 環境測試標準 | `backend/app/standards/` | 三層 STANDARD_TREE，5 法規 78 條件 |
| SOP 路由 + 執行紀錄 | `backend/app/sop.py` | 標準樹展開、三步驟選擇、執行紀錄；`standards/tree` 含 steps 欄位 |
| CSV 報告 | `backend/app/reports.py` | ISO 17025 格式，big5，查詢上限 10000 筆 |
| LINE Bot | `backend/app/line.py` | 狀態查詢、推播、LINE 簽名驗證、User ID 白名單 |
| 異常紀錄 | `backend/app/errors.py` | EMERGENCY 自動寫入 error_logs |
| AI 法規諮詢後端 | `backend/app/ai.py` | 串流 + 非串流，gemma3:4b，system prompt 快取，warm-up 預載 |
| AI 法規諮詢前端 | `client/src/ai/` | 多對話管理、專案分組、串流輸出、追問建議、localStorage 持久化 |
| 儀表板 | `client/src/Dashboard.jsx` | 六狀態、趨勢圖、步驟進度條、倒數計時器、active prop 控制輪詢 |
| SOP 執行頁 | `client/src/SOPPage.jsx` | 三步驟法規選擇、SP+PV 波型曲線、執行資訊面板、防重複提交 |
| 異常看板 | `client/src/Errorlog.jsx` | 統計卡片 + 完整紀錄列表，60s 自動刷新 |
| 全域路由 | `client/src/App.jsx` | CSS display 切換，四頁面常駐 DOM，active prop 傳遞 |

### 下一步待開發（依優先度）

1. **法規正確性審查**（✅ 完成）
2. **AI 諮詢 UI 改版**（✅ 完成）
3. **AI 諮詢模組 bug 修正**（✅ 完成）
4. **後端與前端系統性優化**（✅ 完成）
5. **後端架構優化**（✅ 完成）
6. **LINE Bot 整合**（✅ 完成）
7. **AI 諮詢 UI / 效能優化**（進行中）— 見「已知待修問題」
8. **AI 治具管理助手**（`/api/ai/fixture-recommend`）
9. **AI 設備排程預估**（`/api/ai/schedule-estimate`）
10. **Phase 3**：多台設備架構、治具資料庫、認證系統、RS-485 真實通訊

---

## 已知待修問題

### 高優先（明顯影響體驗）

- `useAIChat.jsx` `generateSuggestions` 延遲 3s → 改為 1s
- `ai.py` 加入 `num_ctx: 2048`、`temperature: 0.3`，降低推理時間
- `ChatSidebar.jsx` `grouped` 和 `sortedGroups` 缺少 `useMemo`，對話多時每次 render 都重算
- `ChatArea.jsx` `suggestRow` 用 `key={i}`，應改為 `key={q}`

### 中優先（UX 改善）

- `ChatSidebar.jsx` 對話移動分組改為拖曳操作，移除現有的下拉選單方式
- `ChatSidebar.jsx` 對話標題支援雙擊直接進入編輯模式
- `ChatSidebar.jsx` 分組支援點擊摺疊/展開
- `ChatArea.jsx` 串流中在泡泡右下角顯示已經過秒數，完成後才顯示最終時間
- `ChatArea.jsx` 空白頁預設問題從題庫隨機抽取，每次載入不同
- `ChatArea.jsx` 串流訊息泡泡右下角加小型停止按鈕，就近操作

### 低優先（效能微調）

- `useAIChat.jsx` `sendMessage` 的 `useCallback` 依賴陣列包含 `messages`，每次訊息更新都重建，應改用 `useRef` 存 messages
- `useAIChat.jsx` `handleInputChange`、`handleKeyDown` 缺少 `useCallback`，每次 render 產生新函式
- `ai.py` 獨立 `/api/ai/suggest` 端點供追問建議專用（timeout 30s），不佔用主對話資源
- `ChatSidebar.jsx` 側欄收合時顯示目前對話縮略，而非完全空白

### UI 細節

- `ChatSidebar.jsx` 刪除確認按鈕字體 11px 太小，觸控裝置難點
- `ChatArea.jsx` 建議列 chip 改為橫向滑動，避免長文字換行爆版
- `MessageBubble.jsx` 免責聲明只在第一則完整顯示，後續改為灰色小圖示，減少視覺干擾
- 加入快捷鍵：`Cmd+K` 新對話、`Esc` 停止串流

---

## 技術規格

### 環境測試標準（standards/）

| 法規 | 條數 |
|------|------|
| IEC 60068 | 17 |
| EN 50155 | 21 |
| IEC 61850-3 | 19 |
| IEC 60945 | 7 |
| DNV | 14 |
| **合計** | **78** |

### AI 模組

- 模型：`gemma3:4b`（本機 Ollama）；備用：`gemma3:12b`
- 端點：`/api/ai/standards-query`（非串流）、`/api/ai/standards-query-stream`（串流）
- system prompt：英文指令，78 個測試條件名稱（約 800 tokens），模組載入快取
- TC_PREFIX：`"[MUST reply in Traditional Chinese zh-TW ONLY, NO Simplified Chinese] "`，前端附加
- 多輪對話：MAX_HISTORY = 4；追問建議 3s 延遲，切換對話自動 abort
- localStorage key：`dqa_ai_chats_v2`

### LINE Bot

- 套件：`line-bot-sdk==3.11.0`
- Webhook：`POST /api/line/webhook`，LINE 簽名強制驗證
- 白名單：只有 `LINE_USER_ID` 可操作
- 推播觸發：EMERGENCY、FINISHING → IDLE
- 指令：`狀態`/`status`、`CH01`~`CH05`、`help`
- 金鑰存於 `backend/.env`：`LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`LINE_USER_ID`
- ngrok：每次重啟 URL 會變，需重新設定 Webhook URL

### 關鍵設計規範

**狀態機**
```
IDLE → RUNNING ↔ PAUSED → FINISHING → IDLE
RUNNING → EMERGENCY（任意時刻）
```

**資料庫**
| 表格 | 說明 |
|------|------|
| `device_data` | 歷史溫濕度，每 10 秒，composite index (device_id, timestamp) |
| `device_states` | 設備狀態持久化 |
| `sop_executions` | 執行歷程主表 |
| `step_records` | 步驟完成狀態 |
| `error_logs` | 緊急停止事件 |

**前端輪詢**
| 元件 | 頻率 |
|------|------|
| Dashboard 設備狀態 | 每 10 秒（隱藏時暫停） |
| Dashboard 執行紀錄 | 每 60 秒（隱藏時暫停） |
| SOPPage 設備狀態 | 每 3 秒（隱藏時暫停） |
| Errorlog | 每 60 秒 |

**欄位命名**
| 正確 | 錯誤 |
|------|------|
| `dwell_time_hours` | `dwell_time` |
| `humidity_rh_percent` | `humidity` |

**常用指令**
```bash
make install               # 安裝所有依賴
python backend/init_db.py  # 首次初始化資料庫
make dev                   # 啟動全部服務
make clean                 # 清理殘留程序
make ngrok                 # 啟動 ngrok（LINE Bot Webhook 用）
# DB 結構變更（在 backend/ 目錄下）
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

---

## 系統架構理論

### 物理模擬引擎

- 斜率控制：`get_ramp_rate()` 動態讀取各標準速率限制
- 低溫測試：先降至 `low_temperature`，再升至 `high_temperature`
- 狀態機：`EMERGENCY` 微幅抖動；`PAUSED` 鎖定數值不寫 DB；`FINISHING` 降溫至 25°C 後回 `IDLE`

### 硬體通訊（Phase 3）

- 通訊協議：KSON AICM，RS-232 串口
- 虛擬橋接：socat `/dev/ttys000` ↔ `/dev/ttys001`
- Phase 3 評估以 MQTT 取代輪詢架構，`serial_reader.py` 屆時啟用