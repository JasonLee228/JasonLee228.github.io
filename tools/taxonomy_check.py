#!/usr/bin/env python3
"""Assert-based check for blog taxonomy. Run: python3 tools/taxonomy_check.py"""
import taxonomy as T

assert T.classify(["Java"], "replace() / replaceAll()", False, True)[:2] == ("Java", "문법")
assert T.classify(["Java"], "[TEST] assertj method", False, True)[:2] == ("Java", "테스트")
assert T.classify(["백준"], "백준 2750, 수 정렬하기", False, True)[:2] == ("문제풀이", "백준")
assert T.classify(["알고리즘"], "삽입 정렬", False, True)[:2] == ("알고리즘", "정렬")
assert T.classify(["Spring-Boot", "[inflearn] JPA"], "엔티티 매핑", False, True)[:2] == ("Spring", "JPA")
assert T.classify(["기타", "SPOTY-PROJECT"], "oauth2", False, True)[:2] == ("프로젝트", "SPOTY")
assert T.classify(["Java"], "folder", True, True) is None
assert T.classify(["Java"], "folder", True, False) is None
assert "java" in T.classify(["Java"], "String.isEmpty", False, True)[2]
print("taxonomy_check: ok")
