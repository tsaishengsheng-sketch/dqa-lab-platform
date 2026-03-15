# 📝 Changelog

所有版本修改紀錄集中於此，依日期倒序排列。


---

## 2026-03-15

**AI 諮詢 UI 改版 — 多對話管理**

- **feat**: `AIPage.jsx` 重構為純組裝層，拆分為 `client/src/ai/` 子模組
- **feat**: 新增 `ai/aiStorage.jsx`，localStorage 讀寫、舊資料自動遷移（`dqa_ai_chat_history` → `dqa_ai_chats_v2`）
- **feat**: 新增 `ai/useAIChat.jsx`，所有狀態邏輯抽離為 custom hook，支援多對話切換
- **feat**: 新增 `ai/MessageBubble.jsx`，單則訊息元件（含免責聲明、複製、計時、簡體偵測）
- **feat**: 新增 `ai/ChatArea.jsx`，右側對話區（串流輸出、Markdown 渲染、追問建議列）
- **feat**: 新增 `ai/ChatSidebar.jsx`，左側欄（對話列表、專案分組、新增/刪除/重新命名）
- **fix**: `App.jsx` AI 頁容器 `display: block` → `display: flex`，修正子元件 `height: 100%` 不生效問題
- **fix**: `AIPage.jsx` 加入 `flex: 1`，確保撐滿父層高度
- **fix**: `ChatSidebar.jsx` sidebar `overflow: hidden` → `overflowX: hidden`，修正新增分組 input 被縱向裁切無法顯示的問題

**AI 諮詢效能優化**

- **perf**: `ai.py` system prompt 移除詳細參數，只保留測試條件名稱，token 數從約 2500 降至約 800
- **perf**: `main.py` lifespan 加入 Ollama warm-up，解決第一次對話冷啟動不串流問題
- **fix**: `AIPage.jsx` 移除 resetBtn（功能與清除對話重複）
- **perf**: `AIPage.jsx` generateSuggestions 加 3s 延遲避免搶佔 Ollama 資源，history 從 6 則縮至 2 則
- **fix**: `AIPage.jsx` 空白頁面條數更新：6 大法規 64 條 → 5 大法規 78 條

**文件精簡**

- **refactor**: 移除 `AGENTS.md` 與 README 重複的 API 端點表格
- **docs**: 修正法規審查狀態，DNV 待審查

**法規正確性審查：DNV DNVGL-CG-0339:2015 修正**

- **fix**: `dnv.py` ClassA Damp Heat `power_on` False → True（法規 Sec.3[8.2.5] 測試期間通電）
- **fix**: `dnv.py` ClassA Damp Heat `humi_tolerance` 10.0 → 3.0（法規 Sec.3[8.6] 明文 +2%/-3%）
- **fix**: `dnv.py` ClassB Dry Heat name/description 修正（「泵室」→「箱體內部，temp rise ≥5°C」）
- DNV 法規審查完成，條數維持 14 條不變

---

## 2026-03-14


**法規正確性審查：IEC 61850-3 溫度循環、濕熱循環、IEC 60945 新建**

- **feat**: `iec61850.py` 新增 C1/C2/C3 各一條 Test Nb 溫度循環（sop_id 68→71）：
  - C1：-10°C ↔ +55°C / 3h/step / 5 cycles / 1°C/min
  - C2/C3：-40°C ↔ +70°C / 3h/step / 5 cycles / 1°C/min
- **fix**: `iec61850.py` C1 Damp Heat 濕度 95%RH → 93%RH
- **feat**: 新建 `iec60945.py`，IEC 60945:2002 共 7 條（乾熱儲存/工作、濕熱 Db variant 1、低溫儲存/工作）
- **feat**: `__init__.py` 加入 `iec60945` import 與 STANDARD_TREE 註冊，四個→五個子模組
- sop_id 總數：68 → 78；IEC 61850-3 條數：16 → 19

**文件整合**

- **docs**: 合併 `architecture.md` 進 `AGENTS.md`，刪除 `architecture.md`
- **docs**: README 延伸文件連結由 `architecture.md` 改為 `AGENTS.md`
- **chore**: 移除 `iec60068.py` / `iec61850.py` 中所有內部參考字串

---

## 2026-03-13

**法規正確性審查：standards/ 套件修正與新增**

