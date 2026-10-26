---
title: "Redis 캐시 backfill이 최신 값을 덮어쓸 때"
date: 2026-10-26 09:30:00 +0900
categories: ["Redis", "운영"]
tags: ["redis", "lua", "동시성", "캐시", "테스트"]
permalink: /posts/redis-캐시-backfill이-최신-값을-덮어쓸-때/
---

## 캐시가 비어 있어서 채웠을 뿐인데 옛 값이 들어갔다

여러 서버가 같이 쓰는 구조에서, 원본 저장소에 있는 값을 Redis에 복사해 두는 "mirror"를 운영하고 있었다. 사용자의 토큰 같은 값을 서버 메모리 대신 Redis hash에 두고, 어느 서버든 Redis를 먼저 읽는다.

배포 직후에는 기존 연결들의 mirror가 비어 있다. 그래서 읽기 경로에 이런 보정(backfill)을 넣었다.

> mirror에 값이 없으면 원본에서 읽고, 읽은 값을 mirror에 채워 둔다.

의도는 좋았다. 한 번 채워지면 다음부터는 Redis만 읽으면 된다. 그런데 코드 리뷰에서 이 보정이 **새로 저장된 최신 값을 옛 값으로 되돌릴 수 있다**는 지적이 나왔다.

---

## 문제 시나리오

코드는 대략 이런 형태였다.

{% raw %}
```java
public String resolveSessionToken(String sessionId) {
    Optional<String> cached = mirror.read(sessionId);
    if (cached.isPresent()) {
        return cached.get();                  // mirror hit: 원본은 다시 보지 않는다
    }
    String token = source.read(sessionId); // 원본 조회 (느릴 수 있다)
    mirror.write(sessionId, token);        // backfill: 무조건 HSET
    return token;
}
```
{% endraw %}

그리고 mirror에 쓰는 Lua는 이랬다.

{% raw %}
```lua
if redis.call('EXISTS', KEYS[1]) == 0 then
  return 0
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[2])
return 1
```
{% endraw %}

"hash가 있을 때만 쓴다"는 조건은 있지만, **필드에 이미 어떤 값이 있는지는 보지 않는다.** 여기서 경쟁이 생긴다.

{% raw %}
```text
시각  요청 X (읽기)                         요청 Y (갱신)
t1    mirror miss
t2    원본에서 토큰 A 조회 (지연 중)
t3                                           클라이언트가 새 토큰 B 전송
t4                                           원본에 B 저장 + mirror에 B 저장
t5    backfill: mirror ← A  (덮어씀)
t6    이후 모든 요청: mirror hit → A 반환
```
{% endraw %}

t5에서 mirror가 옛 값 A로 되돌아간다. 이후 요청은 mirror hit 경로로 바로 반환하므로 **원본에 있는 B를 읽지 않는다.**

토큰 A가 곧 만료되는 값이라면, 정상적으로 갱신한 연결도 만료된 토큰 때문에 인증에 실패한다. 이 상태는 다음 갱신이 오거나 key가 삭제될 때까지 이어진다.

### "경쟁 창이 짧으니 괜찮다"는 판단이 틀린 이유

처음 설계 문서에는 이렇게 적어 두었다.

> mirror가 비어 있을 때만 쓰므로 창이 짧다. 옛 값도 만료 전에는 유효하고 다음 갱신이 덮는다.

리뷰에서 반박이 나왔다. **창이 짧아도 영향은 짧지 않다.** 한 번 잘못 들어간 값은 mirror hit 경로 때문에 아무도 다시 검증하지 않고, 다음 갱신이 언제 올지도 알 수 없다. 경쟁이 일어날 확률과 일어났을 때의 지속 시간은 별개의 문제다.

---

## 해결 방법 비교

핵심은 **"권한 있는 갱신(set)"과 "보정(backfill)"을 구분하는 것**이다.

- 갱신: 새 값을 안다는 근거가 있으므로 무조건 덮어써도 된다.
- backfill: 이미 값이 있으면 쓰면 안 된다. 쓰더라도 내가 읽은 시점 이후 바뀌지 않았을 때만 써야 한다.

### 방법 1. `HSETNX`로 필드가 없을 때만 쓴다

{% raw %}
```lua
-- backfill 전용 스크립트: hash가 있고, 이 필드가 비어 있을 때만 쓴다
if redis.call('EXISTS', KEYS[1]) == 0 then
  return 0
end
return redis.call('HSETNX', KEYS[1], ARGV[1], ARGV[2])
```
{% endraw %}

- `HSETNX`는 필드가 없을 때만 쓰고 성공 여부를 돌려준다.
- 위 시나리오에서는 t4에서 이미 B가 들어 있으므로 t5의 backfill이 아무것도 하지 않는다.
- 주의할 점이 있다. `HSETNX`만 단독으로 쓰면 hash가 없을 때 새로 만들어 버린다. 연결 정보 없이 값만 있는 hash가 생기는 것을 막으려면 위처럼 `EXISTS` 확인을 같이 해야 한다.
- 별도 Lua가 필요 없는 상황이면 `EXISTS` 후 `HSETNX`를 명령 두 개로 보내도 되지만, 두 명령 사이에 key가 지워질 수 있다. 원자성이 필요하면 Lua로 묶는다.

