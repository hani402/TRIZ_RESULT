import streamlit as st

from data_utils import load_all_data
from views import home, sales_kpi, manager_kpi

st.set_page_config(page_title="영업실 결산 대시보드", page_icon="📈", layout="wide")

st.sidebar.title("메뉴")

# ---- 데이터 업로드 (한 번만, 모든 화면이 공유) ----
uploaded = st.sidebar.file_uploader("ALL데이터 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded is not None:
    try:
        st.session_state["df"] = load_all_data(uploaded)
        st.session_state["df_filename"] = uploaded.name
    except ValueError as e:
        st.sidebar.error(str(e))

df = st.session_state.get("df")
if df is not None:
    st.sidebar.success(f"'{st.session_state.get('df_filename', '')}' 불러옴 ({len(df):,}건)")
else:
    st.sidebar.info("엑셀 파일을 업로드하면 모든 화면에 반영돼요.")

st.sidebar.divider()

MENU = {
    "🏠 홈": home,
    "📊 영업 지표": sales_kpi,
    "🧑‍💼 매니저별 진척관리": manager_kpi,
}

choice = st.sidebar.radio("이동", list(MENU.keys()), label_visibility="collapsed")

MENU[choice].render(df)
