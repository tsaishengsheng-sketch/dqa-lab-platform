import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
  Tooltip,
  Brush,
  Legend,
} from "recharts";

const API = "http://localhost:8000";

const STATUS_CONFIG = {
  OFFLINE: { color: "#484f58", bg: "#21262d", label: "OFFLINE" },
  IDLE: { color: "#8b949e", bg: "#21262d", label: "IDLE" },
  RUNNING: { color: "#3fb950", bg: "#0f2318", label: "RUNNING" },
  PAUSED: { color: "#f0a500", bg: "#2d1f00", label: "PAUSED" },
  FINISHING: { color: "#58a6ff", bg: "#0d1f33", label: "FINISHING" },
  EMERGENCY: { color: "#f85149", bg: "#2d0f0f", label: "EMERGENCY" },
};

const card = {
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 12,
  padding: "20px 24px",
};

// ── 單台設備卡片 ──────────────────────────────────────────
const DeviceCard = ({ device, isSelected, onClick }) => {
  const sc = STATUS_CONFIG[device.status] || STATUS_CONFIG.OFFLINE;
  const isActive = ["RUNNING", "PAUSED", "FINISHING", "EMERGENCY"].includes(
    device.status,
  );

  return (
    <div
      onClick={onClick}
      style={{
        ...card,
        borderLeft: `3px solid ${sc.color}`,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        cursor: "pointer",
        outline: isSelected ? `2px solid ${sc.color}` : "none",
        outlineOffset: 2,
        transition: "outline 0.15s",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span
          style={{
            color: "#cdd9e5",
            fontWeight: 700,
            fontSize: 14,
            fontFamily: "monospace",
          }}
        >
          {device.device_id}
        </span>
        <span
          style={{
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 700,
            color: sc.color,
            background: sc.bg,
            border: `1px solid ${sc.color}44`,
          }}
        >
          {sc.label}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div>
          <div
            style={{
              color: "#484f58",
              fontSize: 10,
              letterSpacing: 1,
              marginBottom: 2,
            }}
          >
            TEMP
          </div>
          <div
            style={{
              color: "#ff7b72",
              fontSize: 36,
              fontWeight: 800,
              lineHeight: 1,
            }}
          >
            {device.temperature.toFixed(1)}
            <span style={{ fontSize: 14, color: "#484f58", marginLeft: 3 }}>
              °C
            </span>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              color: "#484f58",
              fontSize: 10,
              letterSpacing: 1,
              marginBottom: 2,
            }}
          >
            HUMI
          </div>
          <div
            style={{
              color: "#a5d6ff",
              fontSize: 36,
              fontWeight: 800,
              lineHeight: 1,
            }}
          >
            {device.humidity.toFixed(1)}
            <span style={{ fontSize: 14, color: "#484f58", marginLeft: 3 }}>
              %
            </span>
          </div>
        </div>
      </div>

      <div
        style={{
          padding: "8px 12px",
          background: "#0d1117",
          borderRadius: 6,
          border: "1px solid #21262d",
          fontSize: 12,
          color: isActive ? "#cdd9e5" : "#484f58",
        }}
      >
        {isActive ? device.running_sop_name : "STANDBY (IDLE)"}
      </div>

      {isActive && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 11,
            color: "#484f58",
          }}
        >
          <span>步驟進度</span>
          <span style={{ color: sc.color, fontWeight: 600 }}>
            {device.completed_steps || 0} /{" "}
            {(() => {
              try {
                const sop = device.active_sop_json
                  ? JSON.parse(device.active_sop_json)
                  : null;
                return sop?.steps?.length || "?";
              } catch {
                return "?";
              }
            })()}
          </span>
        </div>
      )}
    </div>
  );
};

