"""공지 본문의 '모집대상·신청대상' 항목에서 대상 학년을 뽑는다. extract_grades(body) -> (대상 학년 집합 | None, 근거 문구).
None은 대상 항목이 없거나 학년을 알 수 없다는 뜻이다(이때는 공식 공지에서 확인하도록 안내). 졸업생·대학원생 전용이면 빈 집합."""
import re

TARGET = re.compile(r"(모집|신청|참여|지원|응시|참가|선발|교육|등록|제출)\s*(대상|자격)\s*(?:자)?\s*[:：]?|대상\s*[:：]")
STOP = re.compile(r"[■□※●▶◆◇▷☞]|모집\s*인원|선발\s*인원|신청\s*(기간|방법)|모집\s*기간|접수|진행\s*방법|참가\s*비|문의|장소|일시")
ALL = {1, 2, 3, 4}


def _compact(s): return re.sub(r"\s+", "", s)


def _grades(seg):
    g, found = set(), False
    for m in re.finditer(r"([1-4])[~∼-]([1-4])학년", seg):          # 2~4학년
        g |= set(range(int(m[1]), int(m[2]) + 1)); found = True
    for m in re.finditer(r"([1-4](?:[·,、/및]+[1-4])+)학년", seg):    # 3·4학년, 1,2,3학년
        g |= {int(x) for x in re.findall(r"[1-4]", m[1])}; found = True
    for m in re.finditer(r"([1-4])학년(이상|이하)", seg):            # 2학년 이상
        n = int(m[1]); g |= set(range(n, 5)) if m[2] == "이상" else set(range(1, n + 1)); found = True
    if not found:
        for m in re.finditer(r"([1-4])학년(?!\d?학기)", seg):         # 단독 N학년 ('1학년1학기' 같은 학점 문구 제외)
            g.add(int(m[1])); found = True
    if "전학년" in seg or "모든학년" in seg or "모든학적" in seg: return set(ALL)
    return g if found else None


def extract_grades(body):
    b = re.sub(r"^.{0,400}?조회수\s*:\s*\d+\s*", "", body or "", count=1, flags=re.S)
    for t in TARGET.finditer(b):
        seg = b[t.end():t.end() + 90]
        stop = STOP.search(seg)
        if stop: seg = seg[:stop.start()]
        seg = _compact(seg)
        if not seg: continue
        g = _grades(seg)
        if g: return g, seg[:40]
        if "신입생" in seg and "재학생" not in seg: return {1}, seg[:40]          # 신입생 전용
        if "졸업예정" in seg and not re.search(r"재학|학년", seg): return {4}, seg[:40]
        if re.search(r"재학생|휴학생|누구나|모든(대)?학생|모든대학생|본교학생|수원대(학교)?학생", seg): return set(ALL), seg[:40]  # 학년 제한 없음
        if re.search(r"졸업생|대학원생|외국인|지역청년|청소년", seg) and "재학" not in seg: return set(), seg[:40]  # 재학생 대상 아님
    return None, ""
