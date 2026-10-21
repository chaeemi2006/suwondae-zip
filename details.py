"""상세 화면용 정보: 신청 시작일, 신청 대상 문구, 신청 방법 문구를 본문에서 뽑는다.
extract_details(title, body, posted) -> dict(apply_start, target, method). 못 찾으면 None. 끝나는 날(마감일)은 deadline.py."""
import re
from deadline import LABEL, STOP as DSTOP, _compact, _dates
from grades import TARGET, STOP as GSTOP

METHOD = re.compile(r"(신청|접수|지원|참여|참가|제출|등록)\s*방법\s*[:：]?")
CUT = re.compile(r"[■□※●▶◆◇▷☞]|문의|신청\s*기간|모집\s*(기간|대상|인원)|제출\s*서류|유의\s*사항|선발\s*(방법|일정)")


ITEM = re.compile(r"\s(?:\d{1,2}[.)]|[가-하][.)]|[①-⑩])\s")      # 다음 번호 항목('5. 강연', '나. 모집')


def _clean(s, n):
    m = ITEM.search(s, 4)
    if m: s = s[:m.start()]
    s = re.sub(r"\s+", " ", s).strip(" -·:：[]")
    s = re.sub(r"\s*([,.)])", r"\1", s)
    s = re.sub(r"\(\s*([^()]*?)\s*$", r"(\1)", s) if s.count("(") > s.count(")") else s   # 닫히지 않은 괄호 정리
    return (s[:n].rstrip(" ,(") + "…") if len(s) > n else s


def extract_details(title, body, posted):
    b = re.sub(r"^.{0,400}?조회수\s*:\s*\d+\s*", "", body or "", count=1, flags=re.S)
    out = {"apply_start": None, "target": None, "method": None}
    cb = _compact(b)
    for lab in LABEL.finditer(cb):                       # 신청 시작일: 기간 표현에 날짜가 둘 이상일 때의 첫 날짜
        seg = cb[lab.end():lab.end() + 70]
        s = DSTOP.search(seg)
        if s: seg = seg[:s.start()]
        ds, open_end = _dates(seg, posted)
        if ds:
            if len(ds) >= 2 or open_end: out["apply_start"] = ds[0][0]
            break
    t = TARGET.search(b)
    if t:
        seg = b[t.end():t.end() + 90]
        s = GSTOP.search(seg)
        out["target"] = _clean(seg[:s.start()] if s else seg, 60) or None
    m = METHOD.search(b)
    if m:
        seg = b[m.end():m.end() + 110]
        s = CUT.search(seg)
        out["method"] = _clean(seg[:s.start()] if s else seg, 80) or None
    return out
