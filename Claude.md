# 🧬 DQA Lab Digital Twin — AI Agent Context

給 AI 協作工具（Claude、Cursor、Copilot）閱讀的專案背景與開發規範。每個開發階段結束後更新「當前狀態快照」區塊即可，其餘部分不動。

---

## 當前狀態快照（2026-03-24）

### 開發環境

```
本地開發：macOS M2
後端：http://localhost:8000
前端：http://localhost:5173
API 文件：http://localhost:8000/docs
```

### 功能完成狀態

| 模組 | 狀態 | 關鍵說明 |
|------|------|----------|
| 物理模擬引擎 | ✅ | sim_phase 狀態機、多 cycle、重啟自動恢復、dwell 真實時間戳、IDLE 跳過迴圈 |
| 環境測試標準 | ✅ | 5 法規 78 條件，三層 STANDARD_TREE |
| SOP 執行 | ✅ | 三步驟選擇、SP+PV 波型、步驟鎖定、ISO 17025 CSV、useMemo 優化 |
| 異常紀錄 | ✅ | EMERGENCY 防重複、記錄步驟進度、limit 500 |
| RAG 知識庫 | ✅ | Gemini Embedding、in-memory、快取自動失效重建、query cache |
| AI 諮詢 | ✅ | 串流、Gemini 2.5 Flash-Lite、多輪對話、debounce 存檔、focus 競爭修正 |
| LINE Bot | ✅ | 推播、Flex Message、Quick Replies、共用 AsyncClient |
| 存取控制 | ✅ | X-Demo-Password、IP Rate Limiting（maxsize 清理）、8h session、CORS |
| 儀表板 | ✅ | 六狀態、趨勢圖、倒數計時、skeleton loading、時間格式化、執行紀錄顯示測試名稱 |
| 登入頁 | ✅ | offline fallback、不顯示密碼明文、role 存 localStorage、三層權限切換 |
| SOP 元件 | ✅ | 拆分 10 個子元件、自製 confirm modal、步驟鎖定、錯誤訊息細節化 |
| 執行紀錄 | ✅ | 顯示 sop_name、CSV 下載帶 auth header |
| AI 對話 | ✅ | 標題截斷、空分組保留、閉包修正、折疊偵測、textarea 高度重置、modelBadge 修正 |
| 治具管理（核心） | ✅ | 治具總表、借出中、逾期未還、借出登記 Modal、歸還 Modal、Summary 卡片、搜尋篩選、role 權限控制 |
| 治具管理（後端） | ✅ | fixtures / fixture_loans / users / purchase_orders DB 建立、list/summary/loans/overdue/import/inventory 全 API 完成、8 筆初始資料 |
| Excel 匯入 UI | ✅ | 上傳按鈕、FormData POST、成功/失敗筆數預覽、完成後 fetchAll |

---

## 待開發路線圖

### 現階段目標：治具模組全收尾 → Auth 升級完整版

```
[1] LINE Bot 治具通知   P1  ← 下一個開工
[2] 月盤點 UI          P2
[3] Auth 升級完整版    P1
[4] 採購清單           P2
[5] 汰換提醒           P3
─────────────────────────────────────────
[後續] 前端大改版（控制中心 UI）
[後續] 排程系統（甘特圖 + 自動時長計算）
```

---

### [1] LINE Bot 治具通知（P1）

**狀態：❌ 未開始**

#### 後端實作重點

- `POST /api/fixtures/loans` 成功後 → 立即推播借用人（`users.line_user_id`）
- FastAPI lifespan 加入 APScheduler，每日 08:00 執行掃描任務

#### APScheduler 掃描邏輯

```
逾期 >= 1 天  → 推播借用人
逾期 >= 3 天  → 推播保管人（fixture.keeper_user_id → users.line_user_id）
逾期 >= 7 天  → 推播管理者（role = admin 的 users）
到期前 2 天   → 推播借用人（提前提醒）
每日彙整      → 推播保管人（今日到期清單）
月盤點提醒    → 每月 1 日推播保管人
```

#### 注意事項

- `users` 表已有 `line_user_id` 欄位，直接用
- 共用 `line.py` 現有的 `AsyncClient`，不另起 HTTP client
- 推播失敗不應阻斷主流程，用 try/except + log 處理

---

### [2] 月盤點 UI（P2）

