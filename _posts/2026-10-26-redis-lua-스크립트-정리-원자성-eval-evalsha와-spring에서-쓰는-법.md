---
title: "Redis Lua 스크립트 정리: 원자성, EVAL/EVALSHA와 Spring에서 쓰는 법"
date: 2026-10-26 09:35:00 +0900
categories: ["Redis", "운영"]
tags: ["redis", "lua", "동시성", "spring"]
permalink: /posts/redis-lua-스크립트-정리-원자성-eval-evalsha와-spring에서-쓰는-법/
---

Redis 명령 하나하나는 원자적이다. `INCR`을 두 클라이언트가 동시에 실행해도 값이 꼬이지 않는다. 문제는 **여러 명령을 묶어서 "읽고, 판단하고, 쓰는"** 순간이다.

{% raw %}
```text
클라이언트 A: GET lock:order-1   → "token-A"
클라이언트 B: SET lock:order-1 "token-B"   (A의 락이 만료되어 B가 획득)
클라이언트 A: DEL lock:order-1   → B의 락을 지워 버림
```
{% endraw %}

A는 "내 락이면 지운다"를 하고 싶었지만, `GET`과 `DEL` 사이에 다른 클라이언트가 끼어들었다. 이렇게 **조건 확인과 변경 사이의 틈**을 없애는 가장 흔한 방법이 Lua 스크립트다.

## Lua 스크립트가 원자적인 이유

Redis는 명령을 하나의 스레드에서 순서대로 처리한다. Lua 스크립트도 **명령 하나처럼** 실행된다. 스크립트가 도는 동안 다른 클라이언트의 명령은 실행되지 않고 기다린다.

그래서 위의 락 해제는 이렇게 쓴다.

{% raw %}
```lua
-- KEYS[1]: 락 키, ARGV[1]: 내 토큰
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
```
{% endraw %}

`GET`과 `DEL` 사이에 아무도 끼어들 수 없으므로, 내 토큰일 때만 지운다는 조건이 항상 지켜진다.

### 원자적이지만 롤백은 없다

여기서 자주 오해하는 부분이 있다. Lua 스크립트의 원자성은 **"중간에 다른 명령이 끼어들지 않는다"**는 뜻이지, **"실패하면 되돌린다"**는 뜻이 아니다.

{% raw %}
```lua
redis.call('SET', KEYS[1], 'a')
redis.call('INCR', KEYS[2])   -- KEYS[2]가 문자열이면 여기서 에러
redis.call('SET', KEYS[3], 'c')
```
{% endraw %}

두 번째 줄에서 에러가 나면 스크립트는 멈추지만, 첫 번째 `SET`은 이미 반영된 상태로 남는다. 그래서 스크립트는 **쓰기 전에 필요한 검사를 먼저 다 하고, 마지막에 쓰는** 순서로 작성하는 것이 좋다.

## 기본 사용법: EVAL

{% raw %}
```text
EVAL <script> <numkeys> <key1> ... <keyN> <arg1> ... <argM>
```
{% endraw %}

{% raw %}
```bash
redis-cli EVAL "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0" 1 lock:order-1 token-A
```
{% endraw %}

- `numkeys`는 뒤에 오는 인자 중 몇 개가 **키**인지 알려 준다.
- 스크립트 안에서는 `KEYS[1]`, `ARGV[1]`처럼 꺼내 쓴다. Lua 배열은 **1부터** 시작한다.
- 키와 일반 인자를 나누는 이유는 뒤에서 볼 Redis Cluster 때문이다. **스크립트가 건드리는 키는 반드시 `KEYS`로 넘긴다.**

### redis.call과 redis.pcall

| 함수 | 명령이 에러를 내면 |
|---|---|
| `redis.call` | 스크립트 전체가 에러로 끝나고, 클라이언트가 에러를 받는다. |
| `redis.pcall` | 에러를 Lua 테이블(`{err = "..."}`)로 돌려준다. 스크립트가 직접 처리할 수 있다. |

대부분은 `redis.call`을 쓰고, 에러를 스크립트 안에서 처리해야 할 때만 `pcall`을 쓴다.

### 반환값 변환

Lua 값은 Redis 응답 타입으로 바뀌어 돌아온다. 몇 가지는 직관과 다르다.

| Lua 값 | 클라이언트가 받는 값 |
|---|---|
| 숫자 `3.7` | 정수 `3` (소수점이 버려진다) |
| 문자열 | 문자열 |
| `true` | 정수 `1` |
| `false` | nil |
| 테이블(배열) | 배열. 단 중간에 `nil`이 있으면 거기서 잘린다 |

