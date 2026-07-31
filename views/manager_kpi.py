import streamlit as st
import numpy as np

from data_utils import (
    get_managers, get_active_months, build_manager_actuals,
    load_manager_kpi_targets, MONTH_ORDER, QUARTER_MAP,
)


def _fmt_money(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return f"{int(round(v)):,}원"


def _fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return f"{v * 100:,.2f}%"


def _safe_div(a, b):
    if b is None or (isinstance(b, float) and np.isnan(b)) or b == 0:
        return np.nan
    return a / b


def render(df):
    st.title("🧑‍💼 매니저별 진척관리")

    if df is None:
        st.info("왼쪽 사이드바에서 ALL데이터 엑셀 파일을 업로드하면 결과가 표시됩니다.")
        return

    managers = get_managers(df)
    active_months = get_active_months(df)

    if not managers:
        st.warning("담당자('비고1') 정보가 있는 데이터가 없어요.")
        return

    actuals = build_manager_actuals(df, managers)  # index=(담당자,지표), columns=합계+월

    # ---- KPI 목표 (담당자별 고정 KPI 백데이터, 읽기 전용) ----
    kpi_targets = load_manager_kpi_targets()
    if not kpi_targets:
        st.warning("KPI 백데이터 파일(`data/kpi_manager_targets.xlsx`)을 찾지 못했어요. KPI 값 없이 실적만 표시할게요.")

    def _kpi_value(manager, metric, col):
        m = kpi_targets.get(manager)
        if not m:
            return np.nan
        row = m.get(metric)
        if not row:
            return np.nan
        return row.get(col, np.nan)

    # ---- 집계표 구성 ----
    st.subheader("매니저별 진척 현황")
    if len(active_months) < len(MONTH_ORDER):
        st.caption(f"결산 데이터가 있는 월({', '.join(active_months)})만 표시하고 있어요. 나머지 월은 데이터가 들어오면 자동으로 나타나요.")

    METRICS = ["매출 KPI", "GP KPI", "매출 결과", "GP 결과", "매출 달성률(%)", "GP 달성률(%)"]
    COLS = ["합계"] + active_months  # 화면 표시용 (비활성 월 숨김)

    def build_group_rows(sales_kpi_row, gp_kpi_row, rev_row, gp_row):
        rows = {}
        rows["매출 KPI"] = sales_kpi_row
        rows["GP KPI"] = gp_kpi_row
        rows["매출 결과"] = rev_row
        rows["GP 결과"] = gp_row
        rows["매출 달성률(%)"] = {c: _safe_div(rev_row[c], sales_kpi_row[c]) for c in COLS}
        rows["GP 달성률(%)"] = {c: _safe_div(gp_row[c], gp_kpi_row[c]) for c in COLS}
        return rows

    groups = []

    # 부서 총합 (KPI는 백데이터의 '부서 총합' 행을 그대로 사용, 실적은 담당자 실적 합산)
    total_sales_kpi = {c: _kpi_value("부서 총합", "매출 KPI", c) for c in COLS}
    total_gp_kpi = {c: _kpi_value("부서 총합", "GP KPI", c) for c in COLS}
    total_rev = {c: (actuals.xs("매출 결과", level="지표")["합계"].sum() if c == "합계" else actuals.xs("매출 결과", level="지표")[c].sum()) for c in COLS}
    total_gp = {c: (actuals.xs("GP 결과", level="지표")["합계"].sum() if c == "합계" else actuals.xs("GP 결과", level="지표")[c].sum()) for c in COLS}
    groups.append(("부서 총합", build_group_rows(total_sales_kpi, total_gp_kpi, total_rev, total_gp)))

    for manager in managers:
        sales_kpi_row = {c: _kpi_value(manager, "매출 KPI", c) for c in COLS}
        gp_kpi_row = {c: _kpi_value(manager, "GP KPI", c) for c in COLS}
        rev_row = {c: actuals.loc[(manager, "매출 결과"), c] for c in COLS}
        gp_row = {c: actuals.loc[(manager, "GP 결과"), c] for c in COLS}
        groups.append((manager, build_group_rows(sales_kpi_row, gp_kpi_row, rev_row, gp_row)))

    # ---- 분기 헤더 구성 (활성 월만 그룹핑) ----
    quarter_groups = []
    for q in ["1Q", "2Q", "3Q", "4Q"]:
        months_in_q = [m for m in active_months if QUARTER_MAP[m] == q]
        if months_in_q:
            quarter_groups.append((q, months_in_q))

    # ---- HTML 렌더링 ----
    html = """
    <style>
    .mgr-table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .mgr-table th, .mgr-table td {
        text-align: center !important;
        padding: 7px 8px;
        border: 1px solid #d9dce3;
        color: #1f2937 !important;
        white-space: nowrap;
    }
    .mgr-table thead th {
        background-color: #1f2a44 !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    .mgr-table td.rowlabel {
        background-color: #f3f4f8 !important;
        font-weight: 600;
    }
    .mgr-table td.manager-cell {
        background-color: #e4e8f5 !important;
        font-weight: 700;
    }
    .mgr-table td.total-cell {
        background-color: #eef1fb !important;
        font-weight: 700;
    }
    .mgr-table tr.dept-total td {
        background-color: #fdf3e0 !important;
        font-weight: 700;
    }
    </style>
    <table class="mgr-table">
    <thead>
    <tr>
    <th rowspan="2">담당자</th><th rowspan="2">구분</th><th rowspan="2">합계</th>
    """
    for q, months_in_q in quarter_groups:
        html += f'<th colspan="{len(months_in_q)}">{q}</th>'
    html += "</tr><tr>"
    for q, months_in_q in quarter_groups:
        for month in months_in_q:
            html += f"<th>{month}</th>"
    html += "</tr></thead><tbody>"

    for gname, rows in groups:
        is_total = (gname == "부서 총합")
        for i, metric in enumerate(METRICS):
            row_class = ' class="dept-total"' if is_total else ""
            html += f"<tr{row_class}>"
            if i == 0:
                cell_cls = "total-cell" if is_total else "manager-cell"
                html += f'<td rowspan="{len(METRICS)}" class="{cell_cls}">{gname}</td>'
            html += f'<td class="rowlabel">{metric}</td>'
            for c in COLS:
                v = rows[metric][c]
                if "달성률" in metric:
                    text = _fmt_pct(v)
                else:
                    text = _fmt_money(v)
                cls = ' class="total-cell"' if c == "합계" else ""
                html += f"<td{cls}>{text}</td>"
            html += "</tr>"

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)
