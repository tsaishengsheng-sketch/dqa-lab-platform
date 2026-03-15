// client/src/ai/aiStorage.js
const STORAGE_KEY = "dqa_ai_chats_v2";
const LEGACY_KEY = "dqa_ai_chat_history"; // 舊 key，遷移後刪除

export const genId = () =>
  `conv_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

export const createConversation = ({
  title = "新對話",
  projectGroup = "未分類",
} = {}) => ({
  id: genId(),
  title,
  projectGroup,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  messages: [],
});

const emptyStore = () => ({
  activeConversationId: null,
  conversations: {},
  projectGroups: ["未分類"],
});

const titleFrom = (messages) => {
  const first = messages?.find((m) => m.role === "user");
  if (!first) return "新對話";
  return first.content.slice(0, 20) + (first.content.length > 20 ? "…" : "");
};

/** 一次性遷移舊單對話格式 { version, messages } → 新格式 */
const migrate = (store) => {
  try {
    const raw = localStorage.getItem(LEGACY_KEY);
    if (!raw) return store;
    const parsed = JSON.parse(raw);
    // 相容兩種舊格式：純陣列 或 { version, messages }
    const msgs = Array.isArray(parsed) ? parsed : parsed?.messages;
    if (!Array.isArray(msgs) || msgs.length === 0) {
      localStorage.removeItem(LEGACY_KEY);
      return store;
    }
    const conv = createConversation({
      title: titleFrom(msgs),
      projectGroup: "未分類",
    });
    conv.messages = msgs;
    store.conversations[conv.id] = conv;
    store.activeConversationId = conv.id;
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    /* 遷移失敗不影響主流程 */
  }
  return store;
};

export const loadChats = () => {
  let store;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    store = raw ? JSON.parse(raw) : null;
  } catch {
    store = null;
  }

  if (!store) store = emptyStore();
  store = migrate(store);

  if (Object.keys(store.conversations).length === 0) {
    const conv = createConversation();
    store.conversations[conv.id] = conv;
    store.activeConversationId = conv.id;
  }
  return store;
};

export const saveChats = (store) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    /* storage full */
  }
};

export const deleteConversation = (store, id) => {
  const next = { ...store, conversations: { ...store.conversations } };
  delete next.conversations[id];

  if (Object.keys(next.conversations).length === 0) {
    const conv = createConversation();
    next.conversations[conv.id] = conv;
    next.activeConversationId = conv.id;
  } else if (next.activeConversationId === id) {
    const latest = Object.values(next.conversations).sort(
      (a, b) => new Date(b.updatedAt) - new Date(a.updatedAt),
    )[0];
    next.activeConversationId = latest.id;
  }
  return next;
};

export const exportChat = (messages, title = "對話紀錄") => {
  const lines = messages.map((m) => {
    const role = m.role === "user" ? "【使用者】" : "【AI 助手】";
    const time = m.elapsed ? ` (⏱ ${m.elapsed}s)` : "";
    const text = m.content
      .replace(/```[\w]*\n?/g, "")
      .replace(/```/g, "")
      .trim();
    return `${role}${time}\n${text}\n`;
  });
  const header =
    `DQA Lab 法規諮詢對話紀錄\n標題：${title}\n` +
    `匯出時間：${new Date().toLocaleString("zh-TW")}\n${"─".repeat(40)}\n\n`;
  const blob = new Blob([header + lines.join("\n")], {
    type: "text/plain;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `dqa_chat_${new Date().toISOString().slice(0, 10).replace(/-/g, "")}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};
