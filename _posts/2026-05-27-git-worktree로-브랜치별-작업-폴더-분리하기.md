---
title: "git worktree로 브랜치별 작업 폴더 분리하기"
date: 2026-05-27 04:55:02 +0000
categories: ["Git", "워크플로"]
tags: ["워크플로", "git"]
---

> 💡 
>
> 서로 다른 브랜치를 각각 다른 폴더에서 관리하는 방법은 크게 두 가지가 있다. 하나는 저장소를 브랜치별로 여러 번 clone하는 방식이고, 다른 하나는 Git이 제공하는 `git worktree`를 사용하는 방식이다. 둘 다 가능하지만, 목적과 운영 방식에 따라 장단점이 다르다.

---

### 서로 다른 브랜치를 다른 폴더에서 관리하는 법

일반적으로 Git 저장소 하나의 작업 폴더에서는 한 번에 하나의 브랜치만 체크아웃할 수 있다.

{% raw %}
```text
D:\git_workspace\sample-api
  현재 브랜치: develop
```
{% endraw %}

이 상태에서 `feature-search` 브랜치를 보려면 기존 폴더에서 브랜치를 전환해야 한다. 하지만 작업 중인 변경사항이 있거나 두 브랜치를 동시에 빌드·비교해야 한다면 브랜치 전환이 번거로워진다.

이 문제를 해결하는 가장 단순한 방법은 브랜치별로 저장소를 따로 clone하는 것이다.

{% raw %}
```powershell
cd D:\git_workspace

git clone <repo-url> sample-api-develop
cd sample-api-develop
git checkout develop

cd D:\git_workspace
git clone <repo-url> sample-api-feature-search
cd sample-api-feature-search
git checkout feature-search
```
{% endraw %}

그러면 폴더 구조는 다음처럼 된다.

{% raw %}
```text
D:\git_workspace\sample-api-develop
  브랜치: develop

D:\git_workspace\sample-api-feature-search
  브랜치: feature-search
```
{% endraw %}

이 방식은 `git worktree`를 몰라도 이해하기 쉽고, 각 폴더가 완전히 독립적인 저장소로 동작한다.

---

### 여러 번 clone하는 방식의 장단점

여러 번 clone하는 방식의 장점은 단순함과 독립성이다.

- 각 폴더가 완전히 별개의 Git 저장소라서 개념적으로 이해하기 쉽다.

- 같은 브랜치를 여러 폴더에서 동시에 체크아웃할 수 있다.

- `.git`, `.cursor`, 로컬 설정, IDE 설정을 폴더별로 완전히 따로 둘 수 있다.

- 한 폴더에서 Git 설정이나 실험을 해도 다른 폴더에 직접적인 영향을 주지 않는다.

반면 단점도 있다.

- 저장소를 여러 번 clone하므로 디스크 사용량이 늘어난다.

- 각 폴더마다 `fetch`, `pull`, remote 상태를 따로 관리해야 한다.

- 같은 변경사항을 여러 clone에 반영하려면 각각 동기화해야 한다.

- 브랜치가 많아질수록 폴더와 원격 추적 상태가 흩어지기 쉽다.

따라서 완전히 독립된 환경이 필요하거나, 같은 브랜치를 여러 폴더에서 동시에 다뤄야 한다면 여러 번 clone하는 방식이 편할 수 있다.

---

### git worktree 방식

`git worktree`를 사용하면 저장소를 새로 clone하지 않고도 같은 저장소의 다른 브랜치를 별도 폴더로 꺼내 둘 수 있다.

{% raw %}
```text
D:\git_workspace\sample-api
  브랜치: develop 또는 일반 작업용 브랜치

D:\git_workspace\sample-api-feature-search
  브랜치: feature-search
```
{% endraw %}

기본 명령은 다음과 같다.

{% raw %}
```powershell
git worktree add ../sample-api-feature-search feature-search
```
{% endraw %}

위 명령은 현재 저장소 옆에 `sample-api-feature-search` 폴더를 만들고, 그 폴더를 `feature-search` 브랜치 상태로 체크아웃한다.

