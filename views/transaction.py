import streamlit as st

from data_utils import build_transaction_view, get_active_months, QUARTER_MAP, MONTH_ORDER


def _fmt_money(v):
    if v is None:
        return ""
    return f"{int(round(v)):,}원"


def _fmt_count(v):
    if v is None:
        return ""
    return f"{int(v):,}"


def render(df):
    st.title("📑 영업 거래별 (다이렉트/벤더 구분)")

    if df is None:
        st.info("왼쪽 사이드바에서 ALL데이터 엑셀 파일을 업로드하면 결과가 표시됩니다.")
        return

    with st.expander("다이렉트 / 벤더 / PA / 기타 구분 설명", expanded=False):
        st.markdown(
            "- **다이렉트(셀러)**: 셀러와 우리 회사가 직접 거래한 건\n"
            "- **벤더사**: 벤더사가 셀러 영업·진행을 대신해줘서 성사된 거래 (벤더사명별로 하위 전개)\n"
            "- **PA**: 우리 부서에서 운영 중인 인스타 광고\n"
            "- **기타**: 운영비 등 기타 비용이 발생했을 때 별도로 구분해둔 값"
        )

    active_months = get_active_months(df)
    if len(active_months) < len(MONTH_ORDER):
        st.caption(f"결산 데이터가 있는 월({', '.join(active_months)})만 표시하고 있어요.")

    blocks = build_transaction_view(df, active_months)

    COLS = ["합계"] + active_months
    quarter_groups = []
    for q in ["1Q", "2Q", "3Q", "4Q"]:
        months_in_q = [m for m in active_months if QUARTER_MAP[m] == q]
        if months_in_q:
            quarter_groups.append((q, months_in_q))

    # ---- 다이렉트/벤더(대분류) rowspan 계산 ----
    category_rowcount = {}
    for b in blocks:
        n_metric_rows = len(b["metrics"])
        category_rowcount[b["category"]] = category_rowcount.get(b["category"], 0) + n_metric_rows

    html = """
    <style>
    .tx-table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .tx-table th, .tx-table td {
        text-align: center !important;
        padding: 6px 8px;
        border: 1px solid #d9dce3;
        color: #1f2937 !important;
        white-space: nowrap;
    }
    .tx-table thead th {
        background-color: #1f2a44 !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    .tx-table td.cat-cell {
        background-color: #e4e8f5 !important;
        font-weight: 700;
    }
    .tx-table td.sub-cell {
        background-color: #f3f4f8 !important;
        font-weight: 600;
    }
    .tx-table td.metric-cell {
        background-color: #fafafc !important;
    }
    .tx-table td.total-cell {
        background-color: #eef1fb !important;
        font-weight: 700;
    }
    .tx-table tr.all-row td {
        background-color: #fdf3e0 !important;
        font-weight: 700;
    }
    .tx-table td.vendor-sub {
        color: #6b7280 !important;
        font-weight: 500;
    }
    </style>
    <table class="tx-table">
    <thead>
    <tr>
    <th rowspan="2">다이렉트/벤더</th><th rowspan="2">세부</th><th rowspan="2">인원수</th>
    <th rowspan="2">지표</th><th rowspan="2">합계</th>
    """
    for q, months_in_q in quarter_groups:
        html += f'<th colspan="{len(months_in_q)}">{q}</th>'
    html += "</tr><tr>"
    for q, months_in_q in quarter_groups:
        for month in months_in_q:
            html += f"<th>{month}</th>"
    html += "</tr></thead><tbody>"

    prev_category = None
    for b in blocks:
        is_all = b["category"] == "ALL"
        metrics = b["metrics"]
        metric_names = list(metrics.keys())
        n_rows = len(metric_names)

        for i, metric in enumerate(metric_names):
            row_class = ' class="all-row"' if is_all else ""
            html += f"<tr{row_class}>"

            if b["category"] != prev_category:
                html += f'<td rowspan="{category_rowcount[b["category"]]}" class="cat-cell">{b["category"]}</td>'

            if i == 0:
                sub_text = b["sub"] if b["sub"] else "-"
                sub_cls = "sub-cell vendor-sub" if (b["category"] == "벤더사" and b["sub"] and "전체" not in b["sub"]) else "sub-cell"
                html += f'<td rowspan="{n_rows}" class="{sub_cls}">{sub_text}</td>'
                html += f'<td rowspan="{n_rows}" class="sub-cell">{b["headcount"]}명</td>'

            html += f'<td class="metric-cell">{metric}</td>'

            row_vals = metrics[metric]
            for c in COLS:
                v = row_vals.get(c)
                text = _fmt_count(v) if metric == "진행 횟수" else _fmt_money(v)
                cls = ' class="total-cell"' if c == "합계" else ""
                html += f"<td{cls}>{text}</td>"
            html += "</tr>"

        prev_category = b["category"]

    html += "</tbody></table>"

    st.markdown(html, unsafe_allow_html=True)
