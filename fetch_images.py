"""마감일 등을 본문에서 못 읽은 공지의 본문 사진(포스터·안내문 이미지) 주소를 모아 data/notices_images.csv로 저장한다.
사용: python fetch_images.py   (data/notices_parsed.csv에서 마감일이 없는 2026년 공지만, 이미 모은 것은 건너뜀)"""
import os, csv
import pandas as pd
import collect as c

OUT = "data/notices_images.csv"
d = pd.read_csv("data/notices_parsed.csv", encoding="utf-8-sig").fillna("")
d = d[(d.deadline_kind != "마감") & (d.date >= "2026-01-01")]
done = set()
if os.path.exists(OUT):
    done = {(r["board"], r["bbsno"]) for r in csv.DictReader(open(OUT, encoding="utf-8-sig"))}
rows = [dict(board=b, bbsno=str(n), images=i) for b, n, i in
        (csv.reader([x]).__next__() for x in []) ] if False else []
if os.path.exists(OUT): rows = list(csv.DictReader(open(OUT, encoding="utf-8-sig")))
hid = {}
for r in d.itertuples():
    if (r.board, str(r.bbsno)) in done: continue
    menuno = c.BOARDS[r.board]
    hid.setdefault(r.board, c.hidden(c.get(params={"menuno": menuno})))
    h = hid[r.board]
    soup = c.get(params={"menuno": menuno, "bbsno": r.bbsno, "boardno": h["boardno"], "siteno": h["siteno"], "act": "view"})
    imgs = [i["src"] for i in soup.select("img") if "/upload/" in (i.get("src") or "")]   # 로고·아이콘 제외, 업로드된 본문 이미지만
    imgs = [u if u.startswith("http") else "https://www.suwon.ac.kr" + u for u in imgs]
    rows.append(dict(board=r.board, bbsno=r.bbsno, images="|".join(dict.fromkeys(imgs))))
    print(r.board, r.bbsno, len(imgs), flush=True)
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["board", "bbsno", "images"]); w.writeheader(); w.writerows(rows)
print("저장:", len(rows), "건 ->", OUT)