`git worktree`는 Git 히스토리와 객체 저장소는 공유하면서, 작업 디렉터리만 추가로 만드는 방식이다. 즉, clone처럼 저장소 전체를 별도로 하나 더 만드는 것이 아니라, 하나의 저장소에 여러 작업 폴더를 연결하는 구조에 가깝다.

---

### worktree 방식의 장단점

worktree 방식의 장점은 가볍고 Git 관리가 일관적이라는 점이다.

- 하나의 저장소 객체를 공유하므로 여러 번 clone하는 것보다 디스크 사용량이 적다.

- 브랜치별 작업 폴더를 Git이 공식적으로 관리해준다.

- 기준 브랜치와 기능 브랜치를 동시에 열어 비교하거나 빌드하기 좋다.

- `git worktree list`로 연결된 작업 폴더를 한 번에 확인할 수 있다.

- 같은 저장소의 히스토리와 remote 정보를 공유하므로 브랜치 흐름을 한곳에서 파악하기 쉽다.

반면 다음과 같은 제약이 있다.

- 같은 브랜치는 동시에 두 worktree에서 체크아웃할 수 없다.

- 커밋하지 않은 변경사항은 새 worktree로 자동 복사되지 않는다.

- worktree 폴더를 삭제할 때는 `git worktree remove`로 정리하는 습관이 필요하다.

- `.cursor`처럼 커밋되지 않은 로컬 설정 파일은 새 worktree에 자동으로 생기지 않는다.

- 각 worktree가 같은 DB, 포트, 큐 등을 바라보면 실행 환경 충돌은 여전히 발생할 수 있다.

따라서 브랜치별 작업 폴더를 가볍게 유지하면서 Git 흐름을 일관되게 관리하고 싶다면 `git worktree`가 적합하다.

---

### 어떤 방식을 선택하면 좋을까

완전히 독립된 폴더가 필요하면 여러 번 clone하는 방식이 단순하다. 특히 같은 브랜치를 여러 폴더에서 동시에 체크아웃해야 하거나, 폴더별로 `.cursor`나 IDE 설정을 완전히 다르게 가져가고 싶다면 clone 방식이 편하다.

반대로 같은 저장소의 여러 브랜치를 가볍게 나눠 열어두고 싶다면 `git worktree`가 더 적합하다. 기준 브랜치와 기능 브랜치를 동시에 확인하거나, 브랜치 전환 없이 두 작업 상태를 비교할 때 특히 유용하다.

간단히 정리하면 다음과 같다.

{% raw %}
```text
완전히 독립된 저장소 폴더가 필요함
  -> 여러 번 git clone

하나의 저장소를 공유하면서 브랜치별 작업 폴더만 필요함
  -> git worktree
```
{% endraw %}

이 글에서는 브랜치별 폴더 관리 방식 중에서도 Git이 공식적으로 제공하는 `git worktree`를 중심으로 정리한다.

---

### 현재 폴더를 유지하고 특정 브랜치만 worktree로 빼기

예를 들어 현재 폴더인 `sample-api`는 그대로 두고, `feature-search` 브랜치만 별도 worktree로 만들 수 있다.

{% raw %}
```powershell
cd D:\git_workspace\sample-api
git worktree add ../sample-api-feature-search feature-search
```
{% endraw %}

이렇게 하면 구조는 다음처럼 된다.

{% raw %}
```text
D:\git_workspace\sample-api
  메인 worktree
  develop, main, 다른 feature 브랜치로 전환 가능
  단, feature-search로는 checkout 불가

D:\git_workspace\sample-api-feature-search
  feature-search 브랜치 작업 폴더
```
{% endraw %}

여기서 중요한 점은 **같은 브랜치는 동시에 두 worktree에서 체크아웃할 수 없다**는 것이다.

따라서 `feature-search` 브랜치를 별도 worktree에서 사용 중이면, 기존 `sample-api` 폴더에서는 해당 브랜치로 checkout할 수 없다. Git이 브랜치 충돌을 막는다.

---

### worktree 폴더는 특정 브랜치 전용인가?

