---
title: "setIfAbsent의 false를 믿으면 안 되는 이유: 중복 방지 계약 설계"
date: 2026-10-26 11:00:00 +0900
categories: ["Redis", "운영"]
tags: ["redis", "멱등성", "분산락", "fail-open"]
permalink: /posts/setifabsent의-false를-믿으면-안-되는-이유-중복-방지-계약-설계/
---

Redis의 `SET key value NX EX ttl`은 중복 방지와 간단한 분산 락에 자주 쓰인다. Spring Data Redis에서는 `setIfAbsent(key, value, ttl)`이다. 반환값은 단순하다. 키를 새로 만들었으면 `true`, 이미 있었으면 `false`다.

문제는 코드에서 **`false`가 두 가지 뜻으로 쓰일 때** 생긴다. 이 글은 `false`가 "이미 처리됨"과 "Redis 장애"를 동시에 의미하게 되면 어떤 일이 벌어지는지, 그리고 이 계약을 어떻게 정리했는지 다룬다.

---

## 1. 문제가 된 구현

캐시 서비스의 `setIfAbsent`는 이런 모양이었다.

{% raw %}
```java
public boolean setIfAbsent(String key, String value, Duration ttl) {
    try {
        Boolean ok = redisTemplate.opsForValue().setIfAbsent(key, value, ttl);
        return Boolean.TRUE.equals(ok);
    } catch (Exception e) {
        log.warn("setIfAbsent failed: {}", key, e);
        return false;       // 예외를 삼키고 false
    }
}
```
{% endraw %}

호출부 입장에서 `false`를 받으면 두 가지 중 무엇인지 알 수 없다.

| 상황 | 의미 |
|---|---|
| 정상 중복 | 키가 이미 있다. 다른 곳에서 이미 처리했다 |
| Redis 장애 | 키가 있는지조차 모른다. 아무도 처리하지 않았을 수 있다 |

이 두 상황의 올바른 대응은 서로 다르다. 그런데 계약이 하나로 합쳐져 있어서 호출부가 정책을 고를 수 없었다.

---

## 2. 같은 false에서 두 가지 사고가 난다

이 계약이 실제로 두 방향의 문제를 만들었다.

### 2.1 장애를 중복으로 오해해 작업이 누락된다

`false`를 "다른 곳이 이미 처리했다"고 해석해 건너뛰는 코드는, Redis가 죽었을 때도 건너뛴다. 아무도 처리하지 않았는데 처리된 것으로 간주한다. 외부 리소스를 재생성하는 재시도 작업이라면 **재시도가 조용히 멈춘다.**

### 2.2 중복 방지를 포기해서 중복이 생긴다

반대로 감사 로그 전송은 유실을 피하려고 `false`여도 전송하도록 만들어 뒀다. 이 서비스는 같은 이벤트를 **모든 인스턴스가 받는 구조**(인스턴스마다 익명 큐를 구독)였다. 정상 Redis에서도 첫 인스턴스만 `true`를 받고 나머지는 `false`를 받는다. `false`에도 전송하면 인스턴스 수만큼 같은 로그가 중복으로 나간다.

{% raw %}
```text
이벤트 ─┬─ 인스턴스 1: setIfAbsent → true   → 전송
        ├─ 인스턴스 2: setIfAbsent → false  → (그래도 전송)  ← 중복
        └─ 인스턴스 3: setIfAbsent → false  → (그래도 전송)  ← 중복
```
{% endraw %}

한 계약에서 한쪽은 누락, 다른 쪽은 중복이 나온다. 원인은 같다.

---

## 3. 계약을 세 가지 결과로 나눈다

해결의 핵심은 결과를 구분하는 것이다. 새 반환 타입을 만들 수도 있다(`ACQUIRED`, `DUPLICATE`, `UNAVAILABLE` 같은 enum). 이번에는 변경 범위를 줄이려고 기존 `boolean` 의미를 유지하면서 **장애를 예외로 전파**하는 방식을 택했다.

| 결과 | 표현 | 의미 |
|---|---|---|
| 획득 | `true` | 이 호출이 키를 만들었다. 작업 진행 |
| 정상 중복 | `false` | 이미 처리됨(또는 처리 중). 건너뜀 |
| 장애 | 예외 | 상태를 모른다. 호출부 정책에 따른다 |

