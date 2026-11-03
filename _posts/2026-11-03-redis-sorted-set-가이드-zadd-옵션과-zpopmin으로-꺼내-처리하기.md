---
title: "Redis Sorted Set 가이드: ZADD 옵션과 ZPOPMIN으로 꺼내 처리하기"
date: 2026-11-03 09:00:00 +0900
categories: ["Redis", "가이드"]
tags: ["redis", "zset", "zadd", "zpopmin", "lua"]
permalink: /posts/redis-sorted-set-가이드-zadd-옵션과-zpopmin으로-꺼내-처리하기/
---

## Sorted Set이란

Redis Sorted Set(ZSet)은 멤버와 점수(score)의 쌍을 모은 집합이다.

- **멤버는 중복되지 않는다.** 같은 멤버를 다시 넣으면 점수만 바뀐다.
- **점수 순으로 정렬된다.** 점수가 같으면 멤버 문자열의 사전 순이다.
- **점수는 배정밀도 부동소수점(double)이다.**

"키별 최신 시각", "우선순위 큐", "점수 순위표"처럼 키 하나에 값 하나를 두고 크기 순으로 꺼내야 할 때 쓴다.

이 글의 명령 결과는 모두 Redis 7.2.16 컨테이너에서 직접 실행해 확인했다.

---

## ZADD: 넣기와 갱신하기

{% raw %}
```text
> ZADD z 100 m1 100 m2 100 m0    # 멤버 여러 개를 한 번에
3
> ZRANGE z 0 -1 WITHSCORES        # 점수가 같으면 멤버 사전 순
m0 100
m1 100
m2 100
```
{% endraw %}

반환값은 **새로 추가된 멤버 수**다. 이미 있던 멤버의 점수만 바뀌었으면 0이다. 바뀐 수까지 받으려면 `CH` 옵션을 쓴다.

### 옵션 정리

| 옵션 | 동작 | 버전 |
|---|---|---|
| `NX` | 없을 때만 추가한다. 있는 멤버는 건드리지 않는다 | 3.0.2 |
| `XX` | 있을 때만 갱신한다. 새 멤버는 추가하지 않는다 | 3.0.2 |
| `GT` | 새 점수가 **더 클 때만** 갱신한다. 새 멤버는 추가한다 | 6.2 |
| `LT` | 새 점수가 **더 작을 때만** 갱신한다. 새 멤버는 추가한다 | 6.2 |
| `CH` | 반환값에 "추가 + 점수가 바뀐 수"를 센다 | 3.0.2 |
| `INCR` | 점수를 더한다. `ZINCRBY`와 같고, 새 점수를 반환한다 | 3.0.2 |

실행 결과는 이렇다.

{% raw %}
```text
> ZADD z 100 a
1
> ZADD z GT 50 a        # 50 < 100, 갱신 안 함
0
> ZADD z GT 200 a       # 200 > 100, 갱신함. 하지만 반환은 0 (추가가 아니므로)
0
> ZSCORE z a
200
> ZADD z GT CH 300 a    # CH 를 붙이면 갱신도 센다
1
> ZADD z LT 500 a       # 500 > 300, LT 라서 갱신 안 함
0
> ZADD z XX 5 newone    # 없는 멤버, XX 라서 추가 안 함
0
> ZADD z INCR 5 b       # b 점수 10 에 5 를 더함
15
> ZADD z NX GT 1 c
ERR GT, LT, and/or NX options at the same time are not compatible
```
{% endraw %}

`GT`와 `LT`는 서로, 그리고 `NX`와 함께 쓸 수 없다.

### GT가 필요한 경우: 도착 순서가 바뀔 때

"가장 최근 접속 시각"처럼 **가장 큰 값만 의미 있는** 데이터를 여러 클라이언트가 쓴다고 하자. 일반 `ZADD`는 마지막에 도착한 값이 이긴다.

