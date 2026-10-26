---
title: "Lettuce shareNativeConnection(false)는 장애 대응책이 아니다"
date: 2026-10-26 10:30:00 +0900
categories: ["Redis", "운영"]
tags: ["redis", "lettuce", "spring-data-redis", "커넥션"]
permalink: /posts/lettuce-sharenativeconnection-false는-장애-대응책이-아니다/
---

Spring Data Redis의 `LettuceConnectionFactory`에는 `setShareNativeConnection(false)`라는 옵션이 있다. "끊어진 커넥션을 계속 재사용하다가 장애를 겪는 일을 막겠다"는 의도로 이 값을 꺼 두는 코드를 가끔 본다.

우리 서비스의 Sentinel, Cluster 설정에도 이 옵션이 `false`로 들어 있었다. 같은 조직의 다른 서비스가 **pool 없이 이 옵션을 false로 쓰다가 Redis 지연과 타임아웃을 겪은 사례**를 알게 되어 점검했다. 결론은 "장애 감지가 목적이라면 이 옵션이 아니라 `validateConnection`을 쓴다"였다.

이 글은 두 옵션의 역할 차이와, `false`가 어떤 비용을 만드는지 정리한다.

> 라이브러리 동작은 Spring Data Redis와 Lettuce 버전에 따라 다를 수 있다. 정확한 동작은 사용하는 버전의 문서를 확인한다.

---

## 1. 두 옵션은 역할이 다르다

| 설정 | 하는 일 | 비용 |
|---|---|---|
| `shareNativeConnection` | 네이티브 커넥션 하나를 공유해 재사용할지(`true`, 기본값), `getConnection()`마다 새로 만들지(`false`) 결정 | `false`이고 pool이 없으면 command마다 TCP 연결과 인증을 새로 한다. Cluster면 토폴로지 조회까지 따라온다 |
| `validateConnection` | `getConnection()`을 줄 때마다 공유 커넥션이 살아 있는지 확인하고, 죽었으면 새로 만든다 | 로컬 채널 상태를 보는 확인이라 네트워크 왕복이 없다 |

`false`로 두면 확실히 "끊어진 커넥션을 재사용하는 일"은 없다. 매번 새 커넥션을 만들기 때문이다. 그런데 이것은 **정상 상태에서도 항상 비용을 치르는 방식**이다.

{% raw %}
```text
shareNativeConnection=true  (기본)
  command 1 ─┐
  command 2 ─┼─ 공유 커넥션 1개 재사용
  command 3 ─┘

shareNativeConnection=false, pool 없음
  command 1 ─ 새 TCP + AUTH (+ 토폴로지) ─ 실행 ─ 종료
  command 2 ─ 새 TCP + AUTH (+ 토폴로지) ─ 실행 ─ 종료
  command 3 ─ 새 TCP + AUTH (+ 토폴로지) ─ 실행 ─ 종료
```
{% endraw %}

Redis 호출이 늘어날수록 연결 비용이 그대로 곱해진다. 트래픽이 적을 때는 문제가 보이지 않다가 부하가 올라가면 지연과 타임아웃으로 나타난다.

---

## 2. 장애 감지는 이미 다른 설정이 한다

"공유 커넥션이 끊긴 걸 못 잡는다"는 걱정은 `validateConnection(true)`가 해결한다. 여기에 아래 설정이 함께 있으면 커넥션이 끊긴 순간에도 command가 무한정 기다리지 않는다.

- `autoReconnect = true`: 끊어지면 Lettuce가 재연결을 시도한다.
- `disconnectedBehavior = REJECT_COMMANDS`: 연결이 끊긴 동안 들어온 command를 큐에 쌓지 않고 즉시 실패시킨다.
- 짧은 command timeout: 모드별로 500ms~1000ms를 썼다.

{% raw %}
```java
LettuceConnectionFactory factory = new LettuceConnectionFactory(sentinelConfig, clientConfig);
factory.setValidateConnection(true);
// setShareNativeConnection(false)는 호출하지 않는다 (기본값 true)

ClientOptions options = ClientOptions.builder()
        .autoReconnect(true)
        .disconnectedBehavior(ClientOptions.DisconnectedBehavior.REJECT_COMMANDS)
        .build();

LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
        .clientOptions(options)
        .commandTimeout(Duration.ofMillis(500))
        .build();
```
{% endraw %}

`false`가 주려던 효과, 즉 끊긴 커넥션 때문에 장애가 길어지지 않게 하는 것은 위 조합이 이미 제공하고 있었다. 그래서 `false`는 얻는 것이 없고 매 command의 재연결 비용만 추가하고 있었다.

---

## 3. 어떻게 판단했나

