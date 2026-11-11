---
title: "push 전에 중간 커밋 메시지만 고치기: git commit-tree로 tree와 날짜를 그대로 두는 방법"
date: 2026-11-06 18:30:00 +0900
categories: ["Git", "워크플로"]
tags: ["git", "commit-tree", "update-ref", "커밋메시지"]
permalink: /posts/push-전에-중간-커밋-메시지만-고치기-git-commit-tree로-tree와-날짜를-그대로-두는-방법/
---

## amend로는 안 되는 자리

커밋을 두 개 만들었다. 둘 다 제목 다음에 빈 줄이 빠져 본문이 제목에 붙어 버렸다.

{% raw %}
```text
e8fe10f #76708 fix: 둘째 커밋 - 역시 빈 줄 없음
a95848f #76707 fix: 첫 커밋 - 제목 뒤 빈 줄이 빠진 본문
42df82e chore: 기본 파일
```
{% endraw %}

`git log --oneline`에 본문이 한 줄로 이어져 나온다. 아직 push 전이니 고치면 된다. 그런데 `git commit --amend`는 **HEAD 하나만** 고친다. `a95848f`는 HEAD의 부모라 amend가 닿지 않는다.

보통은 `git rebase -i HEAD~2`에서 `reword`를 쓴다. 하지만 에디터를 못 띄우는 환경이 있다. 자동화 스크립트, CI, 코딩 에이전트가 그렇다. `GIT_SEQUENCE_EDITOR`와 `GIT_EDITOR`를 스크립트로 바꿔 끼우는 방법도 있지만, 두 커밋 메시지를 각각 다르게 넣으려면 번거롭다.

이럴 때 `git commit-tree`가 깔끔하다. 커밋 객체를 **직접 만든다**.

---

## 커밋 객체는 네 가지로 만들어진다

커밋은 다음 정보의 묶음이다.

- tree: 그 시점 파일 전체의 스냅샷 해시
- parent: 부모 커밋 해시
- author / committer: 이름, 이메일, 시각
- message

`git commit-tree <tree> -p <parent> -m <message>`는 이 넷을 받아 커밋 객체를 하나 만들고 해시를 출력한다. 브랜치는 건드리지 않는다. 그래서 원하는 만큼 만들고 마지막에 브랜치를 옮기면 된다.

중요한 점: **tree를 원래 커밋 것으로 쓰면 코드는 1바이트도 안 바뀐다.** 메시지만 바뀐 "같은 스냅샷"의 새 커밋이 생긴다.

---

## 절차

두 커밋 `C1`(앞), `C2`(뒤)의 메시지를 고친다. `BASE`는 `C1`의 부모다.

{% raw %}
```bash
C1=$(git rev-parse HEAD~1)
C2=$(git rev-parse HEAD)
BASE=$(git rev-parse HEAD~2)
```
{% endraw %}

### 1. 앞 커밋을 다시 만든다

author와 날짜는 원래 커밋에서 읽어 환경변수로 넘긴다. 메시지는 `-m`을 두 번 써서 제목과 본문을 분리한다. `-m`을 여러 번 주면 각 문단 사이에 빈 줄이 들어간다.

{% raw %}
```bash
N1=$(
  GIT_AUTHOR_NAME="$(git log -1 --format=%an $C1)" \
  GIT_AUTHOR_EMAIL="$(git log -1 --format=%ae $C1)" \
  GIT_AUTHOR_DATE="$(git log -1 --format=%aI $C1)" \
  GIT_COMMITTER_DATE="$(git log -1 --format=%cI $C1)" \
  git commit-tree "$C1^{tree}" -p "$BASE" \
      -m "$(git log -1 --format=%s $C1)" \
      -m "$(git log -1 --format=%b $C1)"
)
```
{% endraw %}

`%s`는 제목, `%b`는 본문이다. 원래 메시지에 빈 줄이 없어서 본문이 제목에 붙어 있었다면 `%s`에 전체가 들어온다. 그때는 `-m`에 고친 제목과 본문을 직접 적는다.

### 2. 뒤 커밋은 새 앞 커밋을 부모로

`-p`에 원래 `C1`이 아니라 **방금 만든 `N1`**을 준다. 이걸 빼먹으면 뒤 커밋이 옛 앞 커밋을 가리켜 고친 게 사라진다.

