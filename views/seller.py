import streamlit as st

from data_utils import build_seller_view, build_seller_total, get_active_months, get_products, MONTH_ORDER


def _fmt_money(v):
    if v is None:
        return ""
    return f"{int(round(v)):,}원"


def _fmt_pct(v):
    if v is None:
        return ""
    return f"{v * 100:,.2f}%"


def render(df):
    st.title("🙋 셀러별")

    if df is None:
        st.info("왼쪽 사이드바에서 ALL데이터 엑셀 파일을 업로드하면 결과가 표시됩니다.")
        return

    active_months = get_active_months(df)
    if len(active_months) < len(MONTH_ORDER):
        st.caption(f"결산 데이터가 있는 월({', '.join(active_months)})만 표시하고 있어요.")

    col1, col2 = st.columns(2)
    with col1:
        products = get_products(df)
        product_choice = st.selectbox("상품 선택 (선택 안 하면 전체 상품 합산)", ["전체"] + products)
    with col2:
        month_choice = st.selectbox("표시할 월", ["전체"] + active_months, key="seller_month_filter")
    table_months = active_months if month_choice == "전체" else [month_choice]

    rows = build_seller_view(df, active_months, product=product_choice)
    total_row = build_seller_total(rows, active_months)
    st.caption(f"총 {len(rows):,}명의 셀러가 집계됐어요. (매출 높은 순 정렬, 맨 위는 전체 총합)")

    html = """
    <style>
    .sl-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .sl-table { border-collapse: collapse; width: 100%; font-size: 13px; }
    .sl-table th, .sl-table td {
        text-align: center !important;
        padding: 6px 8px;
        border: 1px solid #d9dce3;
        color: #1f2937 !important;
        white-space: nowrap;
    }
    .sl-table thead th {
        background-color: #1f2a44 !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    .sl-table td.info-cell {
        background-color: #f3f4f8 !important;
        font-weight: 600;
    }
    .sl-table td.total-cell {
        background-color: #eef1fb !important;
        font-weight: 700;
    }
    .sl-table tbody tr:nth-child(even) td:not(.info-cell):not(.total-cell) { background-color: #fafafc !important; }
    .sl-table tr.grand-total-row td {
        background-color: #fdf3e0 !important;
        font-weight: 700;
    }
    </style>
    <div class="sl-table-wrap">
    <table class="sl-table">
    <thead>
    <tr>
    <th rowspan="2">비전속</th><th rowspan="2">다이렉트/벤더</th><th rowspan="2">셀러명</th>
    <th colspan="6">총합</th>
    """
    for m in table_months:
        html += f'<th colspan="2">{m}</th>'
    html += "</tr><tr>"
    html += "<th>매출 비중</th><th>GP 비중</th><th>매출</th><th>평균 매출</th><th>트리즈 GP</th><th>평균 GP</th>"
    for m in table_months:
        html += "<th>매출</th><th>트리즈 GP</th>"
    html += "</tr></thead><tbody>"

    def _row_html(row, is_total=False):
        cls = ' class="grand-total-row"' if is_total else ""
        out = f"<tr{cls}>"
        out += f'<td class="info-cell">{row["비전속"]}</td>'
        out += f'<td class="info-cell">{row["다이렉트/벤더"]}</td>'
        out += f'<td class="info-cell">{row["셀러명"]}</td>'
        out += f'<td class="total-cell">{_fmt_pct(row["매출비중"])}</td>'
        out += f'<td class="total-cell">{_fmt_pct(row["GP비중"])}</td>'
        out += f'<td class="total-cell">{_fmt_money(row["매출"])}</td>'
        out += f'<td class="total-cell">{_fmt_money(row["평균매출"])}</td>'
        out += f'<td class="total-cell">{_fmt_money(row["GP"])}</td>'
        out += f'<td class="total-cell">{_fmt_money(row["평균GP"])}</td>'
        for m in table_months:
            out += f'<td>{_fmt_money(row.get(f"{m}_매출"))}</td>'
            out += f'<td>{_fmt_money(row.get(f"{m}_GP"))}</td>'
        out += "</tr>"
        return out

    html += _row_html(total_row, is_total=True)
    for row in rows:
        html += _row_html(row)

    html += "</tbody></table></div>"

    st.markdown(html, unsafe_allow_html=True)
