import streamlit as st

st.set_page_config(page_title="영업실 결산 대시보드", page_icon="📈", layout="wide")

home_page = st.Page("home.py", title="홈", icon="🏠", default=True)
sales_kpi_page = st.Page("pages/1_sales_kpi.py", title="영업 지표", icon="📊")

pg = st.navigation([home_page, sales_kpi_page])
pg.run()
