"""수원대 공지 수집: 게시판 목록 + 본문 -> data/notices_raw.csv
사용: python collect.py [페이지수] [게시판,게시판...]   (예: python collect.py 8 통합공지,취업공지)
이미 data/notices_raw.csv에 있는 공지는 건너뛰고 새 공지만 덧붙인다(덮어쓰지 않음).
"""
import os, sys, time, re, csv, datetime, requests
from bs4 import BeautifulSoup

BASE = "https://www.suwon.ac.kr/index.html"
BOARDS = {"통합공지": 674, "취업공지": 677, "국제협력처": 679, "어학원": 680, "장학대출": 2041}
HDR = {"User-Agent": "Mozilla/5.0 (student project; suwondae-zip)"}
DELAY = 1.0   # 서버 부담을 줄이기 위한 요청 간 대기(초)
s = requests.Session(); s.headers.update(HDR)

def get(params=None, data=None):
    time.sleep(DELAY)
    r = s.request("POST" if data else "GET", BASE, params=params, data=data, timeout=20)
    r.raise_for_status(); return BeautifulSoup(r.text, "html.parser")

def hidden(soup):
    return {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden]")
            if i.get("name") in ("ztag", "siteno", "boardno")}

def list_page(menuno, page, h):
    soup = get(params={"menuno": menuno}, data={"act": "list", "pageIndex": page, **h})
    rows = []
    for li in soup.select("ul li"):
        a = li.select_one("p.subject a")
        if not a: continue
        m = re.search(r"'view',(\d+)", a.get("onclick", ""))
        if not m: continue
        rows.append(dict(bbsno=m[1], title=a.get("title", "").strip(),
            date=li.select_one(".date").get_text(strip=True),
            dept=li.select_one(".writer").get_text(strip=True)))
    return rows

def detail(menuno, bbsno, h):
    soup = get(params={"menuno": menuno, "bbsno": bbsno, "boardno": h["boardno"],
                       "siteno": h["siteno"], "act": "view"})
    body = soup.select_one(".board_view, .view_cont, .view_content, .bbs_view, #contents")
    text = re.sub(r"\s+", " ", (body or soup).get_text(" ", strip=True))
    url = f"{BASE}?menuno={menuno}&bbsno={bbsno}&boardno={h['boardno']}&siteno={h['siteno']}&act=view"
    return text, url

RAW = "data/notices_raw.csv"

def main(pages, names=None):
    out, seen = [], set()
    if os.path.exists(RAW):
        with open(RAW, encoding="utf-8-sig", newline="") as f: out = list(csv.DictReader(f))
        seen = {(r["board"], r["bbsno"]) for r in out}
    n0 = len(out)
    today = datetime.date.today().isoformat()
    for name, menuno in BOARDS.items():
        if names and name not in names: continue
        h = hidden(get(params={"menuno": menuno}))
        for p in range(1, pages + 1):
            rows = list_page(menuno, p, h)
            print(f"{name} p{p}: {len(rows)}건"); 
            if not rows: break
            for r in rows:
                if (name, r["bbsno"]) in seen: continue
                seen.add((name, r["bbsno"]))
                text, url = detail(menuno, r["bbsno"], h)
                out.append({**r, "board": name, "body": text[:3000], "url": url, "checked": today})
    with open(RAW, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["bbsno","board","title","date","dept","body","url","checked"])
        w.writeheader(); w.writerows(out)
    print(f"저장: 기존 {n0}건 + 신규 {len(out) - n0}건 = {len(out)}건 -> {RAW}")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2,
         sys.argv[2].split(",") if len(sys.argv) > 2 else None)
