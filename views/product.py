import streamlit as st

from data_utils import build_product_view, get_active_months, QUARTER_MAP, MONTH_ORDER


def _fmt_money(v):
    if v is None:
        return ""
    return f"{int(round(v)):,}원"


def render(df):
    st.title("🏷️ 상품별")

    if df is None:
        st.info("왼쪽 사이드바에서 ALL데이터 엑셀 파일을 업로드하면 결과가 표시됩니다.")
        return

    active_months = get_active_months(df)
    if len(active_months) < len(MONTH_ORDER):
        st.caption(f"결산 데이터가 있는 월({', '.join(active_months)})만 표시하고 있어요.")

    month_choice = st.selectbox("표시할 월", ["전체"] + active_months, key="product_month_filter")
    table_months = active_months if month_choice == "전체" else [month_choice]

    blocks = build_product_view(df, active_months)

    COLS = ["합계"] + table_months
    quarter_groups = []
    for q in ["1Q", "2Q", "3Q", "4Q"]:
        months_in_q = [m for m in table_months if QUARTER_MAP[m] == q]
        if months_in_q:
            quarter_groups.append((q, months_in_q))

    group_rowcount = {}
    for b in blocks:
        group_rowcount[b["group"]] = group_rowcount.get(b["group"], 0) + len(b["metrics"])

    html = """
    <style>
    .pd-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .pd-table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .pd-table th, .pd-table td {
        text-align: center !important;
        padding: 6px 8px;
        border: 1px solid #d9dce3;
        color: #1f2937 !important;
        white-space: nowrap;
    }
    .pd-table thead th {
        background-color: #1f2a44 !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    .pd-table td.group-cell {
        background-color: #e4e8f5 !important;
        font-weight: 700;
    }
    .pd-table td.sub-cell {
        background-color: #f3f4f8 !important;
        font-weight: 600;
    }
    .pd-table td.metric-cell {
        background-color: #fafafc !important;
    }
    .pd-table td.total-cell {
        background-color: #eef1fb !important;
        font-weight: 700;
    }
    .pd-table tr.all-row td {
        background-color: #fdf3e0 !important;
        font-weight: 700;
    }
    .pd-table tr.subtotal-row td {
        background-color: #eef2ff !important;
        font-weight: 700;
    }
    </style>
    <div class="pd-table-wrap">
    <table class="pd-table">
    <thead>
    <tr>
    <th rowspan="2">구분</th><th rowspan="2">카테고리</th><th rowspan="2">지표</th><th rowspan="2">합계</th>
    """
    for q, months_in_q in quarter_groups:
        html += f'<th colspan="{len(months_in_q)}">{q}</th>'
    html += "</tr><tr>"
    for q, months_in_q in quarter_groups:
        for month in months_in_q:
            html += f"<th>{month}</th>"
    html += "</tr></thead><tbody>"

    last_emitted_group = None
    for b in blocks:
        is_all = b["group"] == "ALL"
        is_subtotal = b["sub"] == "소계"
        metrics = b["metrics"]
        metric_names = list(metrics.keys())
        n_rows = len(metric_names)

        for i, metric in enumerate(metric_names):
            row_class = ""
            if is_all:
                row_class = ' class="all-row"'
            elif is_subtotal:
                row_class = ' class="subtotal-row"'
            html += f"<tr{row_class}>"

            if b["group"] != last_emitted_group:
                html += f'<td rowspan="{group_rowcount[b["group"]]}" class="group-cell">{b["group"]}</td>'
                last_emitted_group = b["group"]

            if i == 0:
                sub_text = b["sub"] if b["sub"] else "-"
                html += f'<td rowspan="{n_rows}" class="sub-cell">{sub_text}</td>'

            html += f'<td class="metric-cell">{metric}</td>'

            row_vals = metrics[metric]
            for c in COLS:
                v = row_vals.get(c)
                cls = ' class="total-cell"' if c == "합계" else ""
                html += f"<td{cls}>{_fmt_money(v)}</td>"
            html += "</tr>"

    html += "</tbody></table></div>"

    st.markdown(html, unsafe_allow_html=True)
