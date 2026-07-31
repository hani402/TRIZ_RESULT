"""업로드한 ALL데이터를 GitHub 저장소에 자동 커밋해서 영구 저장/복원하는 모듈.
Streamlit Cloud의 Secrets에 GITHUB_TOKEN, GITHUB_REPO가 설정되어 있어야 동작한다."""
import base64
import streamlit as st
import requests

GITHUB_API = "https://api.github.com"
DEFAULT_PATH = "data_cache/last_all_data.xlsx"


def _get_config():
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    path = st.secrets.get("GITHUB_DATA_PATH", DEFAULT_PATH)
    return token, repo, path


def is_configured() -> bool:
    token, repo, _ = _get_config()
    return bool(token and repo)


def fetch_all_data_bytes():
    """GitHub에 저장된 최신 ALL데이터 파일을 가져온다.
    반환: (bytes 또는 None, 에러메시지 또는 None)"""
    token, repo, path = _get_config()
    if not token or not repo:
        return None, "GITHUB_TOKEN/GITHUB_REPO가 설정되어 있지 않아요."
    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        return None, f"GitHub 요청 실패: {e}"
    if resp.status_code == 404:
        return None, f"GitHub에 저장된 파일이 없어요 (경로: {path})."
    if resp.status_code != 200:
        return None, f"GitHub 응답 오류 (status {resp.status_code}): {resp.text[:200]}"
    content = resp.json().get("content", "")
    try:
        return base64.b64decode(content), None
    except Exception as e:
        return None, f"파일 디코딩 실패: {e}"


def upload_all_data_bytes(file_bytes: bytes, commit_message: str = "Update ALL데이터"):
    """업로드한 파일을 GitHub 저장소에 커밋(생성 또는 갱신)한다. 409 충돌 시 sha를 재조회해 1회 재시도."""
    token, repo, path = _get_config()
    if not token or not repo:
        raise RuntimeError("GitHub 연동(GITHUB_TOKEN/GITHUB_REPO)이 설정되어 있지 않아요.")

    url = f"{GITHUB_API}/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def _current_sha():
        get_resp = requests.get(url, headers=headers, timeout=10)
        if get_resp.status_code == 200:
            return get_resp.json().get("sha")
        return None

    for attempt in range(2):
        sha = _current_sha()
        payload = {
            "message": commit_message,
            "content": base64.b64encode(file_bytes).decode("utf-8"),
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(url, headers=headers, json=payload, timeout=20)
        if put_resp.status_code == 409 and attempt == 0:
            continue  # sha가 그 사이 바뀐 경우, 재조회 후 한 번 더 시도
        put_resp.raise_for_status()
        return put_resp.json()