{% raw %}
```java
public boolean setIfAbsent(String key, String value, Duration ttl) {
    try {
        return Boolean.TRUE.equals(
                redisTemplate.opsForValue().setIfAbsent(key, value, ttl));
    } catch (Exception e) {
        throw new IllegalStateException("redis setIfAbsent failed: " + key, e);   // 삼키지 않는다
    }
}
```
{% endraw %}

enum 방식이 더 명확한 것은 사실이다. 하지만 사용처가 몇 곳뿐인 상황에서 인터페이스까지 넓히는 변경은 과하다고 판단했다. 사용처가 늘어나면 enum으로 올리는 것을 다시 검토할 만하다.

---

## 4. Redis를 쓰지 않는 환경은 어떻게 표현하나

이 서비스는 Redis를 선택적으로 쓴다. Redis가 꺼진 환경에서는 no-op 캐시 구현(`NoOpCacheService`)이 같은 인터페이스를 제공한다. 기존에는 이 구현의 `setIfAbsent`가 항상 `false`를 반환했다.

이것도 위험했다. Redis 미사용 환경이 "이미 처리됨"처럼 보이기 때문이다. 기존 코드는 `instanceof NoOpCacheService`로 이 경우를 따로 우회하고 있었지만, 새 호출부가 이 사실을 모르면 작업을 건너뛴다.

그래서 no-op 구현이 `true`를 반환하게 바꿨다.

{% raw %}
```java
// Redis 미사용: 분산 중복 방지가 불가능하므로 락 없이 진행을 허용한다
@Override
public boolean setIfAbsent(String key, String value, Duration ttl) {
    return true;
}
```
{% endraw %}

이 `true`는 "락을 획득했다"가 아니라 "락 없이 진행해도 좋다"라는 뜻이다. 인터페이스 주석에 이 의미를 남겨야 한다. 호출부에서는 `instanceof` 분기를 지울 수 있다.

단점도 분명하다. 인스턴스가 여러 개이고 Redis가 꺼져 있으면 중복 방지가 되지 않는다. 이것은 반환값 변경으로 새로 생긴 문제가 아니다. Redis 없는 환경의 본질적 제약이다. 중복 방지가 필수인 환경은 Redis 사용을 전제로 해야 한다.

---

## 5. 소비처별로 장애 정책을 정한다

계약을 나눴으면 호출부가 정책을 고른다. 같은 `setIfAbsent`를 쓰지만 소비처마다 장애 시 올바른 선택이 다르다.

| 소비처 | `true` | `false` | 예외(장애) | 이유 |
|---|---|---|---|---|
| 감사 로그 전송 | 전송 | 건너뜀 | **전송 (fail-open)** | 로그 유실이 중복보다 나쁘다 |
| 외부 리소스 재생성 | 재시도 진행 | 건너뜀 | **건너뜀 (fail-closed)** | 중복 생성이 지연보다 나쁘다 |
| Redis 미사용 | 진행 (no-op이 `true` 반환) | - | - | 중복 방지 불가, 기존 동작 유지 |

판단 기준은 "틀렸을 때 비용이 더 큰 쪽"이다. 로그는 두 번 남아도 해가 작지만 빠지면 감사 추적이 끊긴다. 외부 리소스는 두 번 만들면 정리가 어렵지만 재시도가 늦어지는 것은 다음 주기에 복구된다.

{% raw %}
```java
// 감사 로그: 장애는 fail-open
boolean acquired;
try {
    acquired = cache.setIfAbsent(key, token, ttl);
} catch (RuntimeException e) {
    log.error("idempotency check failed, send anyway: {}", key, e);
    acquired = true;            // 키를 못 잡았지만 전송은 한다
}
if (acquired) send(logs);
```
{% endraw %}

{% raw %}
```java
// 외부 리소스 재생성: 장애는 fail-closed
try {
    if (!cache.setIfAbsent(lockKey, token, Duration.ofSeconds(90))) {
        return;                 // 다른 흐름이 처리 중
    }
} catch (RuntimeException e) {
    log.error("lock state unknown, skip retry: {}", lockKey, e);
    return;                     // 상태를 모르면 만들지 않는다
}
retryCreate();
```
{% endraw %}