- **feat**: `iec60068.py` 新增 IEC 60068-2-78 Test Cab 共 4 條（65°C / 90°C × 16h / 24h，95%RH，通電）
- **feat**: `iec61850.py` C1/C2/C3 各新增 Cab 高溫高濕（Method III）共 3 條：40°C / 93%RH / 240h
- **feat**: `iec61850.py` C1/C2/C3 各新增 Cab Non-Operating 16h（Method V）共 3 條
- **fix**: `iec61850.py` C1/C2/C3 乾熱 reference Bb → Be（Method IV）
- **feat**: `en50155.py` 新增 OT4_High_Operating / OT4_High_Operating_ST1 兩條通電測試
- **fix**: `iec60068.py` Test Nb dwell_time_hours 1h → 2h
- sop_id 總數：56 → 68；各法規條數：IEC 60068 17 條、EN 50155 21 條、IEC 61850-3 16 條、DNV 14 條

**Bug 修復與架構優化**

- **fix**: `main.py` `emergency_stop` crash 修正；timestamp 統一 `_now_utc()`；DB 寫入改呼叫 `_save_device_state()`
- **fix**: `sop.py` `start_sop` 新增 `total_steps` 存入 AICM_CACHE，修正 Dashboard 進度條不顯示的 bug
- **perf**: `ai.py` 新增 `_SYSTEM_PROMPT_CACHE`，system prompt 只建立一次
- **refactor**: `standards.py` 拆分為 `standards/` 套件（`__init__.py` / `_base.py` / 4 個法規模組）

---

## 2026-03-12

**AI 諮詢免責聲明 & 前端效能優化**

- **feat**: `AIPage.jsx` 雙層免責聲明（每則回覆固定顯示 + 空白頁面顯示）
- **feat**: `ai.py` system prompt 新增免責規則與法規版本號標注要求
- **perf**: `App.jsx` CSS display 切換取代 React Router unmount，四頁面常駐 DOM，切換無延遲
- **fix**: `SOPPage.jsx` treeLoaded skeleton；generateSP 低溫濕度為 null；ConditionCard 低溫補註
- **fix**: `Dashboard.jsx` 低溫濕度隱藏；趨勢圖低溫段 humidity 存 null（`connectNulls={false}`）
- **perf**: `sop.py` `/api/sop/standards/tree` 移除 steps 欄位（108kB → ~12kB）

---

## 2026-03-11

**AI 輔助模組 — 法規諮詢助手**

- **feat**: 新增 `backend/app/ai.py`，實作串流 + 非串流法規諮詢端點，串接本機 Ollama `qwen2.5:7b`
- **feat**: 新增 `client/src/AIPage.jsx`，串流輸出、Markdown 渲染、快速提問、中途停止、localStorage 持久化、智慧捲動、追問建議、雙層免責聲明

---

## 2026-03-10

**儀表板進度條 & 資料庫遷移**

- **feat**: 導入 Alembic 資料庫遷移管理
- **feat**: `main.py` 新增 `_calc_estimated_end_at()`、`/api/devices/{id}/progress` API
- **feat**: `models.py` `DeviceState` 新增 `completed_steps`、`started_at` 欄位
- **feat**: `Dashboard.jsx` 新增倒數計時器、趨勢圖 Brush 縮放、步驟進度條
- **feat**: `SOPPage.jsx` 新增執行資訊面板、SP+PV 波型曲線、步驟依序鎖定
- **fix**: startup 改為 asynccontextmanager lifespan；新增 `_now_utc()`；多項 models 型別修正

---

## 2026-03-06

- **feat**: `models.py` 新增 `DeviceState` 表，支援重啟後恢復狀態
- **feat**: `Dashboard.jsx` 趨勢圖改為可切換 5 台設備
- **fix**: 移除 `_cleanup_old_data()`，依 ISO/IEC 17025:2017 永久保存量測數據
- **chore**: `sop_execution.py` 合併進 `sop.py`

---

## 2026-03-04

- **feat**: 新增 `ErrorLog` 表與 `errors.py` router，新增異常看板頁面（`ErrorLog.jsx`）
- **feat**: `standards.py` 重構為三層巢狀 `STANDARD_TREE`
- **perf**: `device_data` 寫入頻率從每秒改為每 10 秒

---

## 2026-03-03

- **fix**: `FINISHING` 降溫完成後自動回 `IDLE`；暫停切換改為 `RUNNING ↔ PAUSED`
- **feat**: ISO 17025 格式測試報告（`reports.py`）

---

## 2026-03-02

- 整合 EN50155、IEC60068 環境測試標準，動態 SOP 管理系統，前端 SOP 列表動態載入