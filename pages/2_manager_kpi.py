import streamlit as st
import pandas as pd
import numpy as np

from data_utils import load_all_data, get_managers, build_manager_actuals, MONTH_ORDER, QUARTER_MAP

st.title("🧑‍💼 매니저별 진척관리")
st.caption("'ALL데이터' 시트가 포함된 엑셀 파일을 업로드하면 담당자별 실적이 자동으로 집계됩니다. KPI 목표는 아래에서 직접 입력해주세요.")

uploaded = st.file_uploader("ALL데이터 엑셀 업로드 (.xlsx)", type=["xlsx"], key="manager_upload")

if uploaded is None:
    st.info("파일을 업로드하면 결과가 표시됩니다.")
    st.stop()

try:
    df = load_all_data(uploaded)
except ValueError as e:
    st.error(str(e))
    st.stop()

managers = get_managers(df)
if not managers:
    st.warning("담당자('비고1') 정보가 있는 데이터가 없어요.")
    st.stop()

actuals = build_manager_actuals(df, managers)  # index=(담당자,지표), columns=합계+월

# ---- KPI 목표 입력 ----
st.subheader("① KPI 목표 입력")
st.caption("담당자별 월 매출/GP 목표를 입력해주세요. 아직 목표가 없는 담당자는 비워두면 됩니다.")

def _init_kpi_df(key, managers):
    if key not in st.session_state or set(st.session_state[key].index) != set(managers):
        blank = pd.DataFrame(index=managers, columns=MONTH_ORDER, dtype="float64")
        # 기존 값 있으면 이어받기
        if key in st.session_state:
            for m in managers:
                if m in st.session_state[key].index:
                    blank.loc[m] = st.session_state[key].loc[m]
        st.session_state[key] = blank
    return st.session_state[key]

sales_kpi_input = _init_kpi_df("manager_sales_kpi", managers)
gp_kpi_input = _init_kpi_df("manager_gp_kpi", managers)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**매출 KPI (원)**")
    edited_sales = st.data_editor(
        sales_kpi_input, use_container_width=True, key="editor_sales_kpi",
        column_config={m: st.column_config.NumberColumn(m, format="%d") for m in MONTH_ORDER},
    )
    st.session_state["manager_sales_kpi"] = edited_sales
with col_b:
    st.markdown("**GP KPI (원)**")
    edited_gp = st.data_editor(
        gp_kpi_input, use_container_width=True, key="editor_gp_kpi",
        column_config={m: st.column_config.NumberColumn(m, format="%d") for m in MONTH_ORDER},
    )
    st.session_state["manager_gp_kpi"] = edited_gp

# ---- 집계표 구성 ----
st.subheader("② 매니저별 진척 현황")

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

METRICS = ["매출 KPI", "GP KPI", "매출 결과", "GP 결과", "매출 달성률(%)", "GP 달성률(%)"]
COLS = ["합계"] + MONTH_ORDER


def build_group_rows(name, sales_kpi_row, gp_kpi_row, rev_row, gp_row):
    rows = {}
    rows["매출 KPI"] = sales_kpi_row
    rows["GP KPI"] = gp_kpi_row
    rows["매출 결과"] = rev_row
    rows["GP 결과"] = gp_row
    rows["매출 달성률(%)"] = {c: _safe_div(rev_row[c], sales_kpi_row[c]) for c in COLS}
    rows["GP 달성률(%)"] = {c: _safe_div(gp_row[c], gp_kpi_row[c]) for c in COLS}
    return rows


groups = []

# 부서 총합
total_sales_kpi = {c: edited_sales[MONTH_ORDER].sum(skipna=True).reindex(MONTH_ORDER).to_dict().get(c) if c != "합계" else edited_sales[MONTH_ORDER].sum(skipna=True).sum() for c in COLS}
total_gp_kpi = {c: edited_gp[MONTH_ORDER].sum(skipna=True).reindex(MONTH_ORDER).to_dict().get(c) if c != "합계" else edited_gp[MONTH_ORDER].sum(skipna=True).sum() for c in COLS}
total_rev = {c: (actuals.xs("매출 결과", level="지표")[c].sum() if c != "합계" else actuals.xs("매출 결과", level="지표")["합계"].sum()) for c in COLS}
total_gp = {c: (actuals.xs("GP 결과", level="지표")[c].sum() if c != "합계" else actuals.xs("GP 결과", level="지표")["합계"].sum()) for c in COLS}
groups.append(("부서 총합", build_group_rows("부서 총합", total_sales_kpi, total_gp_kpi, total_rev, total_gp)))

for manager in managers:
    sales_kpi_row = {c: (edited_sales.loc[manager, c] if c != "합계" else edited_sales.loc[manager, MONTH_ORDER].sum(skipna=True)) for c in COLS}
    gp_kpi_row = {c: (edited_gp.loc[manager, c] if c != "합계" else edited_gp.loc[manager, MONTH_ORDER].sum(skipna=True)) for c in COLS}
    rev_row = {c: actuals.loc[(manager, "매출 결과"), c] for c in COLS}
    gp_row = {c: actuals.loc[(manager, "GP 결과"), c] for c in COLS}
    groups.append((manager, build_group_rows(manager, sales_kpi_row, gp_kpi_row, rev_row, gp_row)))

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
<th colspan="3">1Q</th><th colspan="3">2Q</th><th colspan="3">3Q</th><th colspan="3">4Q</th>
</tr>
<tr>
"""
for month in MONTH_ORDER:
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

st.caption("※ KPI 목표는 이 화면에서 입력한 값이 세션 동안 유지됩니다. 새로고침하거나 다른 사람이 열면 초기화되니, 정식 운영 전 저장 방식은 별도로 논의해요.")
