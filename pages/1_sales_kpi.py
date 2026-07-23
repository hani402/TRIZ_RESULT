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
st.dataframe(display, use_container_width=True)

# ---- 차트 ----
st.subheader("월별 추이")
months = MONTH_ORDER
col1, col2 = st.columns(2)

with col1:
    fig1 = go.Figure()
    fig1.add_bar(x=months, y=[kpi.loc["매출 결과", m] for m in months], name="매출 결과")
    fig1.add_bar(x=months, y=[kpi.loc["GP 결과", m] for m in months], name="GP 결과")
    fig1.update_layout(title="매출 / GP 결과", barmode="group", height=380)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = go.Figure()
    fig2.add_bar(x=months, y=[kpi.loc["진행 건수", m] for m in months], name="진행 건수")
    fig2.update_layout(title="진행 건수", height=380)
    st.plotly_chart(fig2, use_container_width=True)

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
