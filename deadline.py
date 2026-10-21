"""공지 본문에서 신청 마감일을 뽑는다. extract_deadline(title, body, posted) -> (마감일 or None, 근거 문구).
신청·접수·모집·제출 '기간/기한/일정/마감' 표현 뒤의 날짜들 중 마지막 날짜를 마감일로 본다."""
import re
from datetime import date

LABEL = re.compile(r"(신청|접수|모집|지원|제출|등록|응시|참가|납부|조사|선발|공모)\s*[-·]?\s*(기간|기한|일정|마감|일자)")
STOP = re.compile(r"[■□※●▶◆◇▷☞\[]|운영\s*(일시|기간|일정)|활동\s*(일시|기간)|교육\s*(일시|기간)|시험\s*(일|일정)|\d\s*차\s*시험|모집\s*대상|신청\s*(방법|대상|자격)|지원\s*(대상|자격|내용)|참가\s*(비|대상)|문의|장소")
ROLLING = re.compile(r"선착순|인원\s*충족|소진\s*시|상시|예산\s*소진")
TOKEN = re.compile(r"(?<![\d.])(?:(\d{4}|\d{2})[.\-/년])?(\d{1,2})[.\-/월](\d{1,2})(?:일|\.|(?![\d:]))")
DAY_ONLY = re.compile(r"(?:\([^)]*\))?[~∼～](\d{1,2})일(?![\d.])")
UNTIL = re.compile(r"[~∼～]\s*(\d{1,2})\s*[/.]\s*(\d{1,2})\s*(?:\([^)]*\))?\s*까지")


def _compact(s):
    return re.sub(r"\s+", "", s)


def _dates(snippet, posted):
    """snippet 안의 날짜들을 순서대로 [(date, 연도추정여부)]. 연도·월이 생략되면 앞 날짜에서 이어받는다.
    마지막 날짜 뒤에 '~'만 있고 끝나면(예: '8/11 ~ 인원충족시') open=True."""
    out, y = [], None
    s = _compact(snippet)
    open_end = False
    for t in TOKEN.finditer(s):
        yy, mm, dd = t.group(1), int(t.group(2)), int(t.group(3))
        inferred = not yy and y is None
        if yy: y = int(yy) + (2000 if len(yy) == 2 else 0)
        yr = y if y else posted.year
        try: out.append((date(yr, mm, dd), inferred))
        except ValueError: continue
        tail = s[t.end():]
        d2 = DAY_ONLY.match(tail)          # '2월16일(월)~27일' 처럼 월이 생략된 끝 날짜
        if d2:
            try: out.append((date(yr, mm, int(d2.group(1))), inferred))
            except ValueError: pass
        open_end = bool(re.match(r"(?:\([^)]*\))?[~∼～]\s*(?!\d)", tail))
    return out, open_end


EVENT = re.compile(r"(운영|행사|교육|시험|개최|활동)?\s*(일시|일자|일정|기간)\s*[:：]")
THRU = re.compile(r"((?:\d{4}\s*[.년]\s*)?\d{1,2}\s*[월./]\s*\d{1,2}\s*일?)[^\d]{0,12}까지")


def extract_deadline(title, body, posted):
    """-> (날짜 | None, 근거 문구, 종류). 종류: '마감'(신청 마감일) | '행사'(행사·운영일, 마감일 아님) | '상시' | ''(못 찾음)."""
    body = body or ""
    body = re.sub(r"^.{0,400}?조회수\s*:\s*\d+\s*", "", body, count=1, flags=re.S)  # 본문 머리의 제목·게시일·부서 제거
    body = _compact(body)                  # 원문에 '시 험 일'처럼 글자 사이까지 공백이 있어 모두 제거

    def fix(d, inferred):
        if inferred and d < posted and (posted - d).days > 180: d = date(d.year + 1, d.month, d.day)  # 연말 공지의 다음 해 마감
        return d

    # 1) 신청기간류 표현 뒤의 날짜
    for lab in LABEL.finditer(body):
        seg = body[lab.end():lab.end() + 70]
        stop = STOP.search(seg)
        if stop: seg = seg[:stop.start()]
        ds, open_end = _dates(seg, posted)
        if ds:
            if open_end: return None, "상시", "상시"
            return fix(*ds[-1]), _compact(lab.group(0) + seg)[:60], "마감"
    # 2) '~10/21까지', '10월 26일부터 11월 9일까지'
    for text in (title, body[:500]):
        u = UNTIL.search(text or "")
        if u:
            try: return fix(date(posted.year, int(u.group(1)), int(u.group(2))), True), u.group(0), "마감"
            except ValueError: pass
    t = THRU.search(body[:500])
    if t:
        ds, _ = _dates(t.group(1), posted)
        if ds: return fix(*ds[-1]), _compact(t.group(0))[:60], "마감"
    if ROLLING.search(body[:1000]): return None, "상시", "상시"
    # 3) 마감일이 없으면 행사·운영 일시 (마감일이 아님)
    for e in EVENT.finditer(body):
        ds, _ = _dates(body[e.end():e.end() + 60], posted)
        if ds: return fix(*ds[0]), _compact(e.group(0) + body[e.end():e.end() + 30])[:50], "행사"
    return None, "", ""