소수를 돌려줘야 하면 `tostring()`으로 문자열을 만들어 반환한다.

## EVALSHA와 스크립트 캐시

매번 스크립트 전문을 보내는 것은 낭비다. Redis는 실행한 스크립트를 **SHA1 해시로 캐시**한다.

{% raw %}
```bash
# 스크립트를 등록하고 SHA1을 받는다
redis-cli SCRIPT LOAD "return redis.call('GET', KEYS[1])"
# "a42059b356c875f0717db19a51f6aaca9ae659ea"

# 이후에는 해시로 실행한다
redis-cli EVALSHA a42059b356c875f0717db19a51f6aaca9ae659ea 1 lock:order-1
```
{% endraw %}

주의할 점이 있다.

- 스크립트 캐시는 영구 저장소가 아니다. Redis 재시작, 장애 조치(failover), `SCRIPT FLUSH` 뒤에는 비어 있다.
- 캐시에 없으면 `NOSCRIPT` 에러가 난다. 클라이언트는 이때 `EVAL`로 전문을 보내 다시 실행해야 한다.
- 해시는 **스크립트 문자열 그대로**로 계산된다. 공백이나 줄바꿈 하나만 달라도 다른 스크립트가 된다.

## 오래 걸리는 스크립트는 Redis 전체를 멈춘다

스크립트가 실행되는 동안 다른 명령은 모두 기다린다. 이것이 원자성의 대가다.

- 큰 키를 전부 순회하거나, 루프 안에서 수천 번 명령을 호출하는 스크립트는 그동안 Redis 전체를 멈춘다.
- 기본 시간 제한(약 5초)을 넘기면 다른 클라이언트는 `BUSY` 에러를 받기 시작한다. 이 제한은 스크립트를 멈추지 않는다. 다른 클라이언트에게 알려 줄 뿐이다.
- 아직 아무것도 쓰지 않은 스크립트는 `SCRIPT KILL`로 멈출 수 있다. 이미 쓰기를 한 스크립트는 원자성을 깨므로 멈출 수 없고, 서버를 내리는 방법밖에 없다.

그래서 Lua 스크립트는 **짧게, 키 몇 개만 다루도록** 쓴다. `KEYS *`나 `SCAN` 전체 순회를 스크립트에 넣지 않는다.

## Redis Cluster에서 쓸 때

Cluster는 키를 해시 슬롯으로 나눠 여러 노드에 저장한다. 스크립트는 한 노드에서 실행되므로, **스크립트가 다루는 키는 모두 같은 슬롯에 있어야 한다.** 그렇지 않으면 `CROSSSLOT` 에러가 난다.

{% raw %}
```text
order:{1001}:status
order:{1001}:items
```
{% endraw %}

키 이름에 `{...}`(hash tag)를 넣으면 중괄호 안의 값만으로 슬롯이 정해진다. 위 두 키는 같은 슬롯에 들어가므로 한 스크립트에서 같이 다룰 수 있다.

또 하나, **스크립트 안에서 키 이름을 조립하지 않는다.**

{% raw %}
```lua
-- 나쁜 예: Cluster가 이 키를 미리 알 수 없다
local key = 'order:' .. ARGV[1] .. ':status'
redis.call('GET', key)
```
{% endraw %}

클라이언트와 Cluster는 `KEYS`로 넘어온 키를 보고 어느 노드로 보낼지 정한다. 스크립트 안에서 만든 키는 이 계산에서 빠지므로, 단일 노드에서는 동작하다가 Cluster로 옮기면 깨진다.

## MULTI/EXEC와 무엇이 다른가

Redis 트랜잭션(`MULTI`/`EXEC`)도 여러 명령을 묶어 끼어들기 없이 실행한다. 차이는 **중간 결과로 판단할 수 있느냐**다.

| | MULTI/EXEC | Lua 스크립트 |
|---|---|---|
| 끼어들기 없음 | 예 | 예 |
| 앞 명령 결과를 보고 분기 | 불가능. 결과는 `EXEC` 뒤에 한꺼번에 나온다 | 가능 |
| 실패 시 롤백 | 없음 | 없음 |
| 낙관적 잠금 | `WATCH`로 가능 | 필요 없음 |

"값이 X면 Y를 한다"처럼 조건이 들어가면 Lua가 훨씬 단순하다. `MULTI`로 하려면 `WATCH` 후 재시도 루프를 써야 한다.