// ── 主元件 ────────────────────────────────────────────────
const Dashboard = () => {
  const [devices, setDevices] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("KSON_CH01");
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const prevStartedAt = useRef(null);
  const lastAppendedMinute = useRef(null);
  const appendTimer = useRef(null);

  // 撈完整歷史
  const fetchFullHistory = useCallback(async (deviceId) => {
    setLoadingHistory(true);
    try {
      const res = await axios.get(`${API}/api/devices/${deviceId}/history`);
      setHistory(res.data);
      if (res.data.length > 0) {
        lastAppendedMinute.current = res.data[res.data.length - 1].full_time;
      } else {
        lastAppendedMinute.current = null;
      }
    } catch {
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // 每分鐘 append 最新一筆
  const appendLatestPoint = useCallback(async (deviceId) => {
    try {
      const res = await axios.get(`${API}/api/devices/${deviceId}/history`);
      const data = res.data;
      if (!data || data.length === 0) return;
      const latest = data[data.length - 1];
      if (latest.full_time !== lastAppendedMinute.current) {
        setHistory((prev) => [...prev, latest]);
        lastAppendedMinute.current = latest.full_time;
      }
    } catch {}
  }, []);

  // 切換設備時重撈歷史
  useEffect(() => {
    fetchFullHistory(selectedDevice);
    prevStartedAt.current = null;
    lastAppendedMinute.current = null;
  }, [selectedDevice, fetchFullHistory]);

  // 每分鐘 append
  useEffect(() => {
    if (appendTimer.current) clearInterval(appendTimer.current);
    appendTimer.current = setInterval(() => {
      appendLatestPoint(selectedDevice);
    }, 60_000);
    return () => clearInterval(appendTimer.current);
  }, [selectedDevice, appendLatestPoint]);

  // 每秒 polling 即時狀態 + 偵測測試重啟
  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const res = await axios.get(`${API}/api/devices`);
        setDevices(res.data);
        const current = res.data.find((d) => d.device_id === selectedDevice);
        if (current) {
          const newStartedAt = current.started_at;
          if (newStartedAt && newStartedAt !== prevStartedAt.current) {
            prevStartedAt.current = newStartedAt;
            fetchFullHistory(selectedDevice);
          } else if (!newStartedAt && prevStartedAt.current) {
            prevStartedAt.current = null;
            setHistory([]);
            lastAppendedMinute.current = null;
          }
        }
      } catch {}
    };
    const interval = setInterval(fetchDevices, 1000);
    fetchDevices();
    return () => clearInterval(interval);
  }, [selectedDevice, fetchFullHistory]);

  useEffect(() => {
    axios
      .get(`${API}/api/reports/list`)
      .then((r) => setExecutions(r.data))
      .catch(() => {});
  }, []);

  const runningCount = devices.filter((d) => d.status === "RUNNING").length;
  const emergencyCount = devices.filter((d) => d.status === "EMERGENCY").length;
  const idleCount = devices.filter((d) =>
    ["IDLE", "OFFLINE"].includes(d.status),
  ).length;
  const selectedDeviceData = devices.find(
    (d) => d.device_id === selectedDevice,
  );
  const sc = STATUS_CONFIG[selectedDeviceData?.status] || STATUS_CONFIG.OFFLINE;

  // Brush 預設最近 60 筆
  const brushEnd = Math.max(history.length - 1, 0);
  const brushStart = Math.max(brushEnd - 59, 0);

  return (
    <div
      style={{
        backgroundColor: "#0d1117",
        color: "#cdd9e5",
        minHeight: "100vh",
        padding: "24px 28px",
        fontFamily: "system-ui, -apple-system, sans-serif",
        boxSizing: "border-box",
        width: "100%",
      }}
    >
      {/* 標題列 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #30363d",
          paddingBottom: 16,
          marginBottom: 24,
        }}
      >
        <h1
          style={{ color: "#58a6ff", margin: 0, fontSize: 22, fontWeight: 700 }}
        >
          KSON AICM | Digital Twin
        </h1>
        <div style={{ display: "flex", gap: 10, fontSize: 12 }}>
          <span style={{ color: "#3fb950" }}>● 執行中 {runningCount}</span>
          <span style={{ color: "#f85149" }}>● 緊急 {emergencyCount}</span>
          <span style={{ color: "#484f58" }}>● 待機 {idleCount}</span>
        </div>
      </div>

      {/* 5 台設備卡片 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {devices.map((device) => (
          <DeviceCard
            key={device.device_id}
            device={device}
            isSelected={device.device_id === selectedDevice}
            onClick={() => setSelectedDevice(device.device_id)}
          />
        ))}
      </div>

      {/* 趨勢圖 */}
      <div style={{ ...card, marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                color: "#8b949e",
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: 1,
              }}
            >
              {selectedDevice} — TEMP / HUMI TREND
            </span>
            <span
              style={{
                padding: "1px 6px",
                borderRadius: 3,
                fontSize: 10,
                fontWeight: 700,
                color: sc.color,
                background: sc.bg,
                border: `1px solid ${sc.color}44`,
              }}
            >
              {selectedDeviceData?.status || "—"}
            </span>
            {loadingHistory && (
              <span style={{ color: "#484f58", fontSize: 10 }}>載入中...</span>
            )}
          </div>
          <div style={{ fontSize: 10, color: "#484f58" }}>
            {history.length > 0
              ? `共 ${history.length} 筆（每分鐘一點）｜拖拉下方 Brush 縮放`
              : "無測試資料"}
          </div>
        </div>

        {history.length === 0 ? (
          <div
            style={{
              height: 200,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#484f58",
              fontSize: 13,
            }}
          >
            {["IDLE", "OFFLINE"].includes(selectedDeviceData?.status)
              ? "設備待機中，尚無測試資料"
              : "等待資料累積（每 10 秒存一筆，每分鐘顯示一點）"}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={history}
              margin={{ top: 5, right: 16, left: -10, bottom: 30 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#21262d"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                stroke="#30363d"
                tick={{ fontSize: 10, fill: "#484f58" }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#30363d"
                domain={["auto", "auto"]}
                tick={{ fontSize: 10, fill: "#484f58" }}
              />
              <Tooltip
                contentStyle={{
                  background: "#161b22",
                  border: "1px solid #30363d",
                  fontSize: 11,
                }}
                itemStyle={{ color: "#cdd9e5" }}
                labelStyle={{ color: "#8b949e", marginBottom: 4 }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "#8b949e", paddingTop: 4 }}
              />
              <Brush
                dataKey="time"
                startIndex={brushStart}
                endIndex={brushEnd}
                height={20}
                stroke="#30363d"
                fill="#0d1117"
                travellerWidth={6}
                style={{ fontSize: 9, fill: "#484f58" }}
              />
              <Line
                type="monotone"
                dataKey="temperature"
                name="溫度 (°C)"
                stroke="#ff7b72"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="humidity"
                name="濕度 (%RH)"
                stroke="#a5d6ff"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 執行紀錄 */}
      <div style={card}>
        <div
          style={{
            color: "#8b949e",
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: 1,
            marginBottom: 16,
          }}
        >
          執行紀錄 EXECUTION HISTORY
        </div>
        {executions.length === 0 ? (
          <div
            style={{
              color: "#484f58",
              fontSize: 13,
              textAlign: "center",
              padding: "20px 0",
            }}
          >
            尚無執行紀錄
          </div>
        ) : (
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid #30363d" }}>
                {["ID", "SOP ID", "執行時間", "報告"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "6px 12px",
                      textAlign: "left",
                      color: "#8b949e",
                      fontWeight: 600,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {executions.map((ex) => (
                <tr key={ex.id} style={{ borderBottom: "1px solid #21262d" }}>
                  <td style={{ padding: "8px 12px", color: "#484f58" }}>
                    #{ex.id}
                  </td>
                  <td
                    style={{
                      padding: "8px 12px",
                      color: "#cdd9e5",
                      fontFamily: "monospace",
                    }}
                  >
                    {ex.sop_id}
                  </td>
                  <td style={{ padding: "8px 12px", color: "#8b949e" }}>
                    {ex.created_at}
                  </td>
                  <td style={{ padding: "8px 12px" }}>
                    <button
                      onClick={() =>
                        window.open(`${API}/api/reports/csv/${ex.id}`, "_blank")
                      }
                      style={{
                        padding: "4px 10px",
                        background: "#1f6feb",
                        color: "#fff",
                        border: "none",
                        borderRadius: 4,
                        cursor: "pointer",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      📥 CSV
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