{% raw %}
```text
클라이언트 A: 시각 t0 을 잡는다 ... (지연) ...
클라이언트 B: 시각 t1 (t1 > t0) 을 잡고 ZADD key t1 m
클라이언트 A: 이제야 ZADD key t0 m      -> 점수가 t1 에서 t0 으로 되돌아간다
```
{% endraw %}

값을 잡는 순서와 Redis에 도착하는 순서는 다를 수 있다. 네트워크 지연, 재시도, 스레드 스케줄링 모두 순서를 바꾼다. `ZADD GT`를 쓰면 도착 순서와 상관없이 결과가 최댓값으로 모인다.

사용하는 클라이언트 라이브러리가 `GT` 옵션을 지원하지 않으면 Lua 한 줄로 실행할 수 있다.

{% raw %}
```lua
-- KEYS[1] = ZSet 키, ARGV[1] = 점수, ARGV[2] = 멤버
return redis.call('ZADD', KEYS[1], 'GT', ARGV[1], ARGV[2])
```
{% endraw %}

{% raw %}
```text
> EVAL "return redis.call('ZADD', KEYS[1], 'GT', ARGV[1], ARGV[2])" 1 e 10 m
1
```
{% endraw %}

키를 하나만 쓰므로 Redis Cluster에서도 문제없다.

### 점수 정밀도: 2^53까지만 정확하다

점수는 double이라 2^53(9007199254740992)을 넘는 정수는 정확히 저장되지 않는다.

{% raw %}
```text
> ZADD f 1700000000123 x       # epoch 밀리초
> ZSCORE f x
1700000000123
> ZADD f 9007199254740993 y    # 2^53 + 1
> ZSCORE f y
9007199254740992
```
{% endraw %}

epoch 밀리초는 여유가 크다. 하지만 64비트 ID나 나노초 시각을 점수로 쓰면 값이 바뀔 수 있다. 그런 값은 멤버에 넣는다.

---

## 조회: ZSCORE, ZRANGE, ZRANK

| 명령 | 용도 |
|---|---|
| `ZSCORE key m` | 멤버 하나의 점수 |
| `ZCARD key` | 멤버 수 |
| `ZRANGE key start stop` | 순위 범위로 조회 |
| `ZRANGE key min max BYSCORE` | 점수 범위로 조회 (6.2부터, `ZRANGEBYSCORE` 대체) |
| `ZRANGE ... REV` | 큰 점수부터 |
| `ZRANGE ... LIMIT offset count` | `BYSCORE`/`BYLEX`와 함께 개수 제한 |
| `ZRANK key m WITHSCORE` | 순위와 점수를 함께 (7.2부터) |

점수 범위 앞에 `(`를 붙이면 그 값을 제외한다. `-inf`, `+inf`로 끝을 열 수 있다.

{% raw %}
```text
> ZRANGE z (100 +inf BYSCORE WITHSCORES             # 100 초과
a 300
> ZRANGE z +inf -inf BYSCORE REV LIMIT 0 2 WITHSCORES  # 큰 점수부터 2개
a  300
m2 100
```
{% endraw %}

`REV`를 쓰면 범위도 큰 값부터 적는다(`+inf -inf`).

---

## 꺼내기: ZPOPMIN, ZPOPMAX, ZMPOP

`ZPOPMIN`은 점수가 가장 작은 멤버를 **꺼내면서 지운다.** 개수를 주면 여러 개를 한 번에 꺼낸다.

{% raw %}
```text
> ZPOPMIN z 2
b  15
m0 100
> ZPOPMAX z
a 300
> ZMPOP 1 z MIN COUNT 2      # 7.0부터. 여러 키 중 처음으로 비어 있지 않은 키에서 꺼낸다
z
m1 100
m2 100
> ZPOPMIN empty 5            # 빈 키는 빈 결과
(empty)
> EXISTS z                   # 마지막 멤버를 꺼내면 키도 사라진다
0
```
{% endraw %}

| 명령 | 버전 | 비고 |
|---|---|---|
| `ZPOPMIN` / `ZPOPMAX` | 5.0 | `count`로 여러 개 |
| `BZPOPMIN` / `BZPOPMAX` | 5.0 | 비어 있으면 타임아웃까지 기다린다 |
| `ZMPOP` / `BZMPOP` | 7.0 | 여러 키 중 하나에서 꺼낸다 |

