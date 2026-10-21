"""수원대-zip — 메인 화면 (app.py가 불러온다). 실행: python3 -m streamlit run app.py
데이터는 `python3 recommend.py --export`가 만든 data/notices_parsed.csv를 읽고,
사람이 사진을 보고 입력한 값(data/notices_manual.csv, '사진 공지 검토' 화면)이 있으면 그 값을 우선한다.
화면: 왼쪽 사이드바(조건 입력) · 위쪽 '먼저 볼 공지' · 가운데 표(추천 결과) · 오른쪽 패널(상세 정보)"""
import datetime as dt
import html
import os
import pandas as pd
import streamlit as st

FIELDS = ["취업·진로", "어학·자격증", "국제교류", "봉사·대외활동", "장학·경제지원"]
OTHERS = ["학사·학습지원", "뉴스레터", "기타"]   # 기본으로는 숨기고, 사이드바에서 골라야 보인다
RECENT_DAYS = 60   # 마감일을 못 읽은 공지는 게시한 지 이만큼 이내인 것만 보여준다
MANUAL = "data/notices_manual.csv"
PERIODS = {"7일 안": 7, "30일 안": 30, "90일 안": 90, "지난 공지": None, "직접 선택": "custom"}

st.markdown("""<style>
:root{--blue:#2f4d78;--blue-soft:#e6edf6;--ink:#0b1626;--mute:#3c4d63;--line:#c3d0e0;--red:#b52a1c}
.dd{display:inline-block;border-radius:8px;padding:2px 10px;font-weight:800;font-size:1.05rem}
.dd.r1{background:#b52a1c;color:#fff}.dd.r2{background:#fbe1dd;color:#b52a1c}.dd.o{background:#fdebd6;color:#a85a12}
.dd.b{background:#d3e1f3;color:#274a78}.dd.g{background:#e9eff7;color:#4f6a8f}.dd.n{background:#eef2f7;color:var(--mute)}
.fd{display:inline-block;border-radius:6px;padding:1px 8px;font-size:.78rem;font-weight:700}
.fd.f1{background:#dbe6f4;color:#274a78}.fd.f2{background:#d9eef0;color:#1f6a72}.fd.f3{background:#e3e4f6;color:#43489a}
.fd.f4{background:#d9efe6;color:#25705a}.fd.f5{background:#f1e8d6;color:#7a5a24}.fd.f6{background:#e4e8ef;color:#4a566b}
.fd.f7{background:#ece6f3;color:#6a4d8c}.fd.f8{background:#eef2f7;color:#56667c}
[data-testid^="stBaseLinkButton"]{background:#a9c1e2!important;border:1.5px solid #7c9bc7!important}
[data-testid^="stBaseLinkButton"],[data-testid^="stBaseLinkButton"] *{color:#12294d!important;font-weight:700!important}
[data-testid^="stBaseLinkButton"]:hover{background:#97b3da!important}
.hint{font-size:.78rem;font-weight:600;color:var(--mute)}
.rt{font-size:1.02rem;font-weight:700;line-height:1.4;color:var(--ink);margin-bottom:.3rem;overflow-wrap:anywhere}
[class*="st-key-row_"]{border-bottom:1px solid var(--line);padding:.6rem .5rem;border-radius:10px}
[class*="st-key-row_"]:hover{background:#eef3fa}
[data-baseweb="tab"]{font-weight:700;font-size:1rem}
[data-testid="stBaseButton-pills"],[data-testid="stBaseButton-segmented_control"]{background:#fff;border:1.5px solid #9fb3cc;color:var(--ink);font-weight:600}
[data-testid="stBaseButton-pillsActive"],[data-testid="stBaseButton-segmented_controlActive"]{background:#142d52!important;border:1.5px solid #0e2240!important;box-shadow:0 2px 8px rgba(14,34,64,.55)}
[data-testid="stBaseButton-pillsActive"] *,[data-testid="stBaseButton-segmented_controlActive"] *{color:#fff!important;font-weight:800!important}
[data-testid="stRadio"] label:has(input:checked){background:#a9c1e2;border:1.5px solid #7c9bc7;border-radius:999px;padding:2px 12px}
[data-testid="stRadio"] label:has(input:checked) *{color:#12294d!important;font-weight:800!important}
.chip{font-size:.8rem;color:var(--mute)}
html,body,[data-testid="stAppViewContainer"]{color:var(--ink)}
.stApp p,.stApp li,.stApp label,.stApp span{font-weight:500}
h1,h2,h3,h4,h5{color:var(--ink);font-weight:800}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:var(--mute)!important;font-weight:500}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p{color:var(--ink);font-weight:600}
[data-testid="stSidebar"]{background:#eaf0f7;border-right:1px solid var(--line)}
[data-testid="stSidebar"] h3{margin-top:1.1rem;font-size:1rem;color:var(--blue)}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 14px}
[data-testid="stMetricValue"]{color:var(--blue)}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important}
.st-key-detail p,.st-key-detail li,.st-key-detail [data-testid="stCaptionContainer"]{font-size:.84rem;line-height:1.45;color:var(--ink)}
.st-key-detail h5{font-size:.98rem}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load(manual_mtime):
    d = pd.read_csv("data/notices_parsed.csv", encoding="utf-8-sig").fillna("")
    d["id"] = d.board + "-" + d.bbsno.astype(str)
    for c in ("date", "checked", "apply_start", "deadline"):
        d[c] = pd.to_datetime(d[c].replace("", None)).dt.date
    d["grade_set"] = d.grades.map(lambda g: None if g == "" else set() if g == "해당없음" else {int(x) for x in str(g).split(",")})
    d["reviewed"] = False
    if os.path.exists(MANUAL):   # 사진을 보고 직접 입력한 값이 자동 추출값보다 우선
        m = pd.read_csv(MANUAL, encoding="utf-8-sig", dtype=str).fillna("")
        for r in m.itertuples():
            i = d.index[d.id == f"{r.board}-{r.bbsno}"]
            if not len(i): continue
            i = i[0]; d.at[i, "reviewed"] = True
            if r.kind: d.at[i, "deadline_kind"] = r.kind
            d.at[i, "deadline"] = dt.date.fromisoformat(r.deadline) if r.kind == "마감" and r.deadline else None
            d.at[i, "apply_start"] = dt.date.fromisoformat(r.apply_start) if r.kind == "마감" and r.apply_start else None
            if r.grades and r.grades != "모름": d.at[i, "grade_set"] = {int(x) for x in r.grades.split(",")}
            if r.target: d.at[i, "target"] = r.target
            if r.method: d.at[i, "method"] = r.method
            if r.field: d.at[i, "분야"] = r.field
    d = d[d.분야.isin(FIELDS + OTHERS)].copy()
    try:   # fetch_images.py가 모은 공지 사진 주소(없으면 사진 기능만 꺼진다)
        im = pd.read_csv("data/notices_images.csv", encoding="utf-8-sig").fillna("")
        im = dict(zip(im.board + "-" + im.bbsno.astype(str), im.images.map(lambda x: [u for u in x.split("|") if u])))
    except FileNotFoundError:
        im = {}
    d["images"] = d.id.map(lambda i: im.get(i, []))
    return d.reset_index(drop=True)


def grade_text(g):
    return "확인 필요" if g is None else "재학생 아님" if not g else "전 학년" if len(g) == 4 else "·".join(map(str, sorted(g))) + "학년"


FIELD_CLS = {"취업·진로": "f1", "어학·자격증": "f2", "국제교류": "f3", "봉사·대외활동": "f4", "장학·경제지원": "f5",
             "학사·학습지원": "f6", "뉴스레터": "f7", "기타": "f8"}


def badge(field):
    return f"<span class='fd {FIELD_CLS.get(field, 'f8')}'>{field}</span>"


def dday(r, today):
    """(색 클래스, 'D-3' 같은 글자). 마감일이 없으면 회색."""
    if r.deadline_kind != "마감" or pd.isna(r.deadline): return "n", "상시" if r.deadline_kind == "상시" else "미확인"
    n = (r.deadline - today).days
    if n < 0: return "n", "마감됨"
    if n <= 1: return "r1", "오늘 마감" if n == 0 else "D-1"       # 가장 급함: 진한 빨강
    cls = "r2" if n <= 3 else "o" if n <= 7 else "b" if n <= 14 else "g"   # 3일 이내 빨강 · 7일 이내 주황 · 14일 이내 진한 파랑 · 그 외 옅은 파랑
    return cls, f"D-{n}"


def when_text(r, today):
    if r.deadline_kind != "마감" or pd.isna(r.deadline): return ("⚪ 상시" if r.deadline_kind == "상시" else "⚪ 미확인") + (" 📷" if r.images else "")
    n = (r.deadline - today).days
    if n < 0: return f"⚫ 마감 {r.deadline:%m/%d}"
    return f"{'🔴' if n <= 3 else '🟠' if n <= 7 else '🔵' if n <= 14 else '⚪'} {'오늘' if n == 0 else f'D-{n}'} · {r.deadline:%m/%d}"


def filter_rows(d, grade, fields, start, end, with_unknown):
    x = d[d.분야.isin(fields) & d.grade_set.map(lambda g: g is None or grade in g)]
    known = x[(x.deadline_kind == "마감") & x.deadline.notna() & (x.deadline >= start) & (x.deadline <= end)].sort_values(["deadline", "date"])
    unk = x[(x.deadline_kind != "마감") & (x.date >= start - dt.timedelta(days=RECENT_DAYS)) & (x.date <= end)].sort_values("date", ascending=False)
    return known, (unk if with_unknown else unk.iloc[0:0])


WD = "월화수목금토일"
MAX_ROWS = 50


def set_active(i):
    st.session_state.active = i


def rows_list(df, today, prefix, active):
    """공지를 한 줄씩: [D-day] [제목(굵게) + 분야·대상] [보기]. 선택된 공지는 배경을 칠한다."""
    for n, r in enumerate(df.head(MAX_ROWS).itertuples()):
        key = f"row_{prefix}{n}"
        with st.container(key=key):
            if r.id == active: st.markdown(f"<style>.st-key-{key}{{background:#dbe6f4;box-shadow:inset 4px 0 0 var(--blue)}}</style>", unsafe_allow_html=True)
            a, b, c = st.columns([1.35, 6, 1.1], vertical_alignment="center")
            cls, txt = dday(r, today)
            sub = f"{r.deadline:%m/%d}({WD[r.deadline.weekday()]})" if r.deadline_kind == "마감" and pd.notna(r.deadline) else ("📷 사진 공지" if r.images else "")
            a.markdown(f"<span class='dd {cls}'>{txt}</span><div class='chip'>{sub}</div>", unsafe_allow_html=True)
            g = "대상 미확인" if r.grade_set is None else f"대상 {grade_text(r.grade_set)}"
            b.markdown(f"<div class='rt'>{html.escape(r.title)}</div><div>{badge(r.분야)} <span class='chip'>{g}</span>"
                       + (" <span class='chip'>📷 사진 공지</span>" if r.images and sub != "📷 사진 공지" else "") + "</div>", unsafe_allow_html=True)
            c.button("보기", key=f"btn_{prefix}{n}", on_click=set_active, args=(r.id,), width="stretch", type="primary" if r.id == active else "secondary")
    if len(df) > MAX_ROWS: st.caption(f"위쪽 {MAX_ROWS}건만 보여드려요. 기간이나 분야를 좁히면 나머지를 볼 수 있어요.")


def detail(r, today):
    st.markdown(f"##### {r.title}")
    st.markdown(badge(r.분야) + (" <span class='fd f8'>AI 분류</span>" if r.predicted else "") + (" <span class='fd f2'>직접 확인</span>" if r.reviewed else "")
                + f" <span class='chip'>{r.dept or r.board} · {r.date} 게시</span>", unsafe_allow_html=True)
    if r.deadline_kind == "마감" and pd.notna(r.deadline):
        cls, txt = dday(r, today)
        period = (f"{r.apply_start:%Y.%m.%d} ~ " if pd.notna(r.apply_start) else "~ ") + f"{r.deadline:%Y.%m.%d}"
        period += f"  <span class='dd {cls}'>{txt}</span>"
    else:
        period = "상시·선착순 모집" if r.deadline_kind == "상시" else "본문에서 읽지 못했어요"
    miss = "공고문에서 읽지 못했어요"
    rows = [("신청 기간", period), ("대상 학년", grade_text(r.grade_set) if r.grade_set is not None else miss),
            ("신청 대상", r.target or miss), ("신청 방법", r.method or miss), ("정보 확인일", str(r.checked))]
    for k, v in rows:
        st.markdown(f"**{k}**  \n{v}" + (f" — [공식 공지에서 확인]({r.url})" if v == miss or v.startswith("본문에서") else ""), unsafe_allow_html=True)
    if r.images:   # 본문이 사진으로 올라온 공지: 마감일 등을 못 읽었으면 사진을 바로 펼쳐 보여준다
        with st.expander(f"📷 공지 사진 보기 ({len(r.images)}장)", expanded=r.deadline_kind != "마감"):
            for u in r.images: st.image(u, width="stretch")
    st.link_button("공식 공지 열기 ↗", r.url, type="primary", width="stretch")
    st.caption("자동으로 읽은 정보라 틀릴 수 있어요. 신청 가능 여부는 공식 공지에서 최종 확인하세요.")


# --- 조건 입력 (사이드바) -----------------------------------------------------
data = load(os.path.getmtime(MANUAL) if os.path.exists(MANUAL) else 0)
collected = data.checked.max()
today = dt.date.today()

with st.sidebar:
    st.header("내 조건")
    st.markdown("### ① 학년")
    grade = st.segmented_control("학년", [1, 2, 3, 4], default=2, format_func=lambda v: f"{v}학년", label_visibility="collapsed") or 2
    st.markdown("### ② 관심 분야 <span class='hint'>· 중복 선택 가능</span>", unsafe_allow_html=True)
    fields = st.pills("관심 분야", FIELDS, selection_mode="multi", default=["장학·경제지원", "취업·진로"], label_visibility="collapsed")
    st.caption("학교 생활·소식도 보고 싶다면 (중복 선택 가능)")
    others = st.pills("그 밖의 공지", OTHERS, selection_mode="multi", default=[], label_visibility="collapsed")
    fields = list(fields or []) + list(others or [])
    st.markdown("### ③ 언제까지 마감?")
    period = st.radio("기간", list(PERIODS), index=1, horizontal=True, label_visibility="collapsed")
    if PERIODS[period] == "custom":
        rng = st.date_input("마감 기간", value=(today, today + dt.timedelta(days=30)), format="YYYY.MM.DD", label_visibility="collapsed")
    elif PERIODS[period] is None:
        rng = (today - dt.timedelta(days=90), today - dt.timedelta(days=1))
    else:
        rng = (today, today + dt.timedelta(days=PERIODS[period]))
    st.caption("오늘부터 그 기간 안에 신청이 끝나는 공지를 보여줘요." if PERIODS[period] not in (None, "custom") else "고른 기간 안에 신청이 끝나는 공지를 보여줘요.")
    unknown = st.checkbox("마감일을 모르는 공지도 같이 보기", value=True)
    st.caption(f"공지 수집일 {collected} · 오늘 {today}")

st.title("수원대-zip")
if not fields: st.info("왼쪽 ② 에서 관심 분야를 하나 이상 골라 주세요."); st.stop()
if len(rng) != 2: st.info("마감 기간의 종료일까지 골라 주세요."); st.stop()
start, end = rng
known, unk = filter_rows(data, grade, fields, start, end, unknown)
ss = st.session_state

days_left = known.deadline.map(lambda x: (x - today).days)
soon = int(((days_left >= 0) & (days_left <= 7)).sum())   # 이미 마감된 공지는 세지 않는다
c1, c2, c3 = st.columns(3)
c1.metric("마감일 확인된 공지", f"{len(known)}건"); c2.metric("7일 안에 마감", f"{soon}건"); c3.metric("마감일 모르는 공지", f"{len(unk)}건")

if known.empty and unk.empty:
    st.warning("조건에 맞는 공지가 없어요. 기간을 넓히거나 분야를 더 선택해 보세요." + (f" (공지 수집일이 {collected}라서 그 이후 공지는 없어요.)" if start > collected else ""))
    st.stop()

# --- 먼저 볼 공지: 아직 안 끝난 공지 중 마감이 가장 가까운 3건 ----------------------------
all_rows = pd.concat([known, unk])
if ss.get("active") not in set(all_rows.id): ss.active = all_rows.iloc[0].id
top = known[known.deadline >= today].head(3)
if len(top):
    st.subheader("🔥 먼저 볼 공지")
    st.caption("마감이 가까운 순서예요.")
    for col, r in zip(st.columns(3), top.itertuples()):
        with col.container(border=True):
            cls, txt = dday(r, today)
            st.markdown(f"<span class='dd {cls}'>{txt}</span> <span class='chip'>{r.deadline:%m/%d}({WD[r.deadline.weekday()]}) 마감</span> {badge(r.분야)}", unsafe_allow_html=True)
            st.markdown(f"<div class='rt'>{html.escape(r.title if len(r.title) <= 42 else r.title[:41] + '…')}</div>", unsafe_allow_html=True)
            st.button("자세히 보기", key=f"top{r.id}", on_click=set_active, args=(r.id,), width="stretch")

# --- 전체 목록 + 상세 --------------------------------------------------------------
st.subheader("전체 목록")
st.caption(f"{grade}학년 · {', '.join(fields)} · 마감 {start:%Y.%m.%d} ~ {end:%Y.%m.%d}   |   🔴 3일 이내  🟠 7일 이내  🔵 14일 이내  ⚪ 그 외·마감일 모름")
left, right = st.columns([7, 3], gap="medium")
with left:
    tab_k, tab_u = st.tabs([f"마감일 확인 ({len(known)})", f"마감일 모름 ({len(unk)})"])
    with tab_k:
        if len(known): rows_list(known, today, "k", ss.active)
        else: st.caption("이 기간에 마감되는 공지가 없어요.")
    with tab_u:
        if len(unk):
            st.caption("신청 기간을 알 수 없는 공지예요. 📷는 공지가 사진이라, 오른쪽 상세에서 사진을 볼 수 있어요.")
            rows_list(unk, today, "u", ss.active)
        else: st.caption("해당 공지가 없어요.")
with right:
    with st.container(border=True, key="detail"):
        st.caption("공지의 ‘보기’ 버튼을 누르면 상세 정보가 바뀌어요.")
        detail(all_rows[all_rows.id == ss.active].iloc[0], today)

st.divider()
st.caption("분야는 직접 검수한 결과와 AI(TF-IDF + 로지스틱 회귀, 교차검증 정확도 약 85%) 예측을 함께 씁니다. 마감일·대상·신청 방법은 본문에서 자동으로 읽은 값이라 비어 있거나 틀릴 수 있어요.")
