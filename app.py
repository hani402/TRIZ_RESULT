import streamlit as st

st.set_page_config(page_title="영업실 결산 대시보드", page_icon="📈", layout="wide")

st.title("📈 영업실 결산 대시보드")
st.caption("ALL데이터만 업로드하면 나머지 뷰는 자동으로 계산됩니다. 왼쪽 사이드바에서 원하는 뷰를 선택하세요.")
st.info("이 사이트는 결산/내부 자료용입니다. 링크를 공유받은 인원만 접속해주세요.", icon="🔒")

st.divider()

st.subheader("📊 영업 지표")
st.write("월별 진행 건수 · 매출 결과 · GP 결과를 자동으로 집계해서 보여드려요.")
st.page_link("pages/1_📊_영업_지표.py", label="바로가기 →", icon="📊")

st.divider()
st.caption("다음 순서로 매니저별 · 셀러별/셀러상품별 · 상품별 뷰가 추가될 예정입니다.")