**狀態：❌ 未開始（後端 `/inventory` API 已完成）**

#### 前端實作重點

- 治具總表新增「實際數量」欄位（keeper/admin 可 inline 編輯，engineer 唯讀）
- 回填後自動比對：`實際數量 < 系統數量` → 差異欄標紅 + 顯示「最後借出者」
- 送出：`POST /api/fixtures/{id}/inventory`，完成後重新 fetchAll

---

### [3] Auth 升級完整版（P1）

**狀態：❌ 未開始（現行用 localStorage role，無後端驗證）**

> ⚠️ 影響範圍最大，建議在治具模組收尾後再動，避免破壞性變更。

#### 後端實作重點

| 端點 | 說明 |
|------|------|
| `POST /api/auth/login` | 帳號 + 密碼 → 回傳 JWT |
| `GET /api/auth/me` | 回傳當前使用者 role / name / line_user_id |
| `POST /api/auth/users` | admin only，新增帳號 |
| `PATCH /api/auth/users/{id}` | admin only，修改 role / 停用帳號 |

- JWT middleware 取代現有的 `X-Demo-Password` header 驗證
- guest 模式保留：demo 密碼換取一個 guest JWT（role=guest），不破壞現有展示功能
- 推薦套件：`python-jose[cryptography]` + `passlib[bcrypt]`

#### 前端實作重點

- 登入頁改為帳號 + 密碼兩欄（guest 入口保留）
- token 存 localStorage，取代 `demo_password`
- `api.js` interceptor 改帶 `Authorization: Bearer <token>`
- admin 可進入「使用者管理」頁：新增帳號、設定 role、綁定 LINE User ID、停用帳號

---

### [4] 採購清單（P2）

**狀態：❌ 未開始（DB `purchase_orders` 表已建立）**

#### 後端

| 端點 | 說明 |
|------|------|
| `GET /api/purchase-orders` | 採購清單列表 |
| `POST /api/purchase-orders` | 手動新增 / 從缺貨自動產生 |
| `PATCH /api/purchase-orders/{id}` | 到貨入庫，更新 `fixtures.quantity` |

#### 前端

- 治具總表「可借數量 = 0」自動標記缺貨，一鍵產生採購單
- 採購清單頁：顯示待採購 / 已到貨狀態，到貨後更新庫存

---

### [5] 汰換提醒（P3）

**狀態：❌ 未開始**

#### 後端

- `fixtures` 表新增 `estimated_replacement_date`（由 `replacement_cycle_years` + 首次入庫時間計算）
- APScheduler 每週一次掃描 → 30 天內到期推播保管人

#### 前端

- 治具總表新增「汰換日期」欄：30 天內到期標黃、已過期標紅

---

## 後續規劃（治具收尾後）

### 前端大改版（控制中心 UI）

三欄固定佈局，1920x1080 桌機/筆電設計：

```
┌─────────────┬──────────────────────┬──────────────┐
│  左欄 155px │    中欄（彈性）       │  右欄 195px  │
│  動態內容   │  設備 / 排程 / 治具   │  AI 諮詢     │
│             │  tab 切換            │  永遠顯示    │
└─────────────┴──────────────────────┴──────────────┘
```

頂部固定一列摘要狀態列：執行中台數、緊急台數、待機台數、治具借出數、今日到期、逾期未還。

**左欄（動態，跟隨中欄 tab 切換）**

- 設備 tab → 5 台設備即時狀態卡片（RUNNING 顯示溫度/測試名稱/剩餘時間，IDLE 簡化，EMERGENCY 紅色警示）
- 左下角「紀錄」可收合：異常紀錄 + 執行紀錄 + 歷史溫濕度連結
- 排程 tab → 今日設備佔用摘要
- 治具 tab → 今日治具動態

**中欄（tab 切換）**

IDLE → 啟動前流程：三步驟選擇標準 → ConditionCard → SafetyChecklist → 啟動 Modal

RUNNING/PAUSED → 執行中監控：
- SV/PV 對比（溫度、濕度、偏差 + 容差進度條）
- 時間資訊（Now Time / Free Time / End Time / Cycle）
- SP + PV 波型圖（縮小版）
- Pgm Step 表格（溫度SV / 濕度SV / 時間 / 狀態）
- SOP 確認步驟（與 Pgm Step 分開，獨立區塊）
- 操作按鈕：暫停切換 / 正常停止 / 緊急停止

