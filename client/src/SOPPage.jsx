import React, { useState, useEffect, useRef, useCallback } from "react";
import api from "./api";
import MonitorSide from "./components/sop/MonitorSide";
import ControlPanel from "./components/sop/ControlPanel";
import ConditionCard from "./components/sop/ConditionCard";
import SelectGroup from "./components/sop/SelectGroup";
import StepList from "./components/sop/StepList";
import ExecutionPanel from "./components/sop/ExecutionPanel";
import SafetyChecklist from "./components/sop/SafetyChecklist";
import "./SOPPage.css";

const DEVICE_IDS = [
  "KSON_CH01",
  "KSON_CH02",
  "KSON_CH03",
  "KSON_CH04",
  "KSON_CH05",
];
const ACTIVE_STATUSES = ["RUNNING", "PAUSED"];

const initDeviceState = () => ({
  activeSop: null,
  completedSteps: {},
  savedExecutionId: null,
  safetyChecked: [false, false, false, false],
  chartHistory: [],
  chartStartedAt: null,
  selectedStd: null,
  selectedVer: null,
  selectedTest: null,
});

function restoreSelectionFromSopId(sopId, standardTree) {
  if (!sopId || !standardTree) return null;
  for (const [stdKey, stdData] of Object.entries(standardTree)) {
    for (const [verKey, verData] of Object.entries(stdData.versions || {})) {
      for (const [testKey, testData] of Object.entries(verData.tests || {})) {
        if (testData.sop_id === sopId)
          return {
            selectedStd: stdKey,
            selectedVer: verKey,
            selectedTest: testKey,
          };
      }
    }
  }
  return null;
}

