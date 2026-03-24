import useAIChat from "../../ai/useAIChat";
import ChatArea from "../../ai/ChatArea";

const QUICK_QUESTIONS = [
  { label: "查庫存", text: "目前哪些治具庫存不足？" },
  { label: "問法規", text: "IEC 60068 有哪些常用測試條件？" },
  { label: "推薦治具", text: "推薦適合溫度循環測試的治具？" },
  { label: "算時長", text: "IEC 60068-2-14 Na 測試需要多久？" },
];

const navBtn = (disabled) => ({
  background: "transparent",
  border: "none",
  color: disabled ? "#30363d" : "#8b949e",
  cursor: disabled ? "default" : "pointer",
  fontSize: 14,
  lineHeight: 1,
  padding: "0 3px",
  borderRadius: 3,
  flexShrink: 0,
});

const iconBtn = (disabled) => ({
  background: "transparent",
  border: "1px solid #30363d",
  color: disabled ? "#30363d" : "#8b949e",
  cursor: disabled ? "default" : "pointer",
  fontSize: 11,
  padding: "1px 5px",
  borderRadius: 3,
  flexShrink: 0,
});

export default function RightPanel() {
  const {
    activeId,
    conversations,
    messages,
    input,
    loading,
    streamText,
    bottomRef,
    chatAreaRef,
    inputRef,
    textareaRef,
    sendMessage,
    stopStream,
    retryInTraditional,
    handleInputChange,
    handleKeyDown,
    switchConversation,
    addConversation,
    clearConversation,
  } = useAIChat();

  // 依最後更新時間排序對話
  const convIds = Object.keys(conversations).sort(
    (a, b) => new Date(conversations[b]?.updatedAt || 0) - new Date(conversations[a]?.updatedAt || 0)
  );
  const total = convIds.length;
  const currentIdx = convIds.indexOf(activeId);
  const activeTitle = conversations[activeId]?.title || "新對話";
  const truncTitle = activeTitle.length > 10 ? activeTitle.slice(0, 10) + "…" : activeTitle;

  const goPrev = () => {
    if (loading || total <= 1) return;
    switchConversation(convIds[(currentIdx - 1 + total) % total]);
  };
  const goNext = () => {
    if (loading || total <= 1) return;
    switchConversation(convIds[(currentIdx + 1) % total]);
  };

  return (
    <div
      style={{
        width: 300,
        flexShrink: 0,
        borderLeft: "1px solid #30363d",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header：標題 + 對話切換列 */}
      <div
        style={{
          padding: "5px 8px",
          borderBottom: "1px solid #21262d",
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          gap: 4,
          minHeight: 30,
        }}
      >
        <span
          style={{
            fontSize: 11,
            color: "#484f58",
            fontWeight: 600,
            letterSpacing: 1,
            flexShrink: 0,
          }}
        >
          AI 諮詢
        </span>

        {/* 迷你對話切換 */}
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            overflow: "hidden",
          }}
        >
          <button
            onClick={goPrev}
            disabled={loading || total <= 1}
            title="上一個對話"
            style={navBtn(loading || total <= 1)}
          >
            ‹
          </button>
          <span
            title={activeTitle}
            style={{
              fontSize: 10,
              color: "#8b949e",
              maxWidth: 80,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {truncTitle}
          </span>
          <button
            onClick={goNext}
            disabled={loading || total <= 1}
            title="下一個對話"
            style={navBtn(loading || total <= 1)}
          >
            ›
          </button>
          {total > 1 && (
            <span style={{ fontSize: 9, color: "#484f58", flexShrink: 0 }}>
              {currentIdx + 1}/{total}
            </span>
          )}
        </div>

        {/* 新增 & 清除 */}
        <button
          onClick={() => addConversation()}
          disabled={loading}
          title="新增對話"
          style={iconBtn(loading)}
        >
          +
        </button>
        <button
          onClick={clearConversation}
          disabled={loading || messages.length === 0}
          title="清除目前對話"
          style={iconBtn(loading || messages.length === 0)}
        >
          ✕
        </button>
      </div>

      {/* 快速問題 */}
      <div
        style={{
          padding: "6px 8px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 4,
          flexShrink: 0,
          borderBottom: "1px solid #21262d",
        }}
      >
        {QUICK_QUESTIONS.map((q) => (
          <button
            key={q.label}
            onClick={() => sendMessage(q.text)}
            disabled={loading}
            style={{
              padding: "4px 6px",
              fontSize: 10,
              borderRadius: 4,
              border: "1px solid #30363d",
              background: "transparent",
              color: loading ? "#484f58" : "#8b949e",
              cursor: loading ? "not-allowed" : "pointer",
              textAlign: "center",
            }}
          >
            {q.label}
          </button>
        ))}
      </div>

      {/* 對話區 */}
      <div style={{ flex: 1, overflow: "hidden", minHeight: 0, display: "flex", flexDirection: "column" }}>
        <ChatArea
          messages={messages}
          loading={loading}
          streamText={streamText}
          input={input}
          chatAreaRef={chatAreaRef}
          bottomRef={bottomRef}
          inputRef={inputRef}
          textareaRef={textareaRef}
          onSend={sendMessage}
          onStop={stopStream}
          onRetry={retryInTraditional}
          onInputChange={handleInputChange}
          onKeyDown={handleKeyDown}
          compact
        />
      </div>
    </div>
  );
}
