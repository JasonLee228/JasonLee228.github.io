---
title: "Redis SCAN으로 인한 부하 폭증 원인과 개선"
parent: "Spring-Boot"
nav_order: 18
permalink: "/notes/redis-scan으로-인한-부하-폭증-원인과-개선/"
---

## Redis SCAN 때문에 발생한 부하 폭증 정리

Redis 부하가 급격히 증가했다는 제보가 있었다. 확인해보니 특정 시간대에 Redis에서 `SCAN MATCH` 명령이 짧은 시간 동안 매우 많이 실행되고 있었다.

제보된 패턴은 대략 아래와 같았다.

- `SCAN MATCH "app:user:sessions:*"` 호출이 수 초 사이 수만 회 발생

- `SCAN MATCH "app:session:user:*"` 호출도 같은 시간대에 수만 회 발생

- 로그에는 Redis command timeout 류의 경고가 함께 나타남

처음에는 실제 세션 수가 많아서 발생한 문제처럼 보였지만, 확인해보니 실제 결과 수는 많지 않았다. 문제는 결과 수가 아니라 **그 결과를 계산하기 위해 Redis 전체 키 공간을 반복해서 훑는 구조**였다.

---

## 어떤 상황이었나

세션 연결/해제 이벤트가 짧은 시간에 몰리는 상황이 있었다. 이때 로그를 찍기 위해 전체 사용자 수, 전체 세션 수 같은 값을 매번 계산하고 있었다.

예를 들면 이런 형태다.

{% raw %}
```java
log.info("connected: sessionId={}, userSessions={}, totalUsers={}, totalSessions={}",
        sessionId,
        getUserSessionCount(userId),
        getTotalUserCount(),
        getTotalSessionCount());
```
{% endraw %}

여기서 `totalSessions` 값 자체는 8~10 정도로 작게 나왔다. 그런데 이 숫자를 구하는 과정이 문제였다.

{% raw %}
```java
Set<String> keys = cacheService.getKeys("app:session:user:*");
return keys.size();
```
{% endraw %}

즉, Redis 입장에서는 `totalSessions=8`이라는 숫자를 바로 알고 있는 것이 아니다. `app:session:user:*`에 맞는 키가 몇 개인지 알기 위해 키 공간을 순회해야 한다.

---

## Redis SCAN은 어떻게 동작하나

`SCAN`은 Redis 키를 cursor 기반으로 조금씩 순회하는 명령이다.

{% raw %}
```text
SCAN 0 MATCH app:session:user:* COUNT 1000
```
{% endraw %}

여기서 중요한 점은 `MATCH`가 데이터베이스 인덱스 조건처럼 동작하지 않는다는 것이다.

Redis는 내부 키 공간을 순회하면서 각 키가 패턴에 맞는지 확인한다. 그래서 매칭 결과가 8개뿐이어도, Redis 안에 다른 키가 많다면 여러 번의 순회가 필요할 수 있다.

또한 `COUNT`도 결과 개수 제한이 아니다. 한 번의 SCAN에서 어느 정도 훑어볼지에 대한 힌트에 가깝다.

정리하면 다음과 같다.

- `SCAN`은 한 번에 전체를 막아버리는 `KEYS`보다 안전한 방식이다.

- 하지만 결국 전체 키 공간을 나누어 순회하는 명령이다.

- `MATCH`는 순회 대상을 줄이는 인덱스가 아니다.

- `COUNT`는 반환 개수 제한이 아니라 탐색량 힌트다.

- cursor가 다시 `0`이 될 때까지 반복해야 전체 순회가 끝난다.

그래서 `SCAN MATCH`를 요청 경로나 이벤트 경로에서 계속 호출하면, 매칭 결과가 적어도 Redis에는 부담이 된다.

---

## 왜 부하가 커졌나

문제는 다음 두 가지가 겹친 것이다.

1. 연결/해제 이벤트가 짧은 시간에 많이 발생했다.

1. 이벤트마다 전체 카운트를 계산하기 위해 `SCAN MATCH`가 실행됐다.

예를 들어 1초에 연결/해제 이벤트가 100번 발생하고, 이벤트마다 전체 사용자 수와 전체 세션 수를 각각 계산하면 Redis에는 전체 패턴 SCAN이 200번 발생할 수 있다.

실제 결과가 몇 건인지와 별개로, Redis는 매번 패턴에 맞는 키를 찾기 위해 키 공간을 순회한다. 이 과정이 누적되면서 Redis command timeout이 발생했고, 애플리케이션의 세션 정리 흐름에도 부수적인 문제가 생길 수 있었다.

---

## 어떻게 처리했나

먼저 이벤트 경로에서 전체 카운트 계산을 제거했다.

연결/해제 로그에서 전체 사용자 수, 전체 세션 수처럼 Redis 전체 키 공간을 훑어야 하는 값은 빼고, 현재 이벤트 처리에 이미 필요한 값만 남겼다.

예를 들면 다음과 같은 방향이다.

{% raw %}
```java
log.info("connected: sessionId={}, userSessions={}",
        sessionId,
        getUserSessionCount(userId));
```
{% endraw %}

특정 사용자 세션 수처럼 하나의 Set 크기만 보는 값은 전체 키 공간을 훑지 않기 때문에 상대적으로 비용이 작다.

그리고 주기적으로 세션을 정리하는 유지보수 작업에서는 전체 사용자 목록 조회가 필요할 수 있으므로, 다음 기준으로 정리했다.

- 같은 전체 조회를 여러 번 반복하지 않는다.

- 한 번 조회한 사용자 목록은 정리 작업과 TTL 갱신 작업에서 재사용한다.

- 유지보수성 조회에만 `COUNT` 힌트를 적용해 SCAN 라운드트립을 줄인다.

## COUNT 옵션에 대한 오해

`COUNT`를 넣으면 문제가 완전히 사라지는 것은 아니다.

{% raw %}
```text
SCAN 0 MATCH app:user:sessions:* COUNT 1000
```
{% endraw %}

`COUNT 1000`은 “1000개만 가져오고 끝”이라는 뜻이 아니다. Redis에게 “이번 cursor 순회에서 이 정도를 훑어봐 달라”는 힌트다.

따라서 `COUNT`는 이벤트 경로에서 반복 호출되는 `SCAN` 문제의 근본 해결책이 아니다. 이벤트 경로에서는 `SCAN` 자체를 제거하는 것이 우선이고, `COUNT`는 주기적 유지보수처럼 어쩔 수 없이 전체 조회가 필요한 곳에서 라운드트립을 줄이는 보조 수단으로 보는 것이 맞다.

## 정리

이번 문제는 세션 수가 많아서 발생한 것이 아니라, 작은 숫자를 구하기 위해 이벤트마다 Redis 전체 키 공간을 반복해서 훑은 것이 원인이었다.

Redis `SCAN`은 `KEYS`보다 안전하지만, 공짜는 아니다. 특히 `MATCH` 패턴을 붙여도 인덱스를 타고 바로 찾는 것이 아니라 전체 키를 순회하면서 필터링한다.

따라서 실시간 요청/이벤트 경로에서는 `SCAN MATCH` 기반 전체 카운트 계산을 피해야 한다. 전체 통계가 필요하다면 별도의 카운터나 Set 인덱스를 두고 정합성까지 함께 설계하는 편이 낫다.
