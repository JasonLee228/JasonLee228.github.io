---
title: "Redis Lua 조건부 CAS로 상태 전이를 원자화하기: first writer wins"
date: 2026-10-27 09:30:00 +0900
categories: ["Redis", "운영"]
tags: ["redis", "lua", "동시성", "상태기계", "테스트"]
permalink: /posts/redis-lua-조건부-cas로-상태-전이를-원자화하기-first-writer-wins/
---

## 완료된 작업이 몇 초 뒤에 "진행 중"으로 되돌아갔다

파일 다운로드 하나에 "티켓"을 발급하고, 티켓의 상태를 Redis에 두는 기능을 만들었다. 상태는 대략 이렇다.

{% raw %}
```text
ISSUED ─┬─▶ IN_USE_A ──▶ CLOSED
        ├─▶ IN_USE_B ──▶ CLOSED
        └─▶ FALLBACK   (A 경로가 상한에 걸려 B 경로로 넘어감)
```
{% endraw %}

`CLOSED`는 끝 상태다. 한 번 닫힌 티켓으로는 다시 받을 수 없어야 한다. 그런데 리뷰에서 이런 지적이 나왔다.

> 두 요청이 같은 `ISSUED`를 읽고 출발한다. 한쪽이 먼저 끝나 `CLOSED`를 저장한 뒤, 다른 쪽이 상한에 걸려 `FALLBACK`을 **덮어쓴다**. 이제 새 요청이 다시 들어올 수 있다.

코드는 단순했다. 상태를 읽고, 판단하고, 결과를 저장한다. 문제는 그 저장이 "내가 읽었던 상태가 아직 그대로인가"를 확인하지 않는다는 점이다.

{% raw %}
```java
// 문제의 패턴: 읽어둔 snapshot을 무조건 저장한다
Binding b = store.get(id);              // ISSUED
... 오래 걸리는 작업 ...
store.save(b.withState(FALLBACK));      // 그 사이 CLOSED가 됐어도 덮는다
```
{% endraw %}

이 글은 이 문제를 **조건부 전이**로 바꾼 과정을 정리한다. 이전 글 [Redis 캐시 backfill이 최신 값을 덮어쓸 때](/posts/redis-캐시-backfill이-최신-값을-덮어쓸-때/)와 뿌리가 같지만, 이번에는 값 하나가 아니라 상태 기계 전체가 대상이다.

---

## 동시 진입은 막지 않고, 전이만 제한한다

먼저 "무엇을 막아야 하는가"를 좁혔다.

- 두 요청이 **동시에** 같은 티켓을 쓰는 것은 이미 허용된 동작이다. 막을 대상이 아니다.
- 막아야 하는 것은 **끝 상태가 되돌아가는 것**이다. `CLOSED` 뒤에 `FALLBACK`이 오면 안 된다.

그래서 락을 걸지 않았다. 대신 전이마다 "어떤 상태에서만 허용되는가"를 정했다.

| 전이 | 허용 조건 |
|---|---|
| `ISSUED → IN_USE_*` | 현재가 `ISSUED` |
| `IN_USE_* → CLOSED` | 현재가 `IN_USE_*` 또는 `ISSUED` |
| `ISSUED → FALLBACK` | 현재가 `ISSUED`일 때만 |
| `CLOSED → *` | 없음. terminal |

이 표가 곧 CAS(compare-and-swap)의 "compare" 조건이다.

---

## Redis 구현: GET → 비교 → SET EX를 한 스크립트로

Redis 명령 하나는 원자적이지만, "읽고 → 판단하고 → 쓰기"는 세 명령이다. 그 사이에 다른 클라이언트가 끼어든다. Lua 스크립트는 실행 동안 다른 명령이 끼지 못하므로 이 세 단계를 하나로 묶을 수 있다.

{% raw %}
```lua
-- KEYS[1] = binding key
-- ARGV[1] = 기대하는 현재 state (쉼표로 여러 개 가능, 예: "ISSUED,IN_USE_A")
-- ARGV[2] = 새 state
-- ARGV[3] = TTL(초)
local current = redis.call('GET', KEYS[1])
if not current then
  return {0, 'MISSING'}
end

local allowed = false
for expected in string.gmatch(ARGV[1], '[^,]+') do
  if current == expected then allowed = true end
end
if not allowed then
  return {0, current}          -- 거절. 호출자가 현재 상태를 알 수 있게 돌려준다
end

redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
return {1, ARGV[2]}
```
{% endraw %}

Spring Data Redis에서는 `DefaultRedisScript`로 로드하고 `execute`한다. 반환값을 "성공/실패 + 현재 상태"로 받으면, 거절됐을 때 로그에 어떤 상태와 충돌했는지 남길 수 있다.

{% raw %}
```java
List<Object> r = redis.execute(transitionScript,
        List.of(key),
        "ISSUED",            // 기대 상태
        "FALLBACK",          // 새 상태
        String.valueOf(ttlSeconds));
boolean applied = Long.valueOf(1).equals(r.get(0));
if (!applied) {
    log.info("binding transition rejected: id={}, expected=ISSUED, actual={}", id, r.get(1));
}
```
{% endraw %}

### 로컬(단일 인스턴스) 구현도 같은 규칙을 지킨다

