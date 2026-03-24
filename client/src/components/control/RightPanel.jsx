import useAIChat from "../../ai/useAIChat";
import ChatArea from "../../ai/ChatArea";

const QUICK_QUESTIONS = [
  { label: "查庫存", text: "目前哪些治具庫存不足？" },
  { label: "問法規", text: "IEC 60068 有哪些常用測試條件？" },
  { label: "推薦治具", text: "推薦適合溫度循環測試的治具？" },
  { label: "算時長", text: "IEC 60068-2-14 Na 測試需要多久？" },
];

export default function RightPanel() {
  const {
    messages, input, loading, streamText,
    bottomRef, chatAreaRef, inputRef, textareaRef,
    sendMessage, stopStream, retryInTraditional,
    handleInputChange, handleKeyDown,
  } = useAIChat();

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
      <div
        style={{
          padding: "8px 10px 6px",
          fontSize: 11,
          color: "#484f58",
          fontWeight: 600,
          letterSpacing: 1,
          borderBottom: "1px solid #21262d",
          flexShrink: 0,
        }}
      >
        AI 諮詢
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