Redis 7부터는 스크립트를 이름으로 등록해 두고 부르는 **Functions**(`FUNCTION LOAD`, `FCALL`)도 있다. 스크립트 캐시와 달리 영속되고 복제된다. 쓸 수 있는 버전이라면 검토할 만하다.

## Spring Data Redis에서 쓰기

Spring Data Redis는 `RedisScript`로 스크립트를 감싸고 `RedisTemplate.execute`로 실행한다.

{% raw %}
```java
@Component
public class OrderLockRepository {

    private static final RedisScript<Long> RELEASE_SCRIPT = RedisScript.of("""
            if redis.call('GET', KEYS[1]) == ARGV[1] then
              return redis.call('DEL', KEYS[1])
            end
            return 0
            """, Long.class);

    private final StringRedisTemplate redisTemplate;

    public OrderLockRepository(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public boolean release(String orderId, String token) {
        Long deleted = redisTemplate.execute(
                RELEASE_SCRIPT,
                List.of("lock:order:" + orderId),   // KEYS
                token);                              // ARGV
        return deleted != null && deleted == 1L;
    }
}
```
{% endraw %}

- `execute`는 먼저 `EVALSHA`로 실행하고, `NOSCRIPT`가 나면 `EVAL`로 다시 보낸다. 재시작 뒤 캐시가 비어도 신경 쓸 필요가 없다.
- 결과 타입은 `Long`, `Boolean`, `List`, `String` 중에서 스크립트 반환값에 맞게 고른다. Lua 정수는 `Long`으로 받는다.
- 스크립트 객체는 **한 번 만들어 재사용**한다. SHA1 계산을 매번 하지 않도록 상수나 빈으로 둔다.
- 템플릿의 직렬화 방식에 따라 `ARGV` 값이 그대로 문자열로 가지 않을 수 있다. 문자열 비교를 하는 스크립트라면 `StringRedisTemplate`을 쓰는 편이 안전하다.

스크립트가 길어지면 Java 문자열 대신 `.lua` 리소스 파일로 빼서 관리할 수 있다. 이때 지켜야 할 점은 [다음 글](/posts/redis-lua-스크립트를-파일로-빼면서-지킨-것들/)에 정리했다.

## 테스트

Lua 스크립트는 Redis 서버 안에서 실행되므로, 모킹으로는 의미 있는 검증이 어렵다. Testcontainers로 실제 Redis를 띄우고 스크립트를 실행해 보는 것이 가장 확실하다.

{% raw %}
```java
@SpringBootTest
@Testcontainers
class OrderLockRepositoryTest {

    @Container
    @ServiceConnection
    static GenericContainer<?> redis = new GenericContainer<>("redis:7.4").withExposedPorts(6379);

    @Autowired OrderLockRepository repository;
    @Autowired StringRedisTemplate redisTemplate;

    @Test
    void releasesOnlyWhenTokenMatches() {
        redisTemplate.opsForValue().set("lock:order:1", "token-B");

        assertThat(repository.release("1", "token-A")).isFalse();
        assertThat(redisTemplate.hasKey("lock:order:1")).isTrue();

        assertThat(repository.release("1", "token-B")).isTrue();
        assertThat(redisTemplate.hasKey("lock:order:1")).isFalse();
    }
}
```
{% endraw %}

## 정리

| 항목 | 기억할 점 |
|---|---|
| 원자성 | 실행 중 다른 명령이 끼어들지 않는다 |
| 롤백 | 없다. 검사를 먼저 하고 쓰기는 마지막에 |
| 인자 | 키는 `KEYS`, 나머지는 `ARGV`. 1부터 시작 |
| 반환 | Lua 숫자는 정수로 잘린다. 소수는 문자열로 |
| EVALSHA | 캐시는 재시작하면 사라진다. `NOSCRIPT`면 `EVAL`로 재시도 |
| 실행 시간 | 길면 Redis 전체가 멈춘다. 짧게 쓴다 |
| Cluster | 모든 키를 같은 슬롯에. 키는 스크립트 밖에서 만들어 `KEYS`로 |
| Spring | `RedisScript`를 재사용하고 `RedisTemplate.execute`로 실행 |

시간 제한 기본값, 복제 방식, Functions 지원 여부는 Redis 버전에 따라 다를 수 있으니, 운영 중인 버전의 문서를 함께 확인하는 것이 좋다.