테스트나 단일 인스턴스용으로 메모리 구현이 따로 있다면 `ConcurrentHashMap.compute`가 같은 역할을 한다. `compute`의 함수 안은 그 키에 대해 원자적이다.

{% raw %}
```java
map.compute(id, (k, cur) -> {
    if (cur == null) return null;
    if (!expected.contains(cur.state())) return cur;   // 거절: 그대로 둔다
    return cur.withState(next);
});
```
{% endraw %}

두 구현의 조건표가 같아야 한다. 테스트는 로컬로 통과하는데 운영(Redis)에서만 되돌림이 나는 상황을 막는 가장 싼 방법은, 조건표를 한 곳(enum 메서드 등)에 두고 두 구현이 그것을 쓰게 하는 것이다.

---

## "먼저 저장한 쪽이 이긴다"는 규칙을 받아들이기

조건부 전이를 넣으면 자연스럽게 **first writer wins**가 된다. 늦게 끝난 쪽은 거절된다. 이 규칙이 업무상 맞는지는 따로 확인해야 했다.

같은 프로젝트의 다른 자리에서는 "정책 평가 결과"와 "timeout 종결"이 경합했다.

- 평가가 늦게 끝나 `ALLOWED`를 먼저 저장하면, 뒤에 오는 `TIMEOUT` 저장은 CAS에서 거절된다.
- 반대로 `TIMEOUT`이 먼저 저장되면 늦은 `ALLOWED`가 거절된다.

처음에는 "timeout이 났는데 ALLOWED가 남는 게 맞나?"가 쟁점이었다. 결론은 세 가지 근거로 **먼저 저장한 쪽이 terminal**로 정했다.

1. 늦게 도착한 `ALLOWED`도 실제 평가 결과다. 거짓 값이 아니다.
2. 두 경로(정상 완료, timeout)가 같은 CAS 계약을 쓰면 어느 쪽이 이겨도 상태가 하나로 수렴한다.
3. `TIMEOUT`이 이기면 fail-closed(차단)다. 안전한 방향으로 틀린다.

규칙을 정하는 것보다 **문서에 명시하는 것**이 더 중요했다. "timeout 뒤에 ALLOWED가 보일 수 있다"는 문장이 없으면 운영에서 버그로 보인다.

---

## TTL도 전이의 일부다

조건부 `SET`에 `EX`를 함께 주기 때문에 TTL 설계가 상태 기계에 얽힌다. 여기서 한 번 더 걸렸다.

- 티켓 TTL은 **발급 시점**부터 시작한다.
- 하지만 파일을 보관하는 쪽은 **파일 등록 시점**(발급보다 뒤)부터 보관 기간을 계산한다.

둘을 같은 값으로 두면, 느린 다운로드에서 티켓이 파일보다 먼저 만료된다. 파일은 아직 있는데 티켓이 없어 재시도가 거부된다. 그래서 `TTL = max(기본 TTL, 보관 기간 + 여유 300초)`로 잡았다. 전이할 때마다 이 TTL을 다시 준다.

---

## 회귀 테스트: 순서를 강제한다

이 결함의 특징은 **독립 상태 저장 테스트로는 절대 잡히지 않는다**는 점이다. "FALLBACK을 저장하면 FALLBACK이 읽힌다"는 테스트는 통과한다. 필요한 것은 순서를 고정한 테스트다.

{% raw %}
```java
@Test
void lateFallbackDoesNotRevertClosed() {
    store.issue(id);                                 // ISSUED
    Binding snapshotT = store.get(id);               // T가 읽어둔 snapshot

    store.transition(id, Set.of("IN_USE_B","ISSUED"), "CLOSED");   // L이 먼저 끝남

    boolean applied = store.transition(id, Set.of("ISSUED"), "FALLBACK");  // T가 늦게 저장 시도

    assertThat(applied).isFalse();
    assertThat(store.get(id).state()).isEqualTo("CLOSED");
}
```
{% endraw %}

Redis 구현은 Testcontainers로 실제 Redis를 띄워 돌렸다. Lua 스크립트는 mock으로 검증할 수 없다. 이 프로젝트에서는 Redis 통합 테스트 17건이 모두 통과한 뒤에야 "조건부 전이가 들어갔다"고 말할 수 있었다.

Redis Cluster를 쓴다면 스크립트의 KEYS가 한 슬롯에 있어야 한다. 이 경우 키가 하나라 문제가 없지만, 두 키를 함께 전이시키려면 hash tag(`{id}`)로 같은 슬롯에 넣어야 한다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 문제 | 읽어둔 snapshot을 무조건 저장해 terminal 상태가 되돌아간다 |
| 막을 것 | 동시 진입이 아니라 **잘못된 전이** |
| Redis | `GET → 기대 상태 비교 → SET EX`를 Lua 한 스크립트로 |
| 로컬 | `ConcurrentHashMap.compute`로 같은 조건표 |
| 규칙 | first writer wins. 늦은 쪽은 거절. 문서에 명시 |
| TTL | 전이마다 다시 부여. 연관 자원의 보관 기간보다 길게 |
| 테스트 | 순서를 강제하는 회귀 테스트 + 실제 Redis |

상태를 "읽고 저장"하는 코드가 있다면, 저장 앞에 "내가 읽은 상태가 아직 그대로인가"라는 조건이 있는지 확인해 볼 만하다. 없다면 그 코드는 언젠가 끝난 일을 되살린다.