fail-closed로 건너뛴 재시도는 실패 기록이 남아 있으므로 Redis가 복구된 뒤 다음 주기에 다시 처리된다. 대신 복구 전까지 자동 복구가 늦어진다. 그래서 건너뛴 사실을 로그로 남겨야 한다.

---

## 6. 로그와 키 정리

작은 규칙 두 가지도 정했다.

- **로그에 키와 맥락을 남긴다.** 중복으로 건너뛰는 경우와 장애로 건너뛰거나 강행하는 경우 모두, 대상 식별자와 키를 포함한다. 운영자가 "왜 이 건이 안 나갔는지"를 추적할 수 있어야 한다. 이번에는 이 로그들을 error 레벨로 남겼다. 정상 중복이 반복되면 노이즈가 커질 수 있어서, 필요하면 레이트 제한이나 지표로 분리하는 후속 개선을 염두에 뒀다.
- **전송에 실패하면 선점한 키를 되돌린다.** 키를 먼저 선점하고 전송이 실패하면, 키가 남아 있어 다음 시도가 "이미 처리됨"으로 건너뛰어 버린다. 선점한 키는 실패 시 삭제하는 것이 안전하다. 장애로 fail-open 전송한 경우는 선점한 키가 없으므로 되돌릴 키도 없다.

---

## 7. 더 나아가기: 락 전용 서비스로 분리

`setIfAbsent`가 캐시 서비스 인터페이스에 있으면 캐시, 자료구조, 락이 한 곳에 섞인다. 호출부가 키 생성, 토큰 생성, 예외 해석을 직접 한다.

이를 `DistributedLockService` 같은 업무 락 전용 인터페이스로 분리하는 안도 설계했다. 구현체를 둘로 나누는 구조다.

| 구현체 | 동작 |
|---|---|
| Redis 기반 | `setIfAbsent` 결과로 판단, 예외는 호출부 정책에 맡김 |
| No-op | 항상 획득 성공(Redis 미사용 시) |

Redisson 같은 라이브러리를 도입할 경우 호출부 변경을 줄이는 효과가 있다. 다만 현재 사용처가 두 곳뿐이므로 바로 큰 구조를 도입하지 않고 계약 정비를 먼저 했다. 이 분리를 실제로 적용했는지는 이 글에서 확인하지 못했다.

---

## 8. 정리

- `false`가 "이미 처리됨"과 "장애"를 함께 의미하면 어느 쪽 정책도 맞지 않는다.
- 결과를 `획득 / 정상 중복 / 장애` 세 가지로 구분한다. 장애는 예외로 전파한다.
- Redis를 쓰지 않는 구현은 `true`(락 없이 진행)로 두고, 그 의미를 주석에 남긴다.
- 소비처마다 장애 시 fail-open과 fail-closed를 고른다. 기준은 틀렸을 때의 비용이다.
- 키를 선점한 뒤 작업이 실패하면 키를 되돌린다.
- 판단에 필요한 식별자와 키를 로그에 남긴다.

체크리스트는 다음과 같다.

- [ ] `setIfAbsent`가 예외를 삼켜 `false`로 바꾸고 있지 않은가
- [ ] 호출부가 `false`와 예외를 구분해서 처리하는가
- [ ] 이 작업은 누락이 나쁜가, 중복이 나쁜가 (fail-open인가 fail-closed인가)
- [ ] Redis가 꺼진 환경에서 `setIfAbsent`가 어떤 값을 돌려주는가
- [ ] 선점한 키가 작업 실패 후에도 남아 다음 시도를 막지 않는가
- [ ] TTL이 작업 소요 시간보다 충분히 긴가 (분산 락이라면 해제 시 토큰 비교도 필요하다)

이 방식에는 한계가 있다. `setIfAbsent` 한 번은 락이 아니라 **TTL이 있는 중복 방지 표식**이다. 작업이 TTL보다 오래 걸리면 다른 흐름이 같은 키를 얻을 수 있다. 엄격한 상호 배제가 필요하면 토큰 비교 해제나 락 갱신 같은 별도 설계가 필요하다.
