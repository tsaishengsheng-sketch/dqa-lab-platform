import React from "react";

const SAFETY_CHECKS = [
  "測試孔是否用塑膠塞及抹布將兩邊塞緊，以免水氣跑出。",
  "線材類治具等移至上方後再塞，以免水氣往利用線材類治具流至設備上造成毀損。",
  "抹布末端勿留至 Sample 上，以免低溫轉高溫時水氣流至 Sample 上導致燒燬。",
  "電源頭請放在治具、線材類上或懸空在鐵架下方，勿放在鐵架上。",
];

// operator 狀態、safetyChecked 狀態由父元件傳入並管理
// 這樣啟動後 operator 值可繼續用於 LINE 推播與報告
const SafetyChecklist = ({
  operator,
  onOperatorChange,
  safetyChecked,
  onSafetyChange,
  testData,
  selectedDevice,
  starting,
  startError,
  onStart,
}) => {
  const checkedCount = safetyChecked.filter(Boolean).length;
  const allChecked = safetyChecked.every(Boolean);

  return (
    <section
      className="operation-box"
      style={{ borderLeft: "3px solid #f0a500" }}
    >
      <div className="box-header">
        <span>⚠️</span>
        <h2>上架驗證注意事項</h2>
      </div>

      {/* 操作人員姓名：移至啟動前填寫 */}
      <div
        style={{
          marginBottom: 16,
          padding: "12px 14px",
          background: "#0d1117",
          borderRadius: 8,
          border: "1px solid #30363d",
        }}
      >
        <label
          style={{
            fontSize: 11,
            color: "#8b949e",
            display: "block",
            marginBottom: 6,
            fontWeight: 600,
            letterSpacing: 0.5,
          }}
        >
          👤 操作人員姓名
        </label>
        <input
          type="text"
          value={operator}
          onChange={(e) => onOperatorChange(e.target.value)}
          placeholder="例：王小明（將寫入 ISO 17025 報告及 LINE 推播）"
          style={{
            width: "100%",
            padding: "8px 10px",
            background: "#161b22",
            border: "1px solid #30363d",
            borderRadius: 6,
            color: "#cdd9e5",
            fontSize: 12,
            boxSizing: "border-box",
          }}
        />
        {!operator.trim() && (
          <div style={{ fontSize: 10, color: "#f0a500", marginTop: 4 }}>
            ⚠️ 建議填寫，異常時 LINE 通知將帶入此姓名
          </div>
        )}
      </div>

      <p style={{ color: "#8b949e", fontSize: 12, marginBottom: 14 }}>
        啟動測試前，請確認以下所有項目（{checkedCount} / {SAFETY_CHECKS.length}{" "}
        已確認）：
      </p>

      {SAFETY_CHECKS.map((item, i) => (
        <label
          key={i}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            marginBottom: 10,
            cursor: "pointer",
            color: safetyChecked[i] ? "#57ab5a" : "#cdd9e5",
          }}
        >
          <input
            type="checkbox"
            checked={safetyChecked[i]}
            onChange={() => onSafetyChange(i)}
            style={{ marginTop: 3, accentColor: "#57ab5a", flexShrink: 0 }}
          />
          <span style={{ fontSize: 12 }}>
            {i + 1}. {item}
          </span>
        </label>
      ))}

      {/* 進度條 */}
      <div
        style={{
          height: 3,
          background: "#21262d",
          borderRadius: 2,
          overflow: "hidden",
          marginBottom: 8,
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 2,
            background: allChecked ? "#57ab5a" : "#f0a500",
            width: `${(checkedCount / SAFETY_CHECKS.length) * 100}%`,
            transition: "width 0.2s ease",
          }}
        />
      </div>

      {allChecked ? (
        <p style={{ color: "#57ab5a", fontSize: 12, marginTop: 6 }}>
          ✅ 所有注意事項已確認，可以啟動測試
        </p>
      ) : (
        <p style={{ color: "#f0a500", fontSize: 12, marginTop: 6 }}>
          ⚠️ 還差 {SAFETY_CHECKS.length - checkedCount} 項未確認
        </p>
      )}

      <button
        onClick={onStart}
        disabled={!allChecked || starting}
        style={{
          marginTop: 14,
          width: "100%",
          padding: "12px",
          background: !allChecked || starting ? "#21262d" : "#238636",
          color: !allChecked || starting ? "#484f58" : "#fff",
          border: `1px solid ${!allChecked || starting ? "#30363d" : "#2ea043"}`,
          borderRadius: 6,
          cursor: !allChecked || starting ? "not-allowed" : "pointer",
          fontWeight: 700,
          fontSize: 14,
          transition: "all .2s",
        }}
      >
        {starting
          ? "⏳ 啟動中..."
          : allChecked
            ? `🚀 啟動 ${selectedDevice}：${testData?.name}`
            : "請先確認所有注意事項"}
      </button>

      {startError && (
        <div
          style={{
            marginTop: 10,
            padding: "10px 14px",
            background: "#2d0f0f",
            border: "1px solid #f8514944",
            borderRadius: 6,
            color: "#f85149",
            fontSize: 12,
          }}
        >
          {startError}
        </div>
      )}
    </section>
  );
};

export default SafetyChecklist;