기술적으로는 worktree 폴더에서도 다른 브랜치로 checkout할 수 있다. 하지만 실무적으로는 권장하지 않는다.

예를 들어 `sample-api-feature-search`라는 폴더를 만들었다면, 그 폴더는 `feature-search` 브랜치 전용으로 쓰는 편이 안전하다.

이렇게 운용하면 각 폴더의 의미가 명확해진다.

{% raw %}
```text
sample-api
  일반 작업용, 브랜치 이동 가능

sample-api-feature-search
  기능 브랜치 전용
```
{% endraw %}

폴더 이름과 브랜치 역할이 일치하면 IDE, 터미널, 실행 서버를 여러 개 띄워도 혼동이 줄어든다.

---

### 커밋하지 않은 작업내역은 가져가는가?

새 worktree를 만들 때 가져가는 것은 대상 브랜치의 **마지막 커밋 상태**다.

자동으로 가져가지 않는 것들은 다음과 같다.

- tracked 파일이지만 수정 후 커밋하지 않은 내용

- `git add`로 staged 해둔 내용

- untracked 파일

- ignored 파일

- 현재 작업 폴더의 로컬 빌드 산출물

예를 들어 현재 폴더에 다음 변경사항이 있다고 하자.

{% raw %}
```text
application.yml        수정됨, 커밋 안 함
SomeService.java       수정 후 git add 함, 커밋 안 함
TestController.java    새 파일, git add 안 함
```
{% endraw %}

이 상태에서 worktree를 만들면 새 worktree에는 위 변경사항이 자동 복사되지 않는다. 새 폴더에는 `feature-search` 브랜치에 커밋되어 있는 파일만 체크아웃된다.

변경사항을 새 worktree로 가져가고 싶다면 보통 다음 중 하나를 선택한다.

1. 임시 커밋을 만든다.

1. `git stash`로 저장한 뒤 새 worktree에서 적용한다.

1. 필요한 파일만 직접 복사한다.

실무에서는 공유할 변경사항이면 커밋, 아직 애매한 작업이면 stash가 무난하다.

---

### 커밋되지 않은 로컬 설정 파일은 어떻게 되는가

`git worktree`는 대상 브랜치에 커밋된 파일만 새 폴더에 체크아웃한다. 그래서 `.cursor`, `.env`, 로컬 전용 설정 파일처럼 커밋되지 않은 파일은 새 worktree에 자동으로 생기지 않는다.

예를 들어 현재 폴더에만 untracked 상태의 `.cursor/rules`가 있다면, 새 worktree 폴더에는 해당 규칙 파일이 없다.

이 경우 선택지는 보통 세 가지다.

- 팀 공통 규칙이면 `.cursor/rules`를 저장소에 커밋한다.

- 개인 로컬 설정이면 새 worktree에 직접 복사한다.

- 여러 프로젝트에서 공통으로 쓸 설정이면 IDE의 사용자 규칙이나 전역 설정으로 옮긴다.

여러 번 clone하는 방식도 untracked 파일을 자동으로 가져가지는 않는다. 다만 clone 방식은 각 폴더가 완전히 독립된 저장소이므로, 폴더별 로컬 설정을 따로 유지하기에는 더 직관적일 수 있다.

---

### worktree별 Git 작업은 독립적인가

worktree로 나누어진 폴더에서는 `commit`, `pull`, `push` 같은 Git 작업을 해당 폴더의 현재 브랜치 기준으로 수행한다.

예를 들어 다음과 같은 구조가 있다고 하자.

{% raw %}
```text
D:\git_workspace\sample-api
  브랜치: develop

D:\git_workspace\sample-api-feature-search
  브랜치: feature-search
```
{% endraw %}

이때 `sample-api-feature-search` 폴더에서 다음 명령을 실행하면, 기본적으로 `feature-search` 브랜치 기준으로 동작한다.

{% raw %}
```powershell
git commit
git pull
git push
```
{% endraw %}

