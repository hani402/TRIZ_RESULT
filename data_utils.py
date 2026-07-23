import pandas as pd
import streamlit as st

MONTH_ORDER = [f"{i}월" for i in range(1, 13)]
QUARTER_MAP = {
    "1월": "1Q", "2월": "1Q", "3월": "1Q",
    "4월": "2Q", "5월": "2Q", "6월": "2Q",
    "7월": "3Q", "8월": "3Q", "9월": "3Q",
    "10월": "4Q", "11월": "4Q", "12월": "4Q",
}
# "진행 건수"에서 제외되는 다이렉트/벤더 구분값 (기존 엑셀 수식 기준)
EXCLUDE_FROM_COUNT = {"기타", "PA"}

REQUIRED_COLS = [
    "월", "비전속", "다이렉트/벤더", "셀러명", "매출", "매입",
    "셀러RS", "내부정산", "트리즈GP", "비고1", "PB/NB", "카테고리", "진행상품", "수량",
]


@st.cache_data(show_spinner=False)
def load_all_data(file) -> pd.DataFrame:
    """업로드된 엑셀에서 'ALL 데이터' 시트를 찾아 표준 데이터프레임으로 변환."""
    xls = pd.ExcelFile(file)
    sheet_name = None
    for name in xls.sheet_names:
        if "ALL" in name.upper().replace(" ", ""):
            sheet_name = name
            break
    if sheet_name is None:
        raise ValueError("'ALL 데이터' 시트를 찾지 못했습니다. 시트명을 확인해주세요.")

    raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    # '월' 이라는 헤더가 있는 행을 자동으로 탐색
    header_row = None
    for r in range(min(15, len(raw))):
        if (raw.iloc[r] == "월").any():
            header_row = r
            break
    if header_row is None:
        raise ValueError("헤더 행('월' 컬럼)을 찾지 못했습니다.")

    header = raw.iloc[header_row]
    col_map = {}
    for c in raw.columns:
        val = header[c]
        if isinstance(val, str) and val.strip():
            col_map[c] = val.strip()

    df = raw.iloc[header_row + 1:].copy()
    df = df.rename(columns=col_map)
    df = df[[c for c in REQUIRED_COLS if c in df.columns]]

    # 월이 비어있는(=데이터 끝난 이후) 행 제거
    df = df[df["월"].notna()].reset_index(drop=True)

    # 숫자 컬럼 정리
    for col in ["매출", "매입", "셀러RS", "내부정산", "트리즈GP", "수량"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["월"] = df["월"].astype(str).str.strip()
    df = df[df["월"].isin(MONTH_ORDER)].reset_index(drop=True)
    df["분기"] = df["월"].map(QUARTER_MAP)

    return df


def build_sales_kpi(df: pd.DataFrame) -> pd.DataFrame:
    """영업 지표: 월별 진행건수 / 매출 결과 / GP 결과."""
    rows = []
    for month in MONTH_ORDER:
        sub = df[df["월"] == month]
        count_sub = sub[~sub["다이렉트/벤더"].isin(EXCLUDE_FROM_COUNT)]
        rows.append({
            "월": month,
            "진행 건수": len(count_sub),
            "매출 결과": sub["매출"].sum(),
            "GP 결과": sub["트리즈GP"].sum(),
        })
    monthly = pd.DataFrame(rows).set_index("월")

    result = monthly.T
    result.insert(0, "ALL", result.sum(axis=1))
    return result