**右欄（永遠顯示）**

AI 諮詢：快速問題按鈕（查庫存、問法規、推薦治具、算時長）+ 對話區 + 輸入框

> ⚠️ 兩種 Step 的區分：
> - **Pgm Step** = 溫箱自動執行的測試段落，對應 generateSP 波型
> - **SOP 確認步驟** = 工程師手動勾選的查核項目（現有 StepList）
> 兩者分開顯示，不混用。

---

### 排程系統

**核心邏輯**
- 系統自動計算時長，人工審核確認
- 先到先排，同一樣品所有條件在同一台設備依序跑
- 同台設備同時間只能一個專案（ISO 17025）

**時長計算**

```
總時長 = Σ（測試條件時長 + 條件間回常溫時間）
回常溫時間 = |測試溫度 - 25°C| ÷ 降溫速率（從法規庫取）
```

**設備分配**
- 自動找最早可用設備排入
- 管理人可標記設備不可用時段（維護/校正/假日）
- 跨假日測試自動標記
- 特殊情況標記：pre-test、產品部授權例外

**審核流程**：系統排好 → 甘特圖預覽 → 管理人確認 → 生效 → RS-485 鎖定（Phase 3）

**新增 DB 表格**
- `schedules`：排程紀錄（專案資訊、設備、測試條件清單、開始/結束時間、狀態）

---

## 已知未修問題

| # | 問題 | 優先度 |
|---|------|--------|
| S2 | 步驟進度 race condition（快速勾選兩步驟第二個 POST 覆蓋，實際發生機率極低） | P3 |
| B4 | generateSP 與 _calc_estimated_end_at 時間計算不同步 | P3 |
| U7 | Dashboard 卡片 vs SOPPage 按鈕組切換設備不一致（新 UI 重構後自然消除） | P3 |
| D5+D6 | App.jsx 無 URL routing，react-router-dom 已裝未用 | P3 |
| X1 | test.db 為 pytest 自動產生，可直接刪除，不影響開發 | P3 |

---

## 治具管理系統設計原則

- 保管人是唯一操作者（Lab Eng），代理人為 Lab Sup
- 代理授權有期限，不是永久
- LINE Bot 只做通知，不做操作（防止未授權操作）
- 所有確認動作在網頁系統完成（有身份驗證）
- 治具統一放在上鎖治具室，保管人管鑰匙

### 可借數量計算
```
可借數 = 總數 - 借出中 - 損壞
```

### 借出流程（保管人中心）
1. 工程師透過任何方式申請（口頭/mail/預約，系統不管申請管道）
2. 保管人在網頁系統 30 秒內完成借出登記：選借用人、選治具、填樣品/專案名稱、綁定設備（KSON_CH01~05）、設歸還日期
3. LINE Bot 推播借用人確認訊息
4. 設備測試結束時系統提示「有借出治具尚未歸還」

### 月盤點流程
保管人清點實際數量 → 系統回填 → 差異自動標記 → 顯示「最後借出者」供追查

### 採購閉環
缺貨警示 → 採購清單自動產生 → 到貨入庫更新數量

---

## 系統整合觸發點

- SOP 正常停止 → 檢查此設備有無未歸還治具 → 提示歸還
- EMERGENCY → 同上
- 排程確認 → 自動預約對應治具
- 排程確認 → RS-485 鎖定溫箱（Phase 3）

---

## 技術規格

### 狀態機

```
設備狀態：
IDLE → RUNNING ↔ PAUSED → FINISHING → IDLE
RUNNING/PAUSED → EMERGENCY（防重複觸發）

模擬相位：
idle → ramp_to_low / ramp_to_high → dwell_high → ramp_to_low2 → dwell_low → ramp_to_ambient
```

### 存取控制（現有，Auth 升級前）

- Header：`X-Demo-Password`（值來自 `backend/.env` 的 `DEMO_PASSWORD`）
- 豁免路徑：`/api/line/webhook`、`/docs`、`/openapi.json`、`/api/latest`、`/health`
- Rate limiting：錯誤 5 次封鎖 IP 10 分鐘，重啟清除
- Session：`demo_password` + `demo_login_at` + `user_role` 存 localStorage，8 小時後踢出
- 401 時前端自動清除 session 並跳回登入頁（api.js interceptor）
- role 值：`guest` / `engineer` / `keeper` / `admin`，`canOperate = role === "admin" || role === "keeper"`