변경 전에 다음 순서로 확인했다.

1. 코드에서 blocking command(`BLPOP` 등), `MULTI/EXEC` 트랜잭션, 수동 pipeline 사용이 있는지 grep으로 확인했다. 없었다.
2. 사용 패턴은 단순한 `get`, `set`, `expire`, `scan`, sorted set 연산이었다.
3. `validateConnection`, `autoReconnect`, `REJECT_COMMANDS`, 짧은 command timeout이 이미 설정되어 있는지 확인했다. 모두 있었다.

세 조건이 맞으면 `shareNativeConnection` 오버라이드를 지워서 기본값(공유)으로 돌린다. 변경은 설정 두 줄(Sentinel, Cluster 각 한 줄)과 그 옆의 주석 정리였다. Standalone 설정은 원래 이 옵션을 건드리지 않아 변경하지 않았다.

---

## 4. pooling은 왜 도입하지 않았나

대안으로 `false`를 유지하고 `LettucePoolingClientConfiguration`(commons-pool2)을 도입하는 방법도 검토했다. 비채택한 이유는 다음과 같다.

- 의존성이 하나 늘고, pool 크기(`max-active`, `max-idle`)를 모드별로 튜닝해야 한다.
- `validateConnection`을 pool과 함께 쓰면 borrow마다 검증 비용이 겹칠 수 있다.
- 지금 코드에는 커넥션 격리가 필요한 blocking command, 트랜잭션, pipeline이 없다. 격리의 실질적인 이득이 없었다.

반대로 아무것도 바꾸지 않고 모니터링만 강화하는 안도 비채택했다. 다른 서비스가 같은 설정으로 이미 문제를 겪었는데, 같은 패턴을 그대로 두는 것은 재현 가능성을 알면서 방치하는 것이기 때문이다.

---

## 5. `false`가 필요한 경우와 한계

이 판단은 모든 경우에 적용되지 않는다.

| 상황 | 판단 |
|---|---|
| 단순 get/set 위주, 위 장애 감지 설정이 모두 있음 | `shareNativeConnection` 기본값(공유) 유지 |
| blocking command, `MULTI/EXEC`, 대량 pipeline 사용 | 커넥션 격리가 필요할 수 있다. `false`와 pooling을 함께 검토한다 |
| `validateConnection`, `autoReconnect`, command timeout 중 하나라도 없음 | 위 설정을 먼저 갖춘 뒤 다시 판단한다 |
| pool 없이 `false`만 사용 | 항상 피한다 |

`validateConnection`에는 한계도 있다. 로컬 채널 상태만 보기 때문에, **TCP는 열려 있지만 상대가 응답하지 않는 zombie 상태**는 잡지 못한다. 방화벽이 조용히 연결을 끊거나 상대 노드가 멈춘 경우가 그렇다. 이 한계는 `shareNativeConnection(false)`로도 해결되지 않는다. 새 커넥션을 맺은 뒤 상대가 죽으면 똑같이 못 잡는다. zombie 연결이 걱정된다면 command timeout을 짧게 유지하고, 필요하면 TCP keepalive 같은 소켓 옵션을 검토한다. 이 부분은 이번 변경 범위 밖이었다.

---

## 6. 정리

- `shareNativeConnection`은 **커넥션을 공유할지** 정하는 옵션이다. 장애 감지 옵션이 아니다.
- 끊긴 공유 커넥션을 감지하는 것은 `validateConnection(true)`의 역할이고, 로컬 확인이라 저렴하다.
- `autoReconnect`, `REJECT_COMMANDS`, 짧은 command timeout을 함께 두면 fail-fast가 된다.
- pool 없는 `shareNativeConnection(false)`는 정상 상태에서도 command마다 연결 비용이 든다.
- blocking command, 트랜잭션, pipeline을 쓰지 않는지 먼저 확인한다. 쓴다면 pooling을 같이 검토한다.
- zombie 연결은 두 방식 모두 완벽히 잡지 못한다.

체크리스트로 줄이면 다음과 같다.

- [ ] `setShareNativeConnection(false)`가 pool 없이 쓰이고 있지 않은가
- [ ] 장애 감지 목적이라면 `validateConnection(true)`가 켜져 있는가
- [ ] `autoReconnect`, `REJECT_COMMANDS`, command timeout이 설정되어 있는가
- [ ] blocking command, `MULTI/EXEC`, pipeline 사용 여부를 grep으로 확인했는가

이 변경의 효과는 Cluster, Sentinel 환경에 배포한 뒤 지연과 타임아웃 지표로 확인해야 한다. 로컬에는 해당 구성이 없어 이번에는 컴파일 확인까지만 했고, 실제 개선 폭은 측정하지 못했다.