원본 폴더인 `sample-api`의 체크아웃 브랜치나 작업 파일이 직접 바뀌지는 않는다. 따라서 작업 폴더 관점에서는 독립적으로 돌아간다고 이해해도 된다.

독립적으로 관리되는 것은 다음과 같다.

- 현재 체크아웃된 브랜치

- working tree의 파일 변경사항

- staging area, 즉 `git add` 상태

- `git status` 결과

- 커밋 작업 대상

- `target/` 같은 빌드 산출물

- `.env`, `.cursor` 같은 폴더별 로컬 파일

하지만 Git 저장소 내부 정보 중 일부는 공유된다.

- Git object database, 즉 커밋 히스토리 저장소

- 로컬 브랜치 목록

- remote 설정

- `fetch`로 갱신되는 `origin/*` 원격 추적 브랜치

- stash 목록

따라서 한 worktree에서 `git fetch`를 실행하면 다른 worktree에서도 갱신된 `origin/develop`, `origin/feature-search` 같은 원격 추적 브랜치 정보를 볼 수 있다. 하지만 한 worktree에서 `git pull`을 했다고 다른 worktree의 작업 파일이 자동으로 바뀌지는 않는다.

주의할 점은 다음과 같다.

- 한 worktree에서 remote 설정을 바꾸면 같은 저장소의 다른 worktree에도 영향을 줄 수 있다.

- 다른 worktree에서 사용 중인 브랜치는 삭제가 막힐 수 있다.

- stash는 저장소 단위로 공유되므로 양쪽 worktree에서 같은 stash 목록이 보일 수 있다.

정리하면, **작업 파일과 커밋 대상은 worktree별로 독립적이지만, Git의 내부 저장소 정보와 remote 정보는 공유된다**고 보면 된다.

---

### 원격 브랜치가 삭제되면 어떻게 되는가

원격에서 `feature-search` 브랜치가 삭제되어도 로컬 worktree 폴더가 즉시 사라지거나 망가지지는 않는다.

예를 들어 원격 브랜치가 삭제된 뒤 `git fetch --prune`을 실행하면 다음 상태가 될 수 있다.

{% raw %}
```text
로컬 브랜치 feature-search
  남아 있음

worktree 폴더
  남아 있음

origin/feature-search
  삭제됨

upstream 연결
  끊김
```
{% endraw %}

이때 `git status`에서는 다음과 비슷한 메시지가 나올 수 있다.

{% raw %}
```text
Your branch is based on 'origin/feature-search', but the upstream is gone.
```
{% endraw %}

이 상태에서도 로컬 커밋은 계속 가능하다. 다만 `git pull`은 받을 원격 브랜치가 없기 때문에 실패하거나 경고가 날 수 있고, `git push`는 upstream을 다시 잡아야 할 수 있다.

같은 이름으로 원격 브랜치를 다시 만들려면 다음처럼 push한다.

{% raw %}
```powershell
git push -u origin feature-search
```
{% endraw %}

더 이상 필요 없다면 worktree와 로컬 브랜치를 정리하면 된다.

{% raw %}
```powershell
git worktree remove ../sample-api-feature-search
git branch -d feature-search
```
{% endraw %}

---

### worktree를 삭제하면 폴더도 삭제되는가

`git worktree remove`를 사용하면 해당 worktree 폴더도 함께 삭제된다.

{% raw %}
```powershell
git worktree remove ../sample-api-feature-search
```
{% endraw %}

이 명령은 `D:\git_workspace\sample-api-feature-search` 폴더를 제거한다.

다만 미커밋 변경사항이나 untracked 파일이 있으면 Git이 삭제를 막을 수 있다. 작업내용 손실을 막기 위한 보호 장치다.

강제로 삭제하려면 `--force`를 사용할 수 있다.

{% raw %}
```powershell
git worktree remove --force ../sample-api-feature-search
```
{% endraw %}

하지만 이 경우 해당 worktree 안의 작업내용이 사라질 수 있으므로, 먼저 `git status`로 변경사항을 확인하는 것이 좋다.

또 하나 중요한 점은 `git worktree remove`가 삭제하는 것은 **작업 폴더**라는 것이다. 로컬 브랜치 자체는 보통 남아 있다.

