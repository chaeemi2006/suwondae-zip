"""수원대-zip (Streamlit). 실행: python3 -m streamlit run app.py
화면 이동(메뉴)을 여기서 직접 정의한다 — 서버를 다시 켜지 않아도 새 화면이 메뉴에 나타난다.
  수원대-zip = home.py (학생이 보는 화면)
  사진 공지 검토 = pages/1_사진공지_검토.py (사진을 보고 마감일 등을 직접 입력) — 운영자 전용:
      .streamlit/secrets.toml의 review_key를 주소에 ?admin=키 로 붙여 들어온 사람에게만 메뉴가 보인다."""
import hmac
import streamlit as st

st.set_page_config(page_title="수원대-zip", page_icon="📌", layout="wide")


def is_admin():
    try: key = st.secrets.get("review_key", "")
    except Exception: key = ""          # secrets.toml이 없으면 아무도 운영자가 아니다
    if not key: return False
    if hmac.compare_digest(str(st.query_params.get("admin", "")).encode(), str(key).encode()): st.session_state.is_admin = True   # 화면을 옮겨도 유지
    return bool(st.session_state.get("is_admin"))


pages = [st.Page("home.py", title="수원대-zip", icon="📌", default=True)]
if is_admin():
    pages.append(st.Page("pages/1_사진공지_검토.py", title="사진 공지 검토", icon="📝", url_path="review"))
st.navigation(pages, position="sidebar" if len(pages) > 1 else "hidden").run()
