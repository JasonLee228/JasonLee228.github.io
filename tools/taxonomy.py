"""Blog-oriented categories/tags. Notion folders are only a hint.

Chirpy expands a category only when posts have a 2nd-level category.
Every published post therefore gets exactly [primary, secondary] plus tags.
Container/index pages are not published as posts.
"""
import re

# Notion top-folder -> default (primary, secondary)
TOP = {
    "알고리즘": ("알고리즘", "정렬"),
    "Java": ("Java", "문법"),
    "C++": ("C++", "문법"),
    "프로그래머스": ("문제풀이", "프로그래머스"),
    "백준": ("문제풀이", "백준"),
    "Git": ("Git", "워크플로"),
    "Spring-Boot": ("Spring", "활용"),
    "Elasticsearch": ("Elasticsearch", "기초"),
    "개발 지식": ("개발지식", "동시성"),
    "리눅스": ("리눅스", "네트워크"),
    "기타": ("기타", "메모"),
    "외부사이트": ("기타", "링크"),
}

# Ancestor (or self) title contains -> override secondary (and sometimes primary)
COURSE = [
    ("스프링부트와 AWS", ("Spring", "웹서비스")),
    ("스프링 핵심 원리", ("Spring", "핵심원리")),
    ("스프링 MVC", ("Spring", "MVC")),
    ("inflearn] JPA", ("Spring", "JPA")),
    ("[inflearn] JPA", ("Spring", "JPA")),
    ("SPOTY", ("프로젝트", "SPOTY")),
    ("취미", ("기타", "취미")),
]

# Chirpy category archives are flat. Same secondary under two primaries
# would share one /categories/:name/ page — uniquify the collisions only.
UNIQUE_SEC = {
    ("C++", "문법"): "C++문법",
    ("Java", "테스트"): "단위테스트",
    ("Elasticsearch", "운영"): "클러스터운영",
}

SKIP_TITLES = {"외부사이트"}

COURSE_LABEL = {
    "MVC": "스프링 MVC",
    "핵심원리": "스프링 핵심원리",
    "JPA": "스프링 JPA",
}

SECTION_RE = re.compile(r"^[Ss]action\s+(\d+)\s*[).\-–]?\s*(.*)$")

TITLE_SECONDARY = [
    (r"정렬|sort", "정렬"),
    (r"제네릭|컬렉션", "컬렉션"),
    (r"scanner|bufferedreader|입력", "입출력"),
    (r"assertj|mockmvc|mockwebserver|test", "테스트"),
    (r"security|oauth|kakao login|principalname", "보안"),
    (r"jpa|entity|영속성|연관관계|엔티티", "JPA"),
    (r"redis|webclient|aop|mysql|oom|scan", "운영"),
    (r"\bioc\b|\bdi\b|컴포넌트 스캔|싱글톤|스코프|생명주기 콜백", "핵심원리"),
    (r"servlet|jsp|mvc", "MVC"),
    (r"이벤트", "GUI"),
    (r"iptables|포트", "네트워크"),
    (r"cas|compare-and-swap|원자", "동시성"),
    (r"worktree|pull|github|repository", "워크플로"),
    (r"볼링", "취미"),
]


