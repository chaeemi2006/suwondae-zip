"""관심 분야·기준일로 공지를 추천한다.
사용: python recommend.py 장학·경제지원,취업·진로 [기준일 YYYY-MM-DD] [--grade 2] [--all]
      python recommend.py --export   (화면용 data/notices_parsed.csv 생성)
- 분야: 검수한 label이 있으면 그것을, 없는 새 공지는 TF-IDF+로지스틱 회귀 예측값을 쓴다.
- --grade N: 본문에서 대상 학년을 읽을 수 있는 공지 중 N학년이 아닌 것은 제외한다(학년을 모르는 공지는 '대상 확인 필요'로 남긴다).
- 마감 전 공지만(기본), 마감 임박순. 마감일을 못 찾은 공지는 '공식 공지에서 확인'으로 뒤에 둔다. --all은 마감 지난 공지도 포함."""
import os
for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(k, "1")
import sys, warnings, datetime
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from deadline import extract_deadline
from grades import extract_grades
from details import extract_details
warnings.filterwarnings("ignore")

FIELDS = ["취업·진로", "어학·자격증", "국제교류", "봉사·대외활동", "장학·경제지원"]  # 학생에게 보여주는 분야 (그 외 라벨은 추천에서 제외)


def text(df): return df.title + " " + df.title + " " + df.body.fillna("").str[:1500]


def load():
    raw = pd.read_csv("data/notices_raw.csv", encoding="utf-8-sig").drop_duplicates("title").reset_index(drop=True)
    lab = pd.read_csv("data/notices_labeled.csv", encoding="utf-8-sig")[["bbsno", "board", "label"]]
    d = raw.merge(lab, on=["bbsno", "board"], how="left")
    known = d.label.notna()
    model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3), min_df=2, max_features=30000, sublinear_tf=True),
                          LogisticRegression(C=10, max_iter=2000, class_weight="balanced"))
    model.fit(text(d[known]), d.label[known])
    d["field"] = d.label
    if (~known).any(): d.loc[~known, "field"] = model.predict(text(d[~known]))   # 라벨이 없는 새 공지만 예측
    d["predicted"] = ~known
    posted = pd.to_datetime(d.date).dt.date
    r = [extract_deadline(t, b, p) for t, b, p in zip(d.title, d.body.fillna(""), posted)]
    d["deadline"], d["evidence"], d["kind"] = zip(*r)
    d["grades"], d["grade_ev"] = zip(*[extract_grades(b) for b in d.body.fillna("")])
    det = pd.DataFrame([extract_details(t, b, p) for t, b, p in zip(d.title, d.body.fillna(""), posted)])
    d["apply_start"], d["target"], d["method"] = det.apply_start, det.target, det.method
    return d


def export(d, path="data/notices_parsed.csv"):
    """화면(웹)에서 쓸 수 있도록 분류·마감·학년·상세 정보를 한 파일로 저장한다."""
    o = d.copy()
    o["grades"] = o.grades.map(lambda g: "" if g is None else ",".join(map(str, sorted(g))) if g else "해당없음")
    o = o.rename(columns={"field": "분야", "kind": "deadline_kind", "evidence": "deadline_evidence"})
    o["deadline_kind"] = o.deadline_kind.replace("", "없음")
    o[["bbsno", "board", "title", "date", "dept", "url", "checked", "분야", "predicted", "apply_start", "deadline", "deadline_kind",
       "grades", "target", "method"]].to_csv(path, index=False, encoding="utf-8-sig")
    return o


def recommend(d, interests, today, include_past=False, grade=None):
    x = d[d.field.isin(interests)].copy()
    if grade:   # 대상 학년을 알 수 있고 그 학년이 아니면 제외 (졸업생·외국인 전용은 빈 집합이라 제외됨)
        x = x[x.grades.map(lambda g: g is None or grade in g)]
    x["end"] = pd.to_datetime(x.deadline)
    if not include_past:
        # 마감일이 지난 공지는 제외. 마감일을 모르는 공지(상시·없음·행사만)는 최근 게시된 것만 남긴다.
        recent = pd.to_datetime(x.date) >= pd.Timestamp(today) - pd.Timedelta(days=60)
        x = x[((x.kind == "마감") & (x.end >= pd.Timestamp(today))) | ((x.kind != "마감") & recent)]
    x["_o"] = (x.kind != "마감").astype(int)
    return x.sort_values(["_o", "end", "date"], ascending=[True, True, False])


def show(x, today):
    for r in x.itertuples():
        link = f"공식 공지에서 확인 → {r.url}"          # 확인하라고 안내하는 곳 바로 옆에 원본 공지 링크를 붙인다
        linked = False
        if r.kind == "마감": when = f"마감 {r.deadline} (D-{(r.deadline - today).days})" if r.deadline >= today else f"마감 {r.deadline} (종료)"
        elif r.kind == "상시": when, linked = f"상시·선착순 모집 — {link}", True
        else: when, linked = f"마감일 미확인 — {link}", True
        if r.grades is not None: who = "전 학년" if len(r.grades) == 4 else "·".join(map(str, sorted(r.grades))) + "학년"
        elif linked: who = "대상 확인 필요"
        else: who, linked = f"대상 확인 필요 — {link}", True
        tail = "" if linked else f" | 원본 공지 {r.url}"
        print(f"[{r.field}] {r.title[:48]}\n    {when} | {who} | 확인일 {r.checked}{tail}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--export" in argv:
        o = export(load()); print(f"저장: {len(o)}건 -> data/notices_parsed.csv"); sys.exit()
    grade = int(argv[argv.index("--grade") + 1]) if "--grade" in argv else None
    if grade: del argv[argv.index("--grade"):argv.index("--grade") + 2]
    args = [a for a in argv if not a.startswith("--")]
    interests = args[0].split(",") if args else FIELDS
    today = datetime.date.fromisoformat(args[1]) if len(args) > 1 else datetime.date.today()
    x = recommend(load(), interests, today, include_past="--all" in sys.argv, grade=grade)
    print(f"{today} 기준 {','.join(interests)}{f' / {grade}학년' if grade else ''}: {len(x)}건"); show(x, today)