완전히 정리하려면 보통 다음 순서를 사용한다.

{% raw %}
```powershell
git worktree remove ../sample-api-feature-search
git branch -d feature-search
```
{% endraw %}

정리하면 다음과 같다.

{% raw %}
```text
git worktree remove = worktree 폴더 삭제
git branch -d       = 로컬 브랜치 삭제
```
{% endraw %}

---

### 예제 프로젝트에서의 추천 운영 방식

일반적인 백엔드 API 프로젝트에서 기준 브랜치와 기능 브랜치를 동시에 봐야 한다면 다음 구조가 깔끔하다.

{% raw %}
```text
D:\git_workspace\sample-api
  일반 작업용 메인 폴더
  develop 또는 다른 브랜치 작업

D:\git_workspace\sample-api-feature-search
  기능 브랜치 전용 폴더
```
{% endraw %}

Cursor에서는 두 폴더를 함께 열 수 있다.

{% raw %}
```text
File > Add Folder to Workspace...
```
{% endraw %}

또는 `.code-workspace` 파일을 사용해 멀티 루트 워크스페이스로 관리할 수도 있다.

---

### 실무 주의사항

worktree는 Git 브랜치 관리는 깔끔하게 해주지만, 애플리케이션 실행 환경까지 자동으로 분리해주지는 않는다.

특히 백엔드 애플리케이션 프로젝트에서는 다음을 확인해야 한다.

- 두 worktree에서 서버를 동시에 실행하면 포트가 충돌할 수 있다.

- 같은 DB, Redis, RabbitMQ를 바라보면 테스트 데이터가 섞일 수 있다.

- `application.yml` 같은 로컬 설정 파일 변경은 자동 공유되지 않는다.

- Maven 의존성 캐시인 `~/.m2`는 공유되지만, 각 프로젝트의 `target/` 폴더는 별도다.

- IDE 인덱싱과 빌드 산출물이 worktree별로 따로 생긴다.

따라서 동시에 실행할 일이 있다면 포트, 프로필, DB 스키마, 큐 이름 등을 분리하는 것이 좋다.

---

### 자주 쓰는 명령어

현재 등록된 worktree 목록 확인:

{% raw %}
```powershell
git worktree list
```
{% endraw %}

새 worktree 추가:

{% raw %}
```powershell
git worktree add ../sample-api-feature-search feature-search
```
{% endraw %}

새 브랜치를 만들면서 worktree 추가:

{% raw %}
```powershell
git worktree add -b feature-new ../sample-api-feature-new develop
```
{% endraw %}

worktree 제거:

{% raw %}
```powershell
git worktree remove ../sample-api-feature-search
```
{% endraw %}

삭제된 worktree 정보 정리:

{% raw %}
```powershell
git worktree prune
```
{% endraw %}

로컬 브랜치 삭제:

{% raw %}
```powershell
git branch -d feature-search
```
{% endraw %}

원격 추적 브랜치 정리:

{% raw %}
```powershell
git fetch --prune
```
{% endraw %}

---

### 결론

서로 다른 브랜치를 다른 폴더에서 관리하는 방법은 여러 번 clone하는 방식과 `git worktree` 방식이 있다.

여러 번 clone하는 방식은 단순하고 완전히 독립적이다. 반면 저장소가 여러 개로 흩어지고 동기화를 폴더별로 관리해야 한다.

`git worktree`는 하나의 저장소를 공유하면서 브랜치별 작업 폴더만 추가하는 방식이다. 가볍고 Git 흐름이 일관적이지만, 같은 브랜치를 동시에 두 worktree에서 사용할 수 없고 커밋되지 않은 로컬 파일은 자동으로 복사되지 않는다.

기준 브랜치와 기능 브랜치를 동시에 열어두고 비교·작업하는 용도라면 `git worktree`가 보통 더 깔끔하다. 다만 완전한 독립 환경이나 같은 브랜치의 중복 체크아웃이 필요하다면 여러 번 clone하는 방식이 더 편할 수 있다.
