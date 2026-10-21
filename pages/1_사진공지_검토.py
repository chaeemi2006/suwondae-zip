"""사진으로만 올라온 공지를 사람이 보고 마감일·대상·신청 방법을 입력하는 화면. 저장하면 data/notices_manual.csv에 쌓이고 메인 앱에 바로 반영된다."""
import csv, datetime as dt, os
import pandas as pd
import streamlit as st

FIELDS = ["취업·진로", "어학·자격증", "국제교류", "봉사·대외활동", "장학·경제지원"]
OTHER = ["학사·학습지원", "뉴스레터", "기타"]
MANUAL = "data/notices_manual.csv"
COLS = ["board", "bbsno", "kind", "apply_start", "deadline", "grades", "target", "method", "field", "reviewed_at"]
KINDS = {"마감": "마감일이 사진에 있어요", "상시": "상시·선착순 모집이에요", "없음": "사진에도 마감일이 없어요"}



def read_manual():
    return pd.read_csv(MANUAL, encoding="utf-8-sig", dtype=str).fillna("") if os.path.exists(MANUAL) else pd.DataFrame(columns=COLS)


def save_row(row):
    m = read_manual()
    m = m[~((m.board == row["board"]) & (m.bbsno == row["bbsno"]))]
    m = pd.concat([m, pd.DataFrame([row])], ignore_index=True)[COLS]
    m.to_csv(MANUAL, index=False, encoding="utf-8-sig")


def d_or_none(v):
    try: return dt.date.fromisoformat(v) if v else None
    except ValueError: return None


parsed = pd.read_csv("data/notices_parsed.csv", encoding="utf-8-sig", dtype=str).fillna("")
img = pd.read_csv("data/notices_images.csv", encoding="utf-8-sig", dtype=str).fillna("")
items = img[img.images != ""].merge(parsed, on=["board", "bbsno"])
items["id"] = items.board + "-" + items.bbsno
manual = read_manual(); done = set(manual.board + "-" + manual.bbsno)
items["shown"] = items.분야.isin(FIELDS)

st.title("사진 공지 검토")
st.caption("공지가 사진으로만 올라와서 마감일을 자동으로 읽지 못한 공지예요. 사진을 보고 아래 칸을 채운 뒤 저장하면 메인 앱에 바로 반영돼요.")
n_show = int(items.shown.sum()); n_done = int((items.id.isin(done) & items.shown).sum())
st.progress(n_done / max(n_show, 1), text=f"앱에 나오는 공지 {n_done} / {n_show}건 검토 완료")
c1, c2 = st.columns(2)
only_shown = c1.checkbox("앱에 나오는 5개 분야만 보기", value=True, help="학사·학습지원, 뉴스레터, 기타는 앱에 안 나와서 검토하지 않아도 돼요.")
only_todo = c2.checkbox("아직 안 한 공지만 보기", value=True)

view = items[items.shown] if only_shown else items
if only_todo: view = view[~view.id.isin(done)]
view = view.sort_values(["shown", "분야", "date"], ascending=[False, True, False])
if view.empty: st.success("검토할 공지가 없어요. 수고하셨어요!"); st.stop()

labels = {r.id: f"{'✅' if r.id in done else '⬜'} [{r.분야}] {r.title[:50]}" for r in view.itertuples()}
ids = list(labels)
if "rv_next" in st.session_state: st.session_state.rv_sel = st.session_state.pop("rv_next")   # 저장 직후 다음 공지로
if st.session_state.get("rv_sel") not in ids: st.session_state.rv_sel = ids[0]
sel = st.selectbox("공지 고르기", ids, format_func=labels.get, key="rv_sel")
r = view[view.id == sel].iloc[0]
old = manual[(manual.board == r.board) & (manual.bbsno == r.bbsno)]
old = old.iloc[0] if len(old) else None

left, right = st.columns([3, 2], gap="large")
with left:
    st.markdown(f"##### {r.title}")
    st.caption(f"{r.dept or r.board} · {r.date} 게시 · [공식 공지 열기 ↗]({r.url})")
    for u in r.images.split("|"): st.image(u, width="stretch")
with right:
    with st.form(f"f-{sel}"):
        kind = st.radio("마감", list(KINDS), format_func=KINDS.get, index=list(KINDS).index(old.kind) if old is not None and old.kind in KINDS else 0)
        a, b = st.columns(2)
        start = a.date_input("신청 시작일 (선택)", value=d_or_none(old.apply_start) if old is not None else None, format="YYYY.MM.DD")
        end = b.date_input("마감일", value=d_or_none(old.deadline) if old is not None else None, format="YYYY.MM.DD")
        g_old = [int(x) for x in old.grades.split(",")] if old is not None and old.grades not in ("", "모름") else []
        gmode = st.radio("대상 학년", ["사진에서 모르겠어요", "전 학년", "학년 선택"], horizontal=True,
                         index=0 if old is None or old.grades in ("", "모름") else 1 if len(g_old) == 4 else 2)
        gsel = st.multiselect("학년 선택일 때만", [1, 2, 3, 4], default=g_old if gmode == "학년 선택" else [], format_func=lambda v: f"{v}학년")
        target = st.text_input("신청 대상 (선택)", value=old.target if old is not None else "", placeholder="예: 직전 학기 12학점 이상 이수한 재학생")
        method = st.text_input("신청 방법 (선택)", value=old.method if old is not None else "", placeholder="예: 학생지원팀 방문 접수")
        cur = old.field if old is not None and old.field else r.분야
        field = st.selectbox("분야 (잘못됐으면 고쳐 주세요)", FIELDS + OTHER, index=(FIELDS + OTHER).index(cur) if cur in FIELDS + OTHER else 0)
        ok = st.form_submit_button("저장", type="primary", width="stretch")
    if ok:
        if kind == "마감" and end is None: st.error("마감일을 골라 주세요. 사진에도 없으면 ‘사진에도 마감일이 없어요’를 선택하세요.")
        elif gmode == "학년 선택" and not gsel: st.error("학년을 하나 이상 골라 주세요.")
        else:
            grades = "모름" if gmode.startswith("사진") else "1,2,3,4" if gmode == "전 학년" else ",".join(map(str, sorted(gsel)))
            save_row(dict(board=r.board, bbsno=r.bbsno, kind=kind, apply_start=start.isoformat() if start and kind == "마감" else "",
                          deadline=end.isoformat() if end and kind == "마감" else "", grades=grades, target=target.strip(), method=method.strip(),
                          field=field if field != r.분야 else "", reviewed_at=dt.date.today().isoformat()))
            nxt = [i for i in ids if i != sel and i not in done]
            st.session_state.rv_next = nxt[0] if nxt else sel
            st.rerun()
    st.caption("저장하면 다음 공지로 넘어가요. 이미 한 공지는 다시 열어 고칠 수 있어요.")
