import streamlit as st

from views import home, sales_kpi, manager_kpi

st.set_page_config(page_title="영업실 결산 대시보드", page_icon="📈", layout="wide")

MENU = {
      "🏠 홈": home,
      "📊 영업 지표": sales_kpi,
      "🧑‍💼 매니저별 진척관리": manager_kpi,
}

st.sidebar.title("메뉴")
choice = st.sidebar.radio("이동", list(MENU.keys()), label_visibility="collapsed")

MENU[choice].render()
