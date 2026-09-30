from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from app.dashboard_data import read_log_file, select_window


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "data" / "logs.jsonl"
CONFIG_PATH = ROOT / "config" / "dashboard.yaml"

st.set_page_config(
    page_title="LLMOps Monitor",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap');
    :root {
        --ink: #202723;
        --muted: #69736c;
        --paper: #f2f4ef;
        --panel: #fbfcf8;
        --line: #dce2d9;
        --green: #187d61;
        --lime: #d7f36a;
        --red: #bd4a3a;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stSidebar"] { background: #e7ebe3; border-right: 1px solid var(--line); }
    h1, h2, h3 { color: var(--ink); font-family: 'DM Sans', 'Segoe UI', sans-serif; }
    p, label, [data-testid="stMetricLabel"] { font-family: 'DM Sans', 'Segoe UI', sans-serif; }
    .dashboard-kicker { color: var(--green); font: 600 11px 'DM Mono', monospace; letter-spacing: 1px; text-transform: uppercase; }
    .dashboard-title { font: 700 32px 'DM Sans', 'Segoe UI', sans-serif; line-height: 1.15; margin: 5px 0 4px; }
    .dashboard-subtitle { color: var(--muted); font-size: 14px; margin-bottom: 18px; }
    .panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .panel-heading h3 { margin: 0; font-size: 17px; }
    .threshold { color: var(--muted); font: 11px 'DM Mono', monospace; white-space: nowrap; }
    .status-good, .status-bad, .status-neutral { font: 600 11px 'DM Mono', monospace; text-transform: uppercase; }
    .status-good { color: var(--green); }
    .status-bad { color: var(--red); }
    .status-neutral { color: var(--muted); }
    [data-testid="stVerticalBlockBorderWrapper"] { background: var(--panel); border-color: var(--line); border-radius: 6px; }
    [data-testid="stMetricValue"] { color: var(--ink); font-family: 'DM Mono', monospace; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    code { font-family: 'DM Mono', monospace; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30, show_spinner=False)
def load_dashboard_data(path: str, modified_ns: int) -> tuple[pd.DataFrame, int]:
    del modified_ns
    return read_log_file(Path(path))


def number_series(frame: pd.DataFrame, field: str) -> pd.Series:
    if field not in frame:
        return pd.Series(0.0, index=frame.index)
    return pd.to_numeric(frame[field], errors="coerce").fillna(0)


def minute_chart(frame: pd.DataFrame, fields: list[str], operation: str = "sum") -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=fields)
    series_frame = frame[["ts", *fields]].copy().set_index("ts")
    for field in fields:
        series_frame[field] = pd.to_numeric(series_frame[field], errors="coerce")
    if operation == "mean":
        return series_frame.resample("1min").mean().dropna(how="all")
    return series_frame.resample("1min").sum().fillna(0)


def threshold_status(value: float | None, threshold: dict) -> tuple[str, bool | None]:
    if value is None or pd.isna(value):
        return "No data", None
    limit = float(threshold["value"])
    passed = value <= limit if threshold["operator"] == "lte" else value >= limit
    return ("Within threshold" if passed else "Threshold exceeded"), passed


def render_panel_title(title: str, threshold_text: str, status: str, passed: bool | None) -> None:
    status_class = "status-neutral" if passed is None else ("status-good" if passed else "status-bad")
    st.markdown(
        f'<div class="panel-heading"><h3>{title}</h3><span class="{status_class}">{status}</span></div>'
        f'<div class="threshold">{threshold_text}</div>',
        unsafe_allow_html=True,
    )


def panel_config(dashboard: dict, panel_id: str) -> dict:
    return next(panel for panel in dashboard["panels"] if panel["id"] == panel_id)


try:
    dashboard_config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["dashboard"]
except (OSError, KeyError, yaml.YAMLError) as exc:
    st.error(f"Could not load dashboard contract: {exc}")
    st.stop()

st.sidebar.markdown("### View settings")
window_minutes = st.sidebar.selectbox(
    "Time window",
    options=[15, 30, dashboard_config["time_range_minutes"]],
    index=2,
    format_func=lambda value: f"Last {value} minutes",
)
st.sidebar.caption(f"Refreshes every {dashboard_config['refresh_seconds']} seconds")
st.sidebar.code("data/logs.jsonl", language=None)


@st.fragment(run_every=dashboard_config["refresh_seconds"])
def render_dashboard() -> None:
    try:
        modified_ns = LOG_PATH.stat().st_mtime_ns
    except OSError:
        st.error(f"Log file not found: {LOG_PATH}")
        return

    all_logs, skipped = load_dashboard_data(str(LOG_PATH), modified_ns)
    if all_logs.empty:
        st.warning("No valid log events yet. Start the API and send a request to populate the dashboard.")
        return

    logs = select_window(all_logs, window_minutes)
    latest = all_logs["ts"].max()
    latest_text = latest.strftime("%Y-%m-%d %H:%M:%S UTC")
    response_logs = logs.loc[logs["event"] == "response_sent"].copy()
    request_logs = logs.loc[logs["event"] == "request_received"]
    failed_logs = logs.loc[logs["event"] == "request_failed"]
    tool_success = response_logs.get("tool_success", pd.Series(index=response_logs.index, dtype=object))
    successful_tools = response_logs.loc[tool_success.notna()]

    st.markdown('<div class="dashboard-kicker">K4-L3B / Monitoring &amp; LLMOps</div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-title">Operations dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="dashboard-subtitle">Window ends at {latest_text} · '
        f'{len(request_logs):,} requests · source: local structured logs</div>',
        unsafe_allow_html=True,
    )

    latency_panel = panel_config(dashboard_config, "latency")
    latency = number_series(response_logs, "latency_ms")
    ttft = number_series(response_logs, "ttft_ms")
    latency_p50 = float(latency.quantile(0.50)) if not response_logs.empty else None
    latency_p95 = float(latency.quantile(0.95)) if not response_logs.empty else None
    latency_p99 = float(latency.quantile(0.99)) if not response_logs.empty else None
    ttft_p95 = float(ttft.quantile(0.95)) if not response_logs.empty else None
    status, passed = threshold_status(latency_p95, latency_panel["threshold"])

    traffic_panel = panel_config(dashboard_config, "traffic")
    traffic_by_minute = minute_chart(request_logs.assign(request_count=1), ["request_count"])
    traffic_count = len(request_logs)
    traffic_rate = traffic_count / window_minutes
    traffic_status, traffic_passed = threshold_status(traffic_rate, traffic_panel["threshold"])

    errors_panel = panel_config(dashboard_config, "errors")
    error_rate = len(failed_logs) / len(request_logs) * 100 if len(request_logs) else None
    retrieval_rate = (
        float((successful_tools["tool_success"] == True).sum() / len(successful_tools) * 100)
        if len(successful_tools)
        else None
    )
    errors_status, errors_passed = threshold_status(error_rate, errors_panel["threshold"])

    cost_panel = panel_config(dashboard_config, "cost")
    costs = number_series(response_logs, "cost_usd")
    total_cost = float(costs.sum()) if not response_logs.empty else None
    cost_status, cost_passed = threshold_status(total_cost, cost_panel["threshold"])

    tokens_panel = panel_config(dashboard_config, "tokens")
    tokens_in = number_series(response_logs, "tokens_in")
    tokens_out = number_series(response_logs, "tokens_out")
    total_tokens = float(tokens_in.sum() + tokens_out.sum()) if not response_logs.empty else None
    tokens_status, tokens_passed = threshold_status(total_tokens, tokens_panel["threshold"])

    quality_panel = panel_config(dashboard_config, "quality")
    quality_values = response_logs.get("quality_score", pd.Series(index=response_logs.index, dtype=object))
    quality = number_series(response_logs, "quality_score")
    quality = quality[quality_values.notna()]
    quality_mean = float(quality.mean()) if len(quality) else None
    quality_status, quality_passed = threshold_status(quality_mean, quality_panel["threshold"])

    latency_col, traffic_col = st.columns(2, gap="medium")
    with latency_col:
        with st.container(border=True):
            threshold = latency_panel["threshold"]
            render_panel_title(
                latency_panel["title"],
                f"P95 {threshold['operator']} {threshold['value']} {latency_panel['unit']}",
                status,
                passed,
            )
            metric_cols = st.columns(4)
            for column, label, value in zip(metric_cols, ["P50", "P95", "P99", "TTFT P95"], [latency_p50, latency_p95, latency_p99, ttft_p95]):
                column.metric(label, f"{value:,.0f} ms" if value is not None else "—")
            chart = minute_chart(response_logs.assign(latency_ms=latency), ["latency_ms"])
            if not chart.empty:
                st.line_chart(chart.rename(columns={"latency_ms": "Latency (ms)"}), height=190)
            else:
                st.caption("No response latency data in this window.")

    with traffic_col:
        with st.container(border=True):
            threshold = traffic_panel["threshold"]
            render_panel_title(
                traffic_panel["title"],
                f"Rate {threshold['operator']} {threshold['value']} requests/min",
                traffic_status,
                traffic_passed,
            )
            st.metric("Requests in window", f"{traffic_count:,}", f"{traffic_rate:.2f} requests/min")
            chart = traffic_by_minute.rename(columns={"request_count": "Requests"})
            if not chart.empty:
                st.bar_chart(chart, height=190)
            else:
                st.caption("No incoming requests in this window.")

    errors_col, cost_col = st.columns(2, gap="medium")
    with errors_col:
        with st.container(border=True):
            threshold = errors_panel["threshold"]
            render_panel_title(
                errors_panel["title"],
                f"Error rate {threshold['operator']} {threshold['value']}%",
                errors_status,
                errors_passed,
            )
            metric_cols = st.columns(2)
            metric_cols[0].metric("Error rate", f"{error_rate:.2f}%" if error_rate is not None else "—")
            metric_cols[1].metric("Retrieval success", f"{retrieval_rate:.1f}%" if retrieval_rate is not None else "—")
            if len(failed_logs) and "error_type" in failed_logs:
                breakdown = failed_logs["error_type"].fillna("unknown").value_counts().rename("Failures")
                st.bar_chart(breakdown, height=155)
            else:
                st.caption("No failed requests in this window.")

    with cost_col:
        with st.container(border=True):
            threshold = cost_panel["threshold"]
            render_panel_title(
                cost_panel["title"],
                f"Total {threshold['operator']} ${threshold['value']:.2f}",
                cost_status,
                cost_passed,
            )
            st.metric("Total cost", f"${total_cost:.4f}" if total_cost is not None else "—")
            chart = minute_chart(response_logs.assign(cost_usd=costs), ["cost_usd"])
            if not chart.empty:
                st.area_chart(chart.rename(columns={"cost_usd": "Cost (USD)"}), height=190)
            else:
                st.caption("No response cost data in this window.")

    tokens_col, quality_col = st.columns(2, gap="medium")
    with tokens_col:
        with st.container(border=True):
            threshold = tokens_panel["threshold"]
            render_panel_title(
                tokens_panel["title"],
                f"Total {threshold['operator']} {threshold['value']:,} tokens",
                tokens_status,
                tokens_passed,
            )
            metric_cols = st.columns(2)
            metric_cols[0].metric("Input", f"{tokens_in.sum():,.0f}")
            metric_cols[1].metric("Output", f"{tokens_out.sum():,.0f}")
            token_frame = response_logs.assign(tokens_in=tokens_in, tokens_out=tokens_out)
            chart = minute_chart(token_frame, ["tokens_in", "tokens_out"])
            if not chart.empty:
                st.area_chart(chart.rename(columns={"tokens_in": "Input", "tokens_out": "Output"}), height=190)
            else:
                st.caption("No token data in this window.")

    with quality_col:
        with st.container(border=True):
            threshold = quality_panel["threshold"]
            render_panel_title(
                quality_panel["title"],
                f"Mean {threshold['operator']} {threshold['value']:.2f}",
                quality_status,
                quality_passed,
            )
            st.metric("Mean quality score", f"{quality_mean:.3f}" if quality_mean is not None else "—")
            quality_frame = response_logs.assign(quality_score=number_series(response_logs, "quality_score"))
            quality_frame = quality_frame.loc[quality_frame["quality_score"] > 0]
            chart = minute_chart(quality_frame, ["quality_score"], operation="mean")
            if not chart.empty:
                st.line_chart(chart.rename(columns={"quality_score": "Quality score"}), height=190)
            else:
                st.caption("No quality scores in this window.")

    latest_age = max(0, int((pd.Timestamp.now(tz="UTC") - latest).total_seconds()))
    freshness = f"{latest_age}s old" if latest_age < 3600 else f"{latest_age // 60}m old"
    st.caption(f"Updated from log at {latest_text} · data freshness {freshness} · skipped records {skipped}")


render_dashboard()