const SOPPage = ({ active = true }) => {
  const [selectedDevice, setSelectedDevice] = useState("KSON_CH01");
  const [allDevices, setAllDevices] = useState({});
  const [deviceStates, setDeviceStates] = useState(() =>
    Object.fromEntries(DEVICE_IDS.map((id) => [id, initDeviceState()])),
  );
  const [emergencyFlash, setEmergencyFlash] = useState(false);
  const [standardTree, setStandardTree] = useState({});
  const [treeLoaded, setTreeLoaded] = useState(false);
  const [startError, setStartError] = useState("");
  const [starting, setStarting] = useState(false);
  const [pauseOptimistic, setPauseOptimistic] = useState(null);
  const [operator, setOperator] = useState(
    () => localStorage.getItem("dqa_operator") || "",
  );

  const historyFetchingRef = useRef(null);
  const lastHistoryMinuteRef = useRef(-1);

  const data = allDevices[selectedDevice] || {
    status: "OFFLINE",
    temperature: 0,
    humidity: 0,
    running_sop_name: "未連線",
    description: "等待連線...",
    timestamp: "--:--:--",
  };
  const ds = deviceStates[selectedDevice];
  const isActive = ACTIVE_STATUSES.includes(data.status);
  const isOffline = data.status === "OFFLINE";
  const isEmergency = data.status === "EMERGENCY";
  const canStop = isActive || isEmergency;
  const effectiveStatus = pauseOptimistic ?? data.status;
  const effectiveIsActive = ACTIVE_STATUSES.includes(effectiveStatus);
  const doneCnt = Object.values(ds.completedSteps).filter(Boolean).length;
  const allStepsDone =
    ds.activeSop && doneCnt === (ds.activeSop?.steps?.length ?? 0);

  const { selectedStd, selectedVer, selectedTest } = ds;
  const stdData = selectedStd ? standardTree[selectedStd] : null;
  const verData = selectedVer ? stdData?.versions?.[selectedVer] : null;
  const testData = selectedTest ? verData?.tests?.[selectedTest] : null;

  const updateDS = (id, patch) =>
    setDeviceStates((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));

  useEffect(() => {
    if (!isEmergency) {
      setEmergencyFlash(false);
      return;
    }
    const t = setInterval(() => setEmergencyFlash((f) => !f), 600);
    return () => clearInterval(t);
  }, [isEmergency]);

  useEffect(() => {
    if (pauseOptimistic && data.status !== "OFFLINE") setPauseOptimistic(null);
  }, [data.status]); // eslint-disable-line

  useEffect(() => {
    api
      .get("/api/sop/standards/tree")
      .then((r) => {
        setStandardTree(r.data);
        setTreeLoaded(true);
      })
      .catch(() => setTreeLoaded(true));
  }, []);

  const fetchHistory = useCallback((deviceId, startedAt) => {
    if (!startedAt) return;
    historyFetchingRef.current = deviceId;
    api
      .get(`/api/devices/${deviceId}/history`)
      .then((res) => {
        if (historyFetchingRef.current === deviceId)
          setDeviceStates((prev) => ({
            ...prev,
            [deviceId]: {
              ...prev[deviceId],
              chartHistory: res.data,
              chartStartedAt: startedAt,
            },
          }));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!active) return;
    const poll = () => {
      api
        .get("/api/devices")
        .then((r) => {
          const map = {};
          r.data.forEach((d) => {
            map[d.device_id] = d;
          });
          setAllDevices(map);
          setDeviceStates((prev) => {
            const next = { ...prev };
            DEVICE_IDS.forEach((id) => {
              const cur = map[id];
              if (!cur) return;
              const p = prev[id];
              let restoredSop = p.activeSop;
              if (!restoredSop && cur.active_sop_json) {
                try {
                  restoredSop = JSON.parse(cur.active_sop_json);
                } catch {
                  /* ignore */
                }
              }
              if (
                !cur.active_sop_json &&
                p.activeSop &&
                !ACTIVE_STATUSES.includes(cur.status)
              )
                restoredSop = null;
              const selPatch =
                restoredSop && !p.selectedStd && cur.active_sop_json
                  ? { _pendingRestoreSopId: restoredSop.sop_id }
                  : {};
              next[id] = { ...p, activeSop: restoredSop, ...selPatch };
            });
            return next;
          });
          const now = new Date();
          const min = now.getHours() * 60 + now.getMinutes();
          if (now.getSeconds() < 10 && min !== lastHistoryMinuteRef.current) {
            lastHistoryMinuteRef.current = min;
            if (map[selectedDevice]?.started_at)
              fetchHistory(selectedDevice, map[selectedDevice].started_at);
          }
        })
        .catch(() => {});
    };
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, [selectedDevice, active, fetchHistory]); // eslint-disable-line

  useEffect(() => {
    if (!treeLoaded) return;
    setDeviceStates((prev) => {
      const next = { ...prev };
      DEVICE_IDS.forEach((id) => {
        const pending = prev[id]._pendingRestoreSopId;
        if (pending && !prev[id].selectedStd) {
          const restored = restoreSelectionFromSopId(pending, standardTree);
          if (restored)
            next[id] = {
              ...prev[id],
              ...restored,
              _pendingRestoreSopId: undefined,
            };
        }
      });
      return next;
    });
  }, [treeLoaded, standardTree]);

  useEffect(() => {
    if (!active) return;
    lastHistoryMinuteRef.current = -1;
    const d = allDevices[selectedDevice];
    if (d?.started_at) fetchHistory(selectedDevice, d.started_at);
    else updateDS(selectedDevice, { chartHistory: [], chartStartedAt: null });
  }, [selectedDevice]); // eslint-disable-line

  useEffect(() => {
    const startedAt = allDevices[selectedDevice]?.started_at;
    if (!startedAt) {
      updateDS(selectedDevice, { chartHistory: [], chartStartedAt: null });
      return;
    }
    fetchHistory(selectedDevice, startedAt);
  }, [allDevices[selectedDevice]?.started_at]); // eslint-disable-line

  const startSop = async () => {
    if (!testData || starting) return;
    setStartError("");
    setStarting(true);
    if (operator.trim()) localStorage.setItem("dqa_operator", operator.trim());
    try {
      await api.post("/api/sop/start", {
        sop_id: testData.sop_id,
        device_id: selectedDevice,
      });
      const sopSteps = testData.steps || [];
      if (!sopSteps.length) {
        setStartError("⚠️ SOP 步驟資料不完整，請確認後端設定後重試。");
        return;
      }
      updateDS(selectedDevice, {
        activeSop: { ...testData, steps: sopSteps },
        completedSteps: {},
        savedExecutionId: null,
      });
    } catch (err) {
      setStartError(
        `❌ 啟動失敗：${err?.response?.data?.detail || err?.message || "未知錯誤"}`,
      );
    } finally {
      setStarting(false);
    }
  };

  const handleAction = async (type) => {
    if (type === "pause")
      setPauseOptimistic(effectiveStatus === "RUNNING" ? "PAUSED" : "RUNNING");
    try {
      await api.post(`/api/stop/${selectedDevice}/${type}`);
      if (type === "normal" || type === "emergency") {
        updateDS(selectedDevice, {
          activeSop: null,
          completedSteps: {},
          savedExecutionId: null,
          safetyChecked: [false, false, false, false],
        });
        setStartError("");
        setPauseOptimistic(null);
      }
    } catch (e) {
      console.error("[SOPPage] action:", e);
      setPauseOptimistic(null);
    }
  };

  const handleToggleStep = async (stepId, stepIndex) => {
    const steps = ds.activeSop?.steps || [];
    const newCompleted = { ...ds.completedSteps };
    if (newCompleted[stepId]) {
      if (!window.confirm(`取消「Step ${stepId}」將清除後續所有步驟，確定？`))
        return;
      steps.slice(stepIndex).forEach((s) => delete newCompleted[s.step_id]);
    } else {
      newCompleted[stepId] = true;
    }
    updateDS(selectedDevice, { completedSteps: newCompleted });
    try {
      await api.post(`/api/devices/${selectedDevice}/progress`, {
        completed: Object.values(newCompleted).filter(Boolean).length,
      });
    } catch (e) {
      console.error("[SOPPage] progress:", e);
    }
  };

  return (
    <div className="sop-page-layout">
      <MonitorSide
        selectedDevice={selectedDevice}
        allDevices={allDevices}
        data={data}
        ds={ds}
        doneCnt={doneCnt}
        isActive={isActive}
        isOffline={isOffline}
        isEmergency={isEmergency}
        onSelectDevice={setSelectedDevice}
      />

      <main className="control-side">
        <div className="scroll-wrapper">
          <ControlPanel
            selectedDevice={selectedDevice}
            data={data}
            emergencyFlash={emergencyFlash}
            effectiveStatus={effectiveStatus}
            effectiveIsActive={effectiveIsActive}
            canStop={canStop}
            isOffline={isOffline}
            isEmergency={isEmergency}
            onAction={handleAction}
          />

          {isActive && ds.activeSop && (
            <section
              className="operation-box"
              style={{ borderLeft: "3px solid #58a6ff" }}
            >
              <div className="box-header">
                <span>📋</span>
                <h2 style={{ fontSize: 13 }}>{ds.activeSop.name}</h2>
              </div>
              <StepList
                steps={ds.activeSop.steps || []}
                completedSteps={ds.completedSteps}
                onToggle={handleToggleStep}
              />
              {allStepsDone && (
                <ExecutionPanel
                  activeSop={ds.activeSop}
                  selectedDevice={selectedDevice}
                  completedSteps={ds.completedSteps}
                  operator={operator}
                  startedAt={data.started_at}
                  savedExecutionId={ds.savedExecutionId}
                  onSaved={(id) =>
                    updateDS(selectedDevice, { savedExecutionId: id })
                  }
                  onError={setStartError}
                />
              )}
            </section>
          )}

          {!isActive && (
            <>
              <section
                className="operation-box"
                style={{ borderLeft: "3px solid #58a6ff" }}
              >
                <div className="box-header">
                  <span>🔬</span>
                  <h2>選擇測試標準</h2>
                </div>
                {!treeLoaded ? (
                  <div
                    style={{ color: "#484f58", fontSize: 12, padding: "8px 0" }}
                  >
                    ⏳ 載入標準資料中...
                  </div>
                ) : (
                  <SelectGroup
                    step={1}
                    title="選擇法規"
                    accent="#58a6ff"
                    items={Object.entries(standardTree).map(([k, v]) => [
                      k,
                      v.label,
                    ])}
                    selected={selectedStd}
                    onSelect={(k) =>
                      updateDS(selectedDevice, {
                        selectedStd: k,
                        selectedVer: null,
                        selectedTest: null,
                      })
                    }
                  />
                )}
                {stdData && (
                  <>
                    <div
                      style={{
                        borderTop: "1px solid #21262d",
                        margin: "4px 0 14px",
                      }}
                    />
                    <div
                      style={{
                        fontSize: 11,
                        color: "#8b949e",
                        marginBottom: 10,
                        lineHeight: 1.5,
                      }}
                    >
                      {stdData.description}
                    </div>
                    <SelectGroup
                      step={2}
                      title="選擇版本 / Class"
                      accent="#f0a500"
                      items={Object.entries(stdData.versions).map(([k, v]) => [
                        k,
                        v.label,
                      ])}
                      selected={selectedVer}
                      onSelect={(k) =>
                        updateDS(selectedDevice, {
                          selectedVer: k,
                          selectedTest: null,
                        })
                      }
                    />
                  </>
                )}
                {verData && (
                  <>
                    <div
                      style={{
                        borderTop: "1px solid #21262d",
                        margin: "4px 0 14px",
                      }}
                    />
                    <div
                      style={{
                        fontSize: 11,
                        color: "#8b949e",
                        marginBottom: 10,
                        lineHeight: 1.5,
                      }}
                    >
                      {verData.description}
                    </div>
                    <SelectGroup
                      step={3}
                      title="選擇測試條件"
                      accent="#57ab5a"
                      items={Object.entries(verData.tests).map(([k, v]) => [
                        k,
                        v.name,
                      ])}
                      selected={selectedTest}
                      onSelect={(k) =>
                        updateDS(selectedDevice, { selectedTest: k })
                      }
                    />
                  </>
                )}
                {testData && <ConditionCard test={testData} />}
              </section>

              {testData && (
                <SafetyChecklist
                  operator={operator}
                  onOperatorChange={setOperator}
                  safetyChecked={ds.safetyChecked}
                  onSafetyChange={(i) => {
                    const u = [...ds.safetyChecked];
                    u[i] = !u[i];
                    updateDS(selectedDevice, { safetyChecked: u });
                  }}
                  testData={testData}
                  selectedDevice={selectedDevice}
                  starting={starting}
                  startError={startError}
                  onStart={startSop}
                />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default SOPPage;
