import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data_utils import load_all_data, build_sales_kpi, MONTH_ORDER

st.title("📊 영업 지표 (월별 전체 실적)")
st.caption("'ALL데이터' 시트가 포함된 엑셀 파일을 업로드하면 자동으로 집계됩니다.")

uploaded = st.file_uploader("ALL데이터 엑셀 업로드 (.xlsx)", type=["xlsx"])

if uploaded is None:
    st.info("파일을 업로드하면 결과가 표시됩니다.")
    st.stop()

try:
    df = load_all_data(uploaded)
except ValueError as e:
    st.error(str(e))
    st.stop()

st.success(f"총 {len(df):,}건의 데이터를 불러왔어요. (데이터가 있는 월: {', '.join(sorted(set(df['월']), key=MONTH_ORDER.index))})")

kpi = build_sales_kpi(df)

# ---- 표 ----
st.subheader("월별 집계표")
display = kpi.copy()
for col in display.columns:
    display[col] = display.apply(
        lambda row: f"{int(row[col]):,}" if row.name == "진행 건수" else f"{int(row[col]):,}원",
        axis=1,
    )

table_html = """
<style>
.kpi-table { border-collapse: collapse; width: 100%; font-size: 14px; }
.kpi-table th, .kpi-table td {
    text-align: center !important;
    padding: 10px 12px;
    border: 1px solid #d9dce3;
    color: #1f2937 !important;
}
.kpi-table thead th {
    background-color: #1f2a44 !important;
    color: #ffffff !important;
    font-weight: 600;
}
.kpi-table tbody th {
    background-color: #f3f4f8 !important;
    color: #1f2937 !important;
    font-weight: 600;
    text-align: center !important;
}
.kpi-table tbody tr:nth-child(even) td:not(.all-col) { background-color: #fafafc !important; }
.kpi-table tbody tr:nth-child(odd) td:not(.all-col) { background-color: #ffffff !important; }
.kpi-table td.all-col {
    background-color: #eef1fb !important;
    color: #1f2937 !important;
    font-weight: 700;
}
</style>
<table class="kpi-table">
<thead><tr><th>구분</th>"""
for col in display.columns:
    table_html += f"<th>{col}</th>"
table_html += "</tr></thead><tbody>"
for idx, row in display.iterrows():
    table_html += f"<tr><th>{idx}</th>"
    for col in display.columns:
        cls = ' class="all-col"' if col == "ALL" else ""
        table_html += f"<td{cls}>{row[col]}</td>"
    table_html += "</tr>"
table_html += "</tbody></table>"

st.markdown(table_html, unsafe_allow_html=True)

# ---- 차트 ----
st.subheader("월별 추이")
months = MONTH_ORDER

from plotly.subplots import make_subplots

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_bar(
    x=months, y=[kpi.loc["매출 결과", m] for m in months],
    name="매출 결과", secondary_y=False,
)
fig.add_bar(
    x=months, y=[kpi.loc["GP 결과", m] for m in months],
    name="GP 결과", secondary_y=False,
)
fig.add_scatter(
    x=months, y=[kpi.loc["진행 건수", m] for m in months],
    name="진행 건수", mode="lines+markers", secondary_y=True,
    line=dict(width=3),
)
fig.update_layout(title="매출 · GP · 진행 건수", barmode="group", height=460)
fig.update_yaxes(title_text="금액 (원)", secondary_y=False)
fig.update_yaxes(title_text="진행 건수", secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

# ---- 다운로드 ----
st.subheader("엑셀로 다운로드")
import io
buf = io.BytesIO()
kpi.to_excel(buf, sheet_name="영업 지표")
st.download_button(
    "영업 지표.xlsx 다운로드",
    data=buf.getvalue(),
    file_name="영업_지표.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
