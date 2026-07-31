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


EXCLUDE_MANAGERS = {"봉석"}  # 오기입 등으로 제외해야 하는 담당자


def get_managers(df: pd.DataFrame) -> list:
    """ALL데이터의 '비고1'(담당자) 컬럼에서 담당자 목록 추출 (제외 대상 필터링)."""
    vals = df["비고1"].dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    vals = vals[~vals.isin(EXCLUDE_MANAGERS)]
    return sorted(vals.unique().tolist())


def get_active_months(df: pd.DataFrame) -> list:
    """실제 결산 데이터가 존재하는 월만 순서대로 반환."""
    present = set(df["월"].dropna().astype(str).str.strip().unique())
    return [m for m in MONTH_ORDER if m in present]


def build_manager_actuals(df: pd.DataFrame, managers: list) -> pd.DataFrame:
    """담당자별 월별 매출 결과 / GP 결과. index=(담당자, 지표), columns=월"""
    rows = []
    for manager in managers:
        sub_m = df[df["비고1"].astype(str).str.strip() == manager]
        rev_row = {"담당자": manager, "지표": "매출 결과"}
        gp_row = {"담당자": manager, "지표": "GP 결과"}
        for month in MONTH_ORDER:
            sub = sub_m[sub_m["월"] == month]
            rev_row[month] = sub["매출"].sum()
            gp_row[month] = sub["트리즈GP"].sum()
        rows.append(rev_row)
        rows.append(gp_row)
    result = pd.DataFrame(rows).set_index(["담당자", "지표"])
    result.insert(0, "합계", result[MONTH_ORDER].sum(axis=1))
    return result


MANAGER_KPI_PATH = "data/kpi_manager_targets.xlsx"


def load_manager_kpi_targets(path: str = MANAGER_KPI_PATH) -> dict:
    """담당자별 고정 KPI 백데이터 파일을 로드.
    형식: 담당자(병합)/구분(매출 KPI, GP KPI)/합계/1월..12월, '부서 총합' 행 포함.
    0은 '해당 기간 KPI 미설정'으로 보고 빈 값(NaN) 처리 (합계 열은 제외).
    반환: {담당자: {"매출 KPI": {"합계":.., "1월":.., ...}, "GP KPI": {...}}}
    """
    import os
    import numpy as np

    if not os.path.exists(path):
        return {}

    try:
        raw = pd.read_excel(path, header=None)
    except Exception:
        return {}

    header_row = None
    for r in range(min(10, len(raw))):
        if (raw.iloc[r] == "담당자").any():
            header_row = r
            break
    if header_row is None:
        return {}

    header = raw.iloc[header_row]
    col_map = {}
    for c in raw.columns:
        v = header[c]
        if isinstance(v, str) and v.strip():
            col_map[c] = v.strip()

    df = raw.iloc[header_row + 1:].copy()
    df = df.rename(columns=col_map)
    keep_cols = ["담당자", "구분", "합계"] + MONTH_ORDER
    df = df[[c for c in keep_cols if c in df.columns]]
    df["담당자"] = df["담당자"].ffill()
    df = df[df["구분"].notna()]

    result = {}
    for manager, group in df.groupby("담당자", sort=False):
        manager_data = {}
        for _, row in group.iterrows():
            metric = row["구분"]
            values = {}
            for col in ["합계"] + MONTH_ORDER:
                v = row.get(col)
                if col != "합계" and (v == 0 or pd.isna(v)):
                    v = np.nan
                values[col] = v
            manager_data[metric] = values
        result[manager] = manager_data

    return result
