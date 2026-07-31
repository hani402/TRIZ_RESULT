import streamlit as st


def render(df):
    st.title("📈 영업실 결산 대시보드")
    st.caption("왼쪽 사이드바에 ALL데이터 엑셀을 업로드하면, 모든 메뉴가 자동으로 계산됩니다.")
    st.info("이 사이트는 결산/내부 자료용입니다. 링크를 공유받은 인원만 접속해주세요.", icon="🔒")

    if df is None:
        st.warning("아직 데이터가 없어요. 왼쪽 사이드바에서 엑셀 파일을 업로드해주세요.")
    else:
        st.success(f"현재 {len(df):,}건의 데이터가 불러와져 있어요. 왼쪽 메뉴에서 원하는 뷰를 선택하세요.")

    st.divider()
    st.subheader("📊 영업 지표")
    st.write("월별 진행 건수 · 매출 결과 · GP 결과를 자동으로 집계해서 보여드려요.")

    st.divider()
    st.subheader("🧑‍💼 매니저별 진척관리")
    st.write("담당자별 매출/GP 실적과 KPI 달성률을 확인해요.")

    st.divider()
    st.subheader("📑 영업 거래별")
    st.write("다이렉트/벤더/PA/기타 구분별로 진행 횟수·매출·GP 결과를 확인해요.")

    st.divider()
    st.caption("다음 순서로 셀러별/셀러상품별 · 상품별 뷰가 추가될 예정입니다.")
