import os
import io
import hashlib
import streamlit as st

from data_utils import load_all_data
from views import sales_kpi, manager_kpi, transaction, seller, product
import github_sync

st.set_page_config(page_title="영업실 결산 대시보드", page_icon="📈", layout="wide")

CACHE_DIR = "data_cache"
CACHE_PATH = os.path.join(CACHE_DIR, "last_all_data.xlsx")

st.sidebar.title("메뉴")

# ---- 데이터 업로드 (한 번만, 모든 화면이 공유) ----
uploaded = st.sidebar.file_uploader("ALL데이터 엑셀 업로드 (.xlsx)", type=["xlsx"])
if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    # 이미 처리한 파일과 동일하면(재실행으로 인한 중복) 건너뜀
    if st.session_state.get("last_synced_hash") != file_hash:
        try:
            # 로컬 캐시에도 저장 (같은 세션/새로고침 대비)
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CACHE_PATH, "wb") as f:
                f.write(file_bytes)

            st.session_state["df"] = load_all_data(io.BytesIO(file_bytes))
            st.session_state["df_filename"] = uploaded.name

            # GitHub에 영구 저장 (설정되어 있는 경우)
            if github_sync.is_configured():
                try:
                    github_sync.upload_all_data_bytes(file_bytes, commit_message=f"Update ALL데이터 ({uploaded.name})")
                    st.sidebar.success("GitHub에 영구 저장했어요. 재부팅해도 유지돼요.")
                except Exception as e:
                    st.sidebar.warning(f"GitHub 저장 중 문제가 있었어요: {e}")

            st.session_state["last_synced_hash"] = file_hash
        except ValueError as e:
            st.sidebar.error(str(e))

# ---- 세션에 없으면, 저장된 데이터를 자동으로 복원 ----
if "df" not in st.session_state:
    if os.path.exists(CACHE_PATH):
        try:
            st.session_state["df"] = load_all_data(CACHE_PATH)
            st.session_state.setdefault("df_filename", "(이전에 업로드된 파일)")
        except Exception:
            pass
    elif github_sync.is_configured():
        cached_bytes = github_sync.fetch_all_data_bytes()
        if cached_bytes:
            try:
                st.session_state["df"] = load_all_data(io.BytesIO(cached_bytes))
                st.session_state.setdefault("df_filename", "(GitHub에 저장된 최신 파일)")
            except Exception:
                pass

df = st.session_state.get("df")
if df is not None:
    st.sidebar.success(f"'{st.session_state.get('df_filename', '')}' 불러옴 ({len(df):,}건)")
else:
    st.sidebar.info("엑셀 파일을 업로드하면 모든 화면에 반영돼요.")

st.sidebar.divider()

MENU = {
    "📊 영업 지표": sales_kpi,
    "🧑‍💼 매니저별": manager_kpi,
    "📑 거래별": transaction,
    "🙋 셀러별": seller,
    "🏷️ 상품별": product,
}

choice = st.sidebar.radio("이동", list(MENU.keys()), label_visibility="collapsed")

MENU[choice].render(df)
