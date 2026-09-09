#!/usr/bin/env python3
"""Assert-based check for blog taxonomy. Run: python3 tools/taxonomy_check.py"""
import taxonomy as T

assert T.classify(["Java"], "replace() / replaceAll()", False, True)[:2] == ("Java", "문법")
assert T.classify(["Java"], "[TEST] assertj method", False, True)[:2] == ("Java", "단위테스트")
assert T.classify(["백준"], "백준 2750, 수 정렬하기", False, True)[:2] == ("문제풀이", "백준")
assert T.classify(["알고리즘"], "삽입 정렬", False, True)[:2] == ("알고리즘", "정렬")
assert T.classify(["Spring-Boot", "[inflearn] JPA"], "엔티티 매핑", False, True)[:2] == ("Spring", "JPA")
assert T.classify(["기타", "SPOTY-PROJECT"], "oauth2", False, True)[:2] == ("프로젝트", "SPOTY")
assert T.classify(["Java"], "folder", True, True) is None
assert T.classify(["Java"], "folder", True, False) is None
assert "java" in T.classify(["Java"], "String.isEmpty", False, True)[2]

# Folder dumps / leftovers should not become posts.
assert T.classify(["기타"], "외부사이트", False, True) is None
assert T.classify(["기타"], "자바 콘솔만을 이용한 게시판 만들기 (진행중)", False, True)[:2] == ("Java", "실습")

# Chirpy archives are flat — colliding secondaries get unique names.
assert T.classify(["C++"], "cin도 표현식 형태를 가질 수 있다?", False, True)[:2] == ("C++", "C++문법")
assert T.classify(["Elasticsearch"], "08. Elasticsearch를 Database처럼 쓸 때의 제약", False, True)[:2] == (
    "Elasticsearch", "클러스터운영")
assert T.classify(["Spring-Boot"], "Redis SCAN으로 인한 부하 폭증", False, True)[:2] == ("Spring", "운영")
assert T.uniquify("Java", "테스트") == ("Java", "단위테스트")
assert T.uniquify("Spring", "테스트") == ("Spring", "테스트")

# Lecture stubs become readable titles; URL slug stays the old saction name.
assert T.display_title("saction 1", "MVC", "웹 애플리케이션 이해") == "스프링 MVC 1. 웹 애플리케이션 이해"
assert T.display_title("saction 4 - 스프링 컨테이너와 스프링 빈", "핵심원리") == (
    "스프링 핵심원리 4. 스프링 컨테이너와 스프링 빈")
assert T.display_title("Saction 3) 영속성 관리 - 내부 동작 방식", "JPA") == (
    "스프링 JPA 3. 영속성 관리 - 내부 동작 방식")
assert T.first_heading("## # 웹 애플리케이션 이해\n\n본문") == "웹 애플리케이션 이해"
assert T.cat_slug("C++") == "c"
assert T.cat_slug("C++문법") == "c-문법"
assert T.cat_url("단위테스트") == "/categories/단위테스트/"

print("taxonomy_check: ok")
