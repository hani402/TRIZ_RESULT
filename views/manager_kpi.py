import streamlit as st
import numpy as np

from data_utils import (
    load_all_data, get_managers, get_active_months, build_manager_actuals,
    load_kpi_targets, save_kpi_targets_to_bytes, MONTH_ORDER, QUARTER_MAP,
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


def render():
    st.title("🧑‍💼 매니저별 진척관리")
    st.caption("'ALL데이터' 시트가 포함된 엑셀 파일을 업로드하면 담당자별 실적이 자동으로 집계됩니다.")

    uploaded = st.file_uploader("ALL데이터 엑셀 업로드 (.xlsx)", type=["xlsx"], key="manager_upload")

    if uploaded is None:
        st.info("파일을 업로드하면 결과가 표시됩니다.")
        return

    try:
        df = load_all_data(uploaded)
    except ValueError as e:
        st.error(str(e))
        return

    managers = get_managers(df)
    active_months = get_active_months(df)

    if not managers:
        st.warning("담당자('비고1') 정보가 있는 데이터가 없어요.")
        return

    actuals = build_manager_actuals(df, managers)  # index=(담당자,지표), columns=합계+월

    # ---- KPI 목표 입력 (저장된 백데이터로 초기값 채움) ----
    st.subheader("① KPI 목표 입력")
    st.caption("담당자별 월 매출/GP 목표예요. 저장된 값이 자동으로 채워지며, 수정 후 아래 '저장' 버튼으로 백데이터 파일을 갱신할 수 있어요.")

    def _init_kpi_df(key, managers):
        if key not in st.session_state or set(st.session_state[key].index) != set(managers):
            saved_sales, saved_gp = load_kpi_targets(managers)
            base = saved_sales if key == "manager_sales_kpi" else saved_gp
            st.session_state[key] = base
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

    save_col1, save_col2 = st.columns([1, 3])
    with save_col1:
        kpi_bytes = save_kpi_targets_to_bytes(edited_sales, edited_gp)
        st.download_button(
            "💾 KPI 목표 저장 (kpi_targets.xlsx)",
            data=kpi_bytes,
            file_name="kpi_targets.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with save_col2:
        st.caption("다운로드한 파일로 저장소의 `data/kpi_targets.xlsx`를 교체하면, 다음 접속부터 이 값이 기본으로 불러와져요.")

    # ---- 집계표 구성 ----
    st.subheader("② 매니저별 진척 현황")
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

    def _kpi_value(edited_df, manager, col):
        if col == "합계":
            return edited_df.loc[manager, MONTH_ORDER].sum(skipna=True)
        return edited_df.loc[manager, col]

    groups = []

    # 부서 총합
    total_sales_kpi = {c: sum((_kpi_value(edited_sales, m, c) or 0) for m in managers) for c in COLS}
    total_gp_kpi = {c: sum((_kpi_value(edited_gp, m, c) or 0) for m in managers) for c in COLS}
    total_rev = {c: (actuals.xs("매출 결과", level="지표")["합계"].sum() if c == "합계" else actuals.xs("매출 결과", level="지표")[c].sum()) for c in COLS}
    total_gp = {c: (actuals.xs("GP 결과", level="지표")["합계"].sum() if c == "합계" else actuals.xs("GP 결과", level="지표")[c].sum()) for c in COLS}
    groups.append(("부서 총합", build_group_rows(total_sales_kpi, total_gp_kpi, total_rev, total_gp)))

    for manager in managers:
        sales_kpi_row = {c: _kpi_value(edited_sales, manager, c) for c in COLS}
        gp_kpi_row = {c: _kpi_value(edited_gp, manager, c) for c in COLS}
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