def clean_title(title):
    t = re.sub(r"[\r\n]+", " ", title or "")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^\[JAVA,?\s*자바\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[자바/JAVA[^\]]*\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[TEST\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[Git\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[SpringBoot\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[Spring\]\s*", "", t, flags=re.I)
    t = re.sub(r"^\[Spring boot Oauth2\]\s*", "", t, flags=re.I)
    t = re.sub(r"\[자바,?\s*JAVA\]", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -")
    return t or title


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def uniquify(primary, secondary):
    return primary, UNIQUE_SEC.get((primary, secondary), secondary)


def cat_slug(name):
    """Match Chirpy/Jekyll slugify: C++ → c, C++문법 → c-문법."""
    slug = re.sub(r"[^\w]+", "-", (name or "").lower())
    return re.sub(r"-{2,}", "-", slug).strip("-")


def cat_url(name):
    return f"/categories/{cat_slug(name)}/"


def first_heading(body):
    if not body:
        return ""
    for m in re.finditer(r"^(#{2,4})\s+(.*)$", body, re.M):
        text = re.sub(r"^#+\s*", "", m.group(2)).strip(" #")
        if text:
            return text
    return ""


def display_title(title, secondary=None, heading=""):
    """Turn Notion 'saction N' stubs into a readable lecture title."""
    t = clean_title(title)
    m = SECTION_RE.match(t)
    if not m:
        return t
    num, rest = m.group(1), (m.group(2) or "").strip(" -")
    if not rest:
        rest = (heading or "").strip()
    label = COURSE_LABEL.get(secondary or "")
    if label and rest:
        return f"{label} {num}. {rest}"
    if label:
        return f"{label} {num}"
    if rest:
        return f"{num}. {rest}"
    return t


def classify(path_titles, title, has_children, has_body):
    """Return (primary, secondary, tags) or None to skip publishing."""
    # Folders stay in the tree as categories, never as posts.
    if has_children:
        return None
    if not has_body:
        return None

    titles = [_norm(t) for t in path_titles if t]
    raw_title = _norm(title)
    if raw_title in SKIP_TITLES:
        return None
    blob = " ".join(titles + [raw_title]).lower()

    primary, secondary = "기타", "메모"
    if titles:
        top = titles[0]
        primary, secondary = TOP.get(top, (top, "기타"))

    for needle, pair in COURSE:
        if any(needle.lower() in t.lower() for t in titles + [raw_title]):
            primary, secondary = pair
            break

    if "콘솔만을 이용한 게시판" in raw_title:
        primary, secondary = "Java", "실습"

    # Title hints only refine default/generic secondaries, not 백준/코스 등.
    if (primary == "Java" and secondary != "실습") or (primary == "C++") or (
        primary == "Spring" and secondary == "활용"
    ):
        for pat, sec in TITLE_SECONDARY:
            if re.search(pat, raw_title, re.I):
                secondary = sec
                break

    if primary == "Elasticsearch":
        if re.search(r"08\.|09\.|10\.|운영|제약|mvp", blob):
            secondary = "운영"
        else:
            secondary = "기초"

    primary, secondary = uniquify(primary, secondary)
    tags = _tags(primary, secondary, blob, raw_title)
    return primary, secondary, tags


def _tags(primary, secondary, blob, title):
    tags = []

    def add(*xs):
        lower = {t.lower() for t in tags}
        for x in xs:
            if x and x.lower() not in lower:
                tags.append(x)
                lower.add(x.lower())

    add(secondary.lower() if secondary.isascii() else secondary)
    if primary == "문제풀이":
        add("알고리즘", "java")
    elif primary not in ("Spring", "Java", "Elasticsearch", "Git", "C++"):
        add(primary)
    if "java" in blob or "자바" in blob or primary == "Java":
        add("java")
    if primary == "Spring" or "spring" in blob:
        add("spring")
    if "elasticsearch" in blob or primary == "Elasticsearch":
        add("elasticsearch")
    if "oauth" in blob or "google" in blob:
        add("oauth2")
    if "jpa" in blob or secondary == "JPA":
        add("jpa")
    if "redis" in blob:
        add("redis")
    if "git" in blob or primary == "Git":
        add("git")
    if "security" in blob or secondary == "보안":
        add("security")
    if "linux" in blob or "리눅스" in blob or "iptables" in blob:
        add("linux")
    if re.search(r"백준|boj", blob):
        add("백준")
    if "프로그래머스" in blob:
        add("프로그래머스")
    if re.search(r"정렬|sort", blob):
        add("정렬")
    return tags[:6]
