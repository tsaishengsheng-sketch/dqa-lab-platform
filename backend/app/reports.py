import io
import datetime
import urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from .models import SessionLocal, SopExecution, StepRecord, DeviceData
from .standards import STANDARDS_AND_SOPS

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORT_VERSION = "1.0"
LAB_NAME = "DQA Lab - KSON AICM Digital Twin"


def _write(output: io.BytesIO, text: str):
    output.write((text + "\r\n").encode("big5", errors="replace"))


def _section(output: io.BytesIO, title: str):
    _write(output, "")
    _write(output, "=" * 60)
    _write(output, f"  {title}")
    _write(output, "=" * 60)


def _row(output: io.BytesIO, label: str, value):
    _write(output, f"  {label:<30}{value}")


def _fmt_dt(dt) -> str:
    """安全格式化 datetime，支援 datetime 物件與 None"""
    if dt is None:
        return "N/A"
    if isinstance(dt, datetime.datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


@router.get("/csv/{execution_id}")
def download_csv_report(execution_id: int):
    """
    下載測試報告（依照 ISO/IEC 17025:2017 §7.8 格式）
    注意：
    - §7.8.6：符合性宣告（PASS/FAIL）須由授權人員判定，系統不自動產生
    - §7.5.1：技術記錄應包含責任人與日期
    - §8.4.2：原始數據依實際測試時間區間查詢，永久保存
    """
    with SessionLocal() as db:
        execution = (
            db.query(SopExecution).filter(SopExecution.id == execution_id).first()
        )
        if not execution:
            raise HTTPException(status_code=404, detail="找不到此執行紀錄")

        steps = (
            db.query(StepRecord)
            .filter(StepRecord.execution_id == execution_id)
            .order_by(StepRecord.step_id)
            .all()
        )

        # §7.5.2：依實際測試開始/結束時間查詢原始數據
        # 若無記錄則回報缺失，不使用模糊備用區間
        device_records = []
        if execution.test_started_at and execution.test_ended_at:
            device_id_filter = execution.device_id or "KSON_CH01"
            device_records = (
                db.query(DeviceData)
                .filter(
                    DeviceData.device_id == device_id_filter,
                    DeviceData.timestamp >= execution.test_started_at,
                    DeviceData.timestamp <= execution.test_ended_at,
                )
                .order_by(DeviceData.timestamp)
                .all()
            )
        else:
            device_id_filter = execution.device_id or "KSON_CH01"

        # 修正：直接用 sop_id 查，不需迴圈比對
        sop_data = STANDARDS_AND_SOPS.get(execution.sop_id, {})
        temp_tolerance = sop_data.get("temp_tolerance", 2.0)
        humi_tolerance = sop_data.get("humi_tolerance", 5.0)

        # 統計溫濕度數據
        temps = [r.temperature for r in device_records if r.temperature is not None]
        humis = [r.humidity for r in device_records if r.humidity is not None]

        temp_max = round(max(temps), 2) if temps else "N/A"
        temp_min = round(min(temps), 2) if temps else "N/A"
        temp_avg = round(sum(temps) / len(temps), 2) if temps else "N/A"
        humi_avg = round(sum(humis) / len(humis), 1) if humis else "N/A"

        target_high = sop_data.get("high_temperature") or sop_data.get(
            "target_temperature"
        )
        target_low = sop_data.get("low_temperature")

        # 產生報告
        output = io.BytesIO()
        report_no = f"RPT-{execution.created_at.strftime('%Y%m%d')}-{execution_id:03d}"

        _write(output, "")
        _write(output, "  " + "=" * 56)
        _write(output, f"  {LAB_NAME}")
        _write(output, "  環境測試報告  Environmental Test Report")
        _write(output, "  " + "=" * 56)

        # 1. 報告識別（ISO/IEC 17025:2017 §7.8.2）
        _section(output, "1. 報告識別  Report Identification")
        _row(output, "報告編號 Report No.:", report_no)
        _row(output, "報告版本 Version:", REPORT_VERSION)
        _row(
            output,
            "產生日期 Issue Date:",
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        _row(output, "執行記錄 ID:", execution_id)

        # 2. 受測樣品（§7.8.2.1 g, h）
        _section(output, "2. 受測樣品資訊  Test Item Information")
        _row(output, "設備編號 Device ID:", device_id_filter)
        _row(output, "SOP ID:", execution.sop_id)
        _row(output, "測試名稱 Test Name:", sop_data.get("name", "N/A"))
        _row(output, "測試類型 Test Type:", sop_data.get("test_type", "N/A"))
        _row(output, "SOP 版本 SOP Version:", sop_data.get("version", "N/A"))
        _row(output, "參考法規 Reference:", sop_data.get("reference", "N/A"))

        # 3. 測試條件（§7.8.3.1 a）
        _section(output, "3. 測試條件  Test Conditions")
        _row(output, "測試標準 Standard:", execution.sop_id)
        _row(output, "目標高溫 Target High (C):", target_high or "N/A")
        _row(output, "目標低溫 Target Low (C):", target_low or "N/A")
        _row(output, "升降溫速率 Ramp Rate (C/min):", sop_data.get("ramp_rate", "N/A"))
        # 修正：key 名稱由 dwell_time 改為 dwell_time_hours
        _row(
            output, "停留時間 Dwell Time (h):", sop_data.get("dwell_time_hours", "N/A")
        )
        _row(output, "循環次數 Cycles:", sop_data.get("cycles", "N/A"))
        # 修正：key 名稱由 humidity 改為 humidity_rh_percent
        _row(
            output,
            "濕度設定 Humidity (%RH):",
            sop_data.get("humidity_rh_percent", "N/A"),
        )
        _row(output, "溫度容差 Temp Tolerance (C):", f"± {temp_tolerance}")
        _row(output, "濕度容差 Humi Tolerance (%RH):", f"± {humi_tolerance}")
        _row(output, "測試開始 Start Time:", _fmt_dt(execution.test_started_at))
        _row(output, "測試結束 End Time:", _fmt_dt(execution.test_ended_at))
        _row(output, "紀錄建立 Record Created:", _fmt_dt(execution.created_at))
        _row(
            output,
            "數據筆數 Data Points:",
            len(device_records) if execution.test_started_at else "測試時間未記錄",
        )

        # 4. 步驟執行記錄（§7.5.1 責任人與日期）
        _section(output, "4. 步驟執行記錄  Step Execution Records")
        _row(output, "執行人員 Operator:", execution.operator or "(待填寫)")
        _write(output, "")
        _write(output, f"  {'步驟':>6}  {'狀態':<12}")
        _write(output, "  " + "-" * 30)
        for step in steps:
            status = "完成" if step.completed else "未完成"
            _write(output, f"  Step {step.step_id:<4}  {status}")
        if not steps:
            _write(output, "  (無步驟記錄)")

        # 5. 測試數據統計（§7.8.3.1 c 量測不確定度）
        _section(output, "5. 測試數據統計  Measurement Summary")
        _row(output, "最高溫度 Max Temp (C):", temp_max)
        _row(output, "最低溫度 Min Temp (C):", temp_min)
        _row(output, "平均溫度 Avg Temp (C):", temp_avg)
        _row(output, "平均濕度 Avg Humi (%RH):", humi_avg)
        _row(
            output,
            "溫度容差範圍 Temp Limit (C):",
            f"{round(target_high - temp_tolerance, 1)} ~ {round(target_high + temp_tolerance, 1)}"
            if target_high
            else "N/A",
        )
        _row(output, "量測不確定度 Uncertainty:", "待儀器校正證書確認")

        # 6. 測試結論（§7.8.6 & §7.8.7）
        _section(output, "6. 測試結論  Test Conclusion")
        _write(output, "  ※ 依照 ISO/IEC 17025:2017 §7.8.6 及 §7.8.7，")
        _write(output, "     符合性宣告及測試意見須由授權工程師人工判定。")
        _write(output, "")
        _row(output, "判定結果 Result:", "[          ]  (工程師人工填寫)")
        _row(output, "判定依據 Based on:", sop_data.get("reference", "IEC 60068"))
        _row(output, "判定人員 Judged by:", "(工程師簽名)")
        _row(output, "判定日期 Judge Date:", "(填寫日期)")

        # 7. 原始數據（§7.5.1 原始觀察結果）
        _section(output, "7. 原始溫濕度數據  Raw Temperature & Humidity Data")
        if not device_records:
            _write(output, "  (測試時間未記錄或無原始數據)")
        else:
            _write(output, f"  {'時間戳':<22}  {'溫度(C)':>10}  {'濕度(%RH)':>10}")
            _write(output, "  " + "-" * 48)
            for record in device_records:
                ts = record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                temp = (
                    f"{round(record.temperature, 2):.2f}"
                    if record.temperature is not None
                    else "N/A"
                )
                humi = (
                    f"{round(record.humidity, 1):.1f}"
                    if record.humidity is not None
                    else "N/A"
                )
                _write(output, f"  {ts:<22}  {temp:>10}  {humi:>10}")

        _write(output, "")
        _write(output, "  " + "=" * 56)
        _write(output, f"  報告結束  End of Report  [{report_no}]")
        _write(output, "  " + "=" * 56)
        _write(output, "")

        output.seek(0)
        filename = f"{report_no}_{execution.sop_id}.csv"
        # 修正：RFC 5987 編碼，支援非 ASCII 檔名
        encoded_filename = urllib.parse.quote(filename)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            },
        )


@router.get("/list")
def list_executions():
    """取得所有執行紀錄列表"""
    with SessionLocal() as db:
        executions = (
            db.query(SopExecution).order_by(SopExecution.created_at.desc()).all()
        )
        return [
            {
                "id": e.id,
                "sop_id": e.sop_id,
                "device_id": e.device_id,
                "operator": e.operator,
                "test_started_at": _fmt_dt(e.test_started_at),
                "test_ended_at": _fmt_dt(e.test_ended_at),
                "created_at": _fmt_dt(e.created_at),
            }
            for e in executions
        ]