{% raw %}
```bash
N2=$(
  GIT_AUTHOR_NAME="$(git log -1 --format=%an $C2)" \
  GIT_AUTHOR_EMAIL="$(git log -1 --format=%ae $C2)" \
  GIT_AUTHOR_DATE="$(git log -1 --format=%aI $C2)" \
  GIT_COMMITTER_DATE="$(git log -1 --format=%cI $C2)" \
  git commit-tree "$C2^{tree}" -p "$N1" \
      -m "$(git log -1 --format=%s $C2)" \
      -m "$(git log -1 --format=%b $C2)"
)
```
{% endraw %}

### 3. 브랜치를 새 끝으로 옮긴다

{% raw %}
```bash
git update-ref -m "commit-tree rewrite" refs/heads/main "$N2" "$C2"
```
{% endraw %}

마지막 인자 `$C2`는 "현재 값이 이것일 때만 바꿔라"는 안전장치다. 사이에 누가 커밋했으면 실패한다. reflog에도 남는다. `git reset --soft "$N2"`로도 같은 효과지만, `update-ref`는 작업 트리와 index를 전혀 건드리지 않는다.

---

## 확인

{% raw %}
```text
$ git log --format="%h %ad %s" --date=iso -n 3
482e6d8 2026-11-03 14:01:08 +0900 #76708 fix: 둘째 커밋
3fa5d82 2026-11-03 14:00:50 +0900 #76707 fix: 첫 커밋
42df82e 2026-11-06 18:03:51 +0900 chore: 기본 파일

$ git cat-file commit HEAD | sed -n '/^$/,$p'

#76708 fix: 둘째 커밋

- 역시 빈 줄 없음
```
{% endraw %}

- 해시는 바뀌었다(`e8fe10f` → `482e6d8`). 메시지가 커밋 해시의 입력이라 당연하다.
- 날짜는 원래 값 그대로다.
- 제목과 본문 사이에 빈 줄이 들어갔다.

tree가 같은지는 한 줄로 본다.

{% raw %}
```bash
[ "$(git rev-parse HEAD^{tree})" = "$(git rev-parse $C2^{tree})" ] && echo same
git diff --stat $C2 HEAD      # 출력 없음 = 파일 차이 없음
```
{% endraw %}

옛 커밋 `e8fe10f`, `a95848f`는 **고아(orphan)** 로 남는다. 아무 브랜치도 가리키지 않지만 reflog가 참조하는 동안 객체는 살아 있다. 되돌리고 싶으면 `git update-ref refs/heads/main $C2`로 돌아갈 수 있다. 시간이 지나면 `gc`가 치운다.

---

## 주의할 것

**commit-msg hook은 돌지 않는다.** `commit-tree`는 plumbing 명령이라 `git commit`의 hook을 거치지 않는다. 메시지 형식 검사 hook이 있다면 고친 메시지가 규칙에 맞는지 직접 확인한다. 이번 경우는 hook이 요구하는 "제목 뒤 빈 줄"을 맞추는 작업이었으니 결과를 `git cat-file commit`으로 눈으로 봤다.

**sed로 메시지를 다루면 빈 줄을 날리기 쉽다.** 처음에 `git log --format=%B | sed ...`로 메시지를 가공했다가 빈 줄이 또 사라졌다. `-m`을 두 번 쓰는 쪽이 안전하다.

**이미 push한 커밋에는 쓰지 않는다.** 해시가 바뀌므로 rebase와 같은 성격이다. 공유 브랜치에서는 force push가 필요하고, 다른 사람의 로컬과 어긋난다. 이 글의 범위는 **push 전 로컬 커밋**이다.

**머지 커밋은 `-p`를 두 번 준다.** `git commit-tree <tree> -p <p1> -p <p2>`.

---

## 정리

| 항목 | 내용 |
|---|---|
| 상황 | push 전, HEAD가 아닌 커밋의 메시지만 고치고 싶다. 에디터 없이 |
| 도구 | `git commit-tree <tree> -p <parent> -m <제목> -m <본문>` |
| 유지할 것 | `C^{tree}`로 같은 스냅샷, `GIT_AUTHOR_*`·`GIT_COMMITTER_DATE`로 같은 시각 |
| 순서 | 앞 커밋부터 만든다. 뒤 커밋의 `-p`는 새로 만든 앞 커밋 |
| 반영 | `git update-ref -m <사유> refs/heads/<branch> <new> <old>` |
| 확인 | `git cat-file commit HEAD`, tree 해시 비교, `git diff --stat <old> HEAD` |
| 주의 | hook 미실행, sed로 빈 줄 유실, push 후에는 쓰지 않음 |

실험은 Git for Windows의 bash에서 임시 저장소를 만들어 했다. `git rebase -i`가 되는 환경이면 그쪽이 더 짧다. 이 방법은 에디터를 못 쓰거나, 날짜까지 정확히 보존해야 할 때 쓴다.