### CORS

- 本地開發：`http://localhost:5173`（預設值，取自 `backend/.env` 的 `ALLOWED_ORIGINS`）

### 前端元件結構（現有）

```
src/
  components/
    sop/
      generateSP.js          # SP 波形計算（純函式）
      TempChart.jsx          # SP+PV 趨勢圖
      ConditionCard.jsx      # 測試條件摘要卡片
      SelectGroup.jsx        # 步驟選擇器（法規/版本/條件 共用）
      StepList.jsx           # 步驟勾選清單 + 進度條
      ExecutionPanel.jsx     # 儲存執行紀錄 + blob 報告下載
      ExecutionInfoPanel.jsx # 執行中資訊面板（Pgm/Step/Free Time/Cycle）
      SafetyChecklist.jsx    # 注意事項 + 啟動前 modal + 啟動按鈕
      MonitorSide.jsx        # 左側監控欄
      ControlPanel.jsx       # 暫停/正常停止/緊急停止按鈕組
    ai/
      aiStorage.jsx          # localStorage 操作（純函式）
      ChatArea.jsx
      ChatSidebar.jsx        # 對話列表，標題超 20 字截斷
      MessageBubble.jsx
      useAIChat.jsx          # AI 對話 custom hook
  App.jsx                    # 路由、登入、session 管理、role 控制
  Dashboard.jsx
  SOPPage.jsx                # 主頁面，只負責狀態協調
  ErrorLog.jsx
  AIPage.jsx
  FixturePage.jsx            # 治具管理（總表/借出中/逾期未還 + Modal）
  api.js                     # axios instance，含 401 interceptor
```

### 治具管理後端 API（已完成）

| 端點 | 說明 |
|------|------|
| `GET /api/fixtures/` | 治具列表（含 loaned_quantity / available_quantity）|
| `GET /api/fixtures/summary` | 摘要（total_loaned / due_today / overdue / shortage_count）|
| `GET /api/fixtures/interface-types` | 介面類型清單（篩選用）|
| `GET /api/fixtures/{id}` | 單一治具詳情 |
| `GET /api/fixtures/loans/active` | 借出中清單 |
| `GET /api/fixtures/loans/overdue` | 逾期清單（含 overdue_days）|
| `POST /api/fixtures/loans` | 新增借出登記 |
| `POST /api/fixtures/loans/{id}/return` | 歸還確認 |
| `POST /api/fixtures/loans/{id}/extend` | 申請延期 |
| `POST /api/fixtures/import` | Excel 批次匯入 |
| `POST /api/fixtures/{id}/inventory` | 月盤點回填實際數量 |

### 資料庫（現有）

| 表格 | 說明 | 索引 |
|------|------|------|
| `device_data` | 歷史溫濕度，每 10 秒 | (device_id, timestamp) |
| `device_states` | 狀態持久化，含 sim_phase、sim_cycle、started_at | device_id |
| `sop_executions` | 執行主表，含 operator | id, created_at |
| `step_records` | 步驟完成狀態 | execution_id, step_index |
| `error_logs` | 緊急停止事件，含 completed_steps、total_steps | device_id, created_at |
| `fixtures` | 治具基本資料 | id, interface_type |
| `fixture_loans` | 借出紀錄（fixture_id, borrower, device, project, 狀態）| id, fixture_id |
| `users` | 工程師名單（帳號/密碼/LINE ID/權限）| id |
| `purchase_orders` | 採購紀錄 | id |

### 前端輪詢頻率（現有）

| 元件 | 頻率 | 備註 |
|------|------|------|
| Dashboard 設備狀態 | 10s | 隱藏時暫停 |
| Dashboard 執行紀錄 | 60s | 隱藏時暫停 |
| SOPPage 設備狀態 | 3s | 隱藏時暫停 |
| ErrorLog | 60s | 隱藏時暫停 |
| FixturePage | 手動觸發 | fetchAll 於 active 變化時執行 |

### AI 模組

