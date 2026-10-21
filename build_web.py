"""data/notices_parsed.csv -> web/index.html (데이터를 안에 넣은 정적 페이지). 사용: python build_web.py"""
import json, pandas as pd
FIELDS = ["취업·진로", "어학·자격증", "국제교류", "봉사·대외활동", "장학·경제지원"]
d = pd.read_csv("data/notices_parsed.csv", encoding="utf-8-sig").fillna("")
d = d[d.분야.isin(FIELDS)]
def grades(g): return None if g == "" else [] if g == "해당없음" else [int(x) for x in str(g).split(",")]
rows = [dict(id=f"{r.board}-{r.bbsno}", field=r.분야, title=r.title, date=r.date, dept=r.dept, board=r.board, url=r.url, checked=r.checked,
             predicted=bool(r.predicted), start=r.apply_start or None, end=r.deadline or None, kind=r.deadline_kind,
             grades=grades(r.grades), target=r.target or None, method=r.method or None) for r in d.itertuples()]
html = open("web/template.html", encoding="utf-8").read().replace("__DATA__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
open("web/index.html", "w", encoding="utf-8").write(html)
print(f"web/index.html: 공지 {len(rows)}건, {len(html)//1024}KB")