### 방법 2. 값에 버전을 붙여 CAS로 쓴다

필드에 값과 함께 sequence(또는 갱신 시각)를 저장하고, backfill은 **조회 시점에 본 버전과 같을 때만** 쓴다.

{% raw %}
```lua
-- ARGV[1]=field, ARGV[2]=새 값, ARGV[3]=내가 읽었던 버전(없었다면 빈 문자열)
local cur = redis.call('HGET', KEYS[1], ARGV[1] .. ':version') or ''
if cur ~= ARGV[3] then
  return 0
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[2], ARGV[1] .. ':version', ARGV[4])
return 1
```
{% endraw %}

- 필드가 비어 있는 경우만이 아니라 "값은 있지만 더 오래된 경우"도 다룰 수 있다.
- 대신 모든 쓰기 경로가 버전을 함께 관리해야 한다. 변경 범위가 커진다.

### 두 방법 비교

| 항목 | 단순 `HSET` | `HSETNX` | 버전 CAS |
|---|---|---|---|
| 새 값 보호 | 안 됨 | 됨 | 됨 |
| 옛 값이 이미 들어 있을 때 교정 | 덮어씀 | 교정 안 함 | 버전 비교로 가능 |
| 구현 비용 | 가장 작음 | 작음 | 모든 쓰기 경로 수정 |
| backfill 용도 | 부적합 | 적합 | 적합 |

backfill 목적이 "비어 있는 곳을 채우는 것"이라면 `HSETNX` 정도가 가장 작은 변경이다. 갱신 경로(set)는 그대로 무조건 `HSET`을 유지한다. 이렇게 하면 두 경로가 서로 다른 스크립트를 갖게 되어 의도가 이름에서 드러난다.

---

## 회귀 테스트: latch로 조회를 멈추고 순서를 강제한다

이 경쟁은 일반 단위 테스트에서 재현되지 않는다. "mirror miss일 때 backfill을 호출했는가"와 "mirror hit일 때 호출하지 않았는가"를 따로 검증하는 테스트는 있었지만, **조회가 느려서 갱신이 중간에 끼는 순서**는 없었다. 테스트가 순서를 직접 만들어야 한다.

{% raw %}
```java
@Test
void backfillDoesNotOverwriteNewerValue() throws Exception {
    CountDownLatch readStarted = new CountDownLatch(1);
    CountDownLatch releaseRead = new CountDownLatch(1);

    // 원본 조회를 일부러 멈춘다. 멈추기 전에 옛 값 A를 읽은 상태가 된다.
    when(source.read("sess-1")).thenAnswer(inv -> {
        String old = "token-A";
        readStarted.countDown();
        releaseRead.await();
        return old;
    });

    ExecutorService pool = Executors.newSingleThreadExecutor();
    Future<String> reader = pool.submit(() -> service.resolveSessionToken("sess-1"));

    assertTrue(readStarted.await(2, TimeUnit.SECONDS));

    // 읽기가 멈춘 사이에 권한 있는 갱신이 새 값을 저장한다.
    service.storeSessionToken("sess-1", "token-B");     // 원본 + mirror 모두 B

    releaseRead.countDown();                     // 이제 멈춘 읽기가 backfill을 시도한다
    reader.get(2, TimeUnit.SECONDS);

    // mirror는 B로 유지되어야 한다.
    assertEquals("token-B", mirror.read("sess-1").orElseThrow());
    pool.shutdownNow();
}
```
{% endraw %}

테스트 구조의 핵심은 세 가지다.

1. `readStarted`로 읽기 스레드가 **옛 값을 이미 들고 있는 시점**까지 기다린다.
2. 그 사이에 갱신을 끝낸다.
3. `releaseRead`로 읽기를 풀어 backfill이 **마지막에** 실행되게 한다.

단순 `HSET` 구현에서는 이 테스트가 실패하고, `HSETNX` 구현에서는 통과한다. Redis 동작 자체를 보려면 Redis 통합 테스트(Testcontainers 등)에서 실제 Lua를 실행해 본다.

---

## 정리

| 구분 | 내용 |
|---|---|
| 문제 | 오래 걸린 조회 결과를 무조건 `HSET`으로 backfill하면 그 사이 저장된 새 값을 덮는다 |
| 영향 | mirror hit 경로가 원본을 다시 읽지 않아 옛 값이 오래 남는다 |
| 오해 | 경쟁 창이 짧다고 영향도 짧은 것은 아니다 |
| 해결 | 갱신과 backfill을 구분하고, backfill은 `HSETNX` 또는 버전 CAS로 쓴다 |
| 주의 | `HSETNX` 단독은 hash를 새로 만든다. 필요하면 `EXISTS`와 Lua로 묶는다 |
| 테스트 | latch로 조회를 멈추고, 새 값 저장 뒤에 backfill을 완료시켜 새 값 보존을 확인한다 |

캐시를 채우는 코드는 "빈 곳만 채운다"는 약속을 가져야 한다. 읽은 시점의 값이 쓰는 시점에도 최신이라고 가정하는 순간, 읽기와 쓰기 사이의 시간이 곧 경쟁 창이 된다.