- **推理**：`gemini-2.5-flash-lite`，1000 次/天免費，temperature=0.3
- **向量化**：`gemini-embedding-001`，啟動時批次向量化（20 條/批，批次間等 5 秒），快取至 `rag_cache.pkl`
- **RAG 檢索**：法規條件靜態檢索，治具說明靜態檢索，治具即時庫存查詢走 DB 不走 RAG
- **歷史繼承**：未指定標準時自動從 history 抓之前提過的標準
- **預設推薦**：預設推 IEC 60068，明確說鐵道/船舶/海事/變電站才推對應標準
- **多輪對話**：MAX_HISTORY = 4；localStorage key：`dqa_ai_chats_v2`
- **輸入**：Enter 送出，Shift+Enter 換行

### Auth 升級規格（未實作，規劃用）

| 端點 | 說明 |
|------|------|
| `POST /api/auth/login` | 帳號 + 密碼 → JWT |
| `GET /api/auth/me` | 當前使用者 role / name / line_user_id |
| `POST /api/auth/users` | admin only，新增帳號 |
| `PATCH /api/auth/users/{id}` | admin only，修改 role / 停用帳號 |

- 推薦套件：`python-jose[cryptography]` + `passlib[bcrypt]`
- JWT middleware 取代 `X-Demo-Password` header
- guest 模式保留：demo 密碼換取 guest JWT（role=guest）

### 三層權限（Auth 升級後）

| 功能 | 管理者 | 保管人 | 工程師 |
|------|--------|--------|--------|
| 全部功能 + 報表 | ✅ | ❌ | ❌ |
| 治具借出/歸還登記 | ✅ | ✅ | ❌ |
| 月盤點回填 | ✅ | ✅ | ❌ |
| 報廢執行 | ✅ | ❌ | ❌ |
| 排程確認 | ✅ | ❌ | ❌ |
| 看治具總表 | ✅ | ✅ | ✅ |
| 看自己借出紀錄 | ✅ | ✅ | ✅ |
| 申請延期 | ✅ | ✅ | ✅ |
| 查看排程甘特圖 | ✅ | ✅ | ✅ |

### 欄位命名規範

- `dwell_time_hours`（非 `dwell_time`）
- `humidity_rh_percent`（非 `humidity`）
- 避免縮寫，保持一致性

### Alembic 注意事項

SQLite autogenerate 有時產生空的 `upgrade()`，需手動填入。若 `alembic upgrade head` 無動作：

```bash
# 直接在資料庫執行 SQL（替換表名稱與欄位）
sqlite3 backend/dqa_lab.db "ALTER TABLE table_name ADD COLUMN col_name TYPE;"
```

---

## 常用指令

```bash
# 安裝與初始化
make install                   # 安裝所有依賴
python backend/init_db.py      # 首次初始化資料庫

# 開發
make dev                       # 啟動全部服務（含 ngrok）
make clean                     # 清理殘留程序

# 資料庫遷移（在 backend/ 目錄下）
alembic revision --autogenerate -m "描述"
alembic upgrade head
alembic downgrade -1           # 回退上一個遷移

# 測試
python -m pytest backend/tests/
pytest client/src/components/__tests__/

# 清理測試 DB
rm backend/test.db
```

---

## 開發檢查清單

### 新增功能前
- [ ] 確認功能優先度（P1 / P2 / P3）
- [ ] 檢查是否涉及 DB 結構變更
- [ ] 檢查是否需要新增 API 端點

### 提交前
- [ ] 運行 `make dev`，檢查無明顯錯誤
- [ ] 確認 `backend/.env` 已填入必要變數
- [ ] 檢查 `requirements.txt` 與 `package.json` 是否需要更新
- [ ] 更新本文件的「當前狀態快照」

### 雲端部署前（如適用）
- [ ] 本地 `make dev` 測試無誤
- [ ] 確認敏感資訊未洩露（檢查 README、代碼註解）
- [ ] 清除本地密碼與 `.env` 相關資訊

---

## 參考資源

- [FastAPI 官方文件](https://fastapi.tiangolo.com/)
- [React 官方文件](https://react.dev/)
- [SQLAlchemy 官方文件](https://docs.sqlalchemy.org/)
- [Gemini API 文件](https://ai.google.dev/)
- [LINE Messaging API](https://developers.line.biz/en/services/messaging-api/)
- [APScheduler 官方文件](https://apscheduler.readthedocs.io/)
- [python-jose](https://python-jose.readthedocs.io/)

---

## 備註

本文件為本地開發參考，不推送至 GitHub。敏感資訊（API 密鑰、部署 URL）請保存在 `.env` 檔案中。