꺼내기와 지우기가 한 명령이라 원자적이다. 여러 소비자가 동시에 `ZPOPMIN`을 해도 같은 멤버를 두 번 받지 않는다. 그래서 "쌓아 두었다가 주기적으로 묶어서 처리"하는 작업 큐로 쓰기 좋다.

### 꺼낸 뒤 처리가 실패하면 데이터가 사라진다

`ZPOPMIN`에는 처리 완료 확인(ack)이 없다. 꺼낸 순간 Redis에서는 지워진다. 처리하다 예외가 나거나 프로세스가 죽으면 그 항목은 없어진다.

대응은 두 가지다.

1. **실패한 항목을 다시 넣는다.** 이때 `ZADD GT`를 쓴다. 꺼낸 사이에 같은 멤버가 더 큰 점수로 다시 들어왔으면, 옛 점수로 덮지 않는다.
2. **유실이 허용되지 않으면 다른 구조를 쓴다.** `ZRANGE`로 읽고 처리 후 `ZREM`하거나, ack가 있는 Redis Streams를 쓴다. 이때는 같은 항목을 두 번 처리할 수 있으니 처리를 멱등(idempotent, 여러 번 해도 결과가 같음)하게 만든다.

### 되돌릴 때 주의: 바로 다시 넣으면 같은 항목만 돈다

한 번 실행에서 `ZPOPMIN`을 여러 번 반복하는 작업이라면, 실패 항목을 **즉시** 되돌리면 안 된다.

되돌린 항목은 점수가 옛 값이라 다음 `ZPOPMIN`에서 맨 앞에 다시 나온다. 꺼내고, 실패하고, 되돌리고, 다시 꺼낸다. 뒤에 쌓인 새 항목은 처리되지 않는다.

{% raw %}
```java
List<ScoredMember> retry = new ArrayList<>();
try {
    for (int i = 0; i < MAX_BATCHES; i++) {
        List<ScoredMember> batch = redis.popMin(KEY, BATCH_SIZE);
        if (batch.isEmpty()) break;
        retry.addAll(process(batch));   // 처리하지 못한 항목만 돌려받는다
    }
} finally {
    retry.forEach(m -> redis.zaddGt(KEY, m.score(), m.member()));   // 실행이 끝날 때 한꺼번에
}
```
{% endraw %}

실행 한 번 동안 모았다가 `finally`에서 되돌린다. 그리고 무한히 되돌리지 않도록 기준을 둔다. 예를 들어 일정 시간보다 오래된 항목이나, 재시도 횟수를 넘은 항목은 버리고 로그를 남긴다.

---

## 정리

| 하고 싶은 것 | 명령 |
|---|---|
| 넣기, 점수 덮기 | `ZADD key score member` |
| 더 클 때만 갱신 (최신 시각, 최고 점수) | `ZADD key GT score member` |
| 더 작을 때만 갱신 (최초 시각, 최저가) | `ZADD key LT score member` |
| 없을 때만 넣기 | `ZADD key NX score member` |
| 바뀐 수까지 받기 | `ZADD key CH ...` |
| 점수 더하기 | `ZINCRBY` 또는 `ZADD key INCR` |
| 점수 범위 조회 | `ZRANGE key min max BYSCORE [REV] [LIMIT]` |
| 작은 것부터 꺼내 지우기 | `ZPOPMIN key count` |
| 기다렸다 꺼내기 | `BZPOPMIN key timeout` |

주의할 점은 세 가지다.

- `ZADD`의 반환값은 기본적으로 "추가된 수"다. 갱신 여부를 보려면 `CH`를 붙인다.
- 점수는 double이다. 2^53을 넘는 정수는 정확하지 않다.
- `ZPOPMIN`은 꺼내는 순간 지운다. 실패 항목은 `ZADD GT`로 되돌리되, 실행이 끝날 때 한꺼번에 되돌린다.
