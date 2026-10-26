---
title: "ThreadPoolTaskExecutor에서 max를 올려도 빨라지지 않는 이유"
date: 2026-10-26 10:40:00 +0900
categories: ["Spring", "운영"]
tags: ["threadpool", "executor", "spring", "동시성"]
permalink: /posts/threadpooltaskexecutor에서-max를-올려도-빨라지지-않는-이유/
---

비동기 작업이 자꾸 타임아웃으로 끝나는 서비스가 있었다. 해당 작업용 executor는 `core=2, max=8, queue=200`이었다. 처음에는 "max가 8이라 부족한가 보다"라고 생각하기 쉽다.

로그를 보면 이야기가 달랐다. **큐 거절(reject)은 0건이었는데 타임아웃은 150건**이었다. 작업은 큐에 잘 들어갔지만 응답 예산(약 3초) 안에 실행되지 못한 것이다.

이 글은 `ThreadPoolTaskExecutor`가 스레드를 늘리는 순서와, 이 순서 때문에 max만 올려서는 소용이 없는 이유, 그리고 pool 분리까지 정리한다.

---

## 1. 스레드가 늘어나는 순서

`ThreadPoolTaskExecutor`는 내부적으로 `ThreadPoolExecutor`를 쓴다. 새 작업이 들어왔을 때의 처리 순서는 다음과 같다.

{% raw %}
```text
1. 현재 스레드 수 < core        → 새 스레드를 만들어 바로 실행
2. core가 모두 사용 중          → 큐(queue)에 넣는다
3. 큐도 가득 참                 → max까지 스레드를 추가한다
4. max도 가득 참 + 큐도 가득 참 → reject (RejectedExecutionHandler)
```
{% endraw %}

많은 사람이 놓치는 부분은 2번과 3번의 순서다. **max는 큐가 가득 찬 뒤에야 열린다.**

그래서 `core=2, max=8, queue=200`이면 이렇게 동작한다.

- 평소에는 스레드가 2개뿐이다.
- 작업이 몰리면 큐에 최대 200개가 쌓인다. 이 동안 스레드는 여전히 2개다.
- 201번째 작업부터 스레드가 8개까지 늘어난다.

큐가 200칸인 한, max를 8에서 80으로 올려도 평소 처리량은 바뀌지 않는다. 큐가 차기 전까지는 max가 쓰이지 않기 때문이다.

---

## 2. 우리 상황에 대입해 보기

executor가 처리하는 작업은 대부분 외부 호출을 기다리는 I/O 작업이었다. 한 건에 200ms 안팎이 걸렸다. 사용자 약 100명이 동시에 쓰고, 한 요청이 3단계의 작업을 만든다고 가정하면 대략 이런 계산이 나온다.

{% raw %}
```text
200ms × 100명 × 3단계 / 8 worker ≈ 7.5초
```
{% endraw %}

이 식은 worker가 8개일 때다. 현실에서는 큐가 차기 전까지 worker가 core인 2개이므로 지연은 더 커진다. 응답 예산이 약 3초인 구조에서는 큐에 들어갔다는 것이 곧 늦는다는 뜻이다.

reject가 0건이었던 이유도 설명된다. 큐 200칸이 꽤 크기 때문에 거절은 일어나지 않았고, 대신 기다리다 timeout이 났다. **reject 로그가 없다고 pool이 충분하다는 뜻은 아니다.**

---

## 3. 해결 1: core를 올리고 core = max로 둔다

큐가 차기 전에 필요한 병렬도가 있다면 core를 그 값으로 올려야 한다. blocking I/O가 많은 작업이라 CPU 코어 수 기반 공식은 맞지 않는다. 일반적으로 대기 시간 비율이 높을수록 스레드 수를 더 크게 잡는다.

{% raw %}
```text
적정 스레드 수 ≈ CPU 코어 수 × (1 + 대기 시간 / 계산 시간)
```
{% endraw %}

이번에는 주문 검증용 pool을 `core=32, max=32, queue=200`으로 바꿨다. 도달 시점의 의미가 달라진다.

| 구성 | 평소 worker | 큐가 차면 |
|---|---|---|
| `2 / 8 / 200` | 2 | 8까지 증가 |
| `32 / 32 / 200` | 32 | 증가 없음, 이후 reject |

core와 max를 같게 둔 이유는 두 가지다.

- 정상 상태의 처리량은 core가 담당한다. 큐가 찬 시점은 이미 장애 상태다.
- 장애 중에 max를 더 열면 하류(외부 API, Redis, DB)로 부하를 더 밀어낸다. 상한이 고정되어 있는 편이 하류를 보호한다.

그래서 `32 / 64 / 200` 같은 구성은 채택하지 않았다. 추가 32개는 큐가 가득 찬 장애 순간에만 열리는데, 그때 하류에 부하를 더하는 쪽이다.

---

## 4. 해결 2: reject는 AbortPolicy로 둔다

큐와 max가 모두 찼을 때의 정책도 중요하다. `ThreadPoolExecutor`의 기본 정책은 다음과 같다.

| 정책 | 동작 | 위험 |
|---|---|---|
| `AbortPolicy` | `RejectedExecutionException`을 던진다 | 호출자가 처리해야 한다 |
| `CallerRunsPolicy` | 제출한 스레드가 직접 실행한다 | 요청 스레드가 느린 작업에 묶인다 |
| `DiscardPolicy` | 조용히 버린다 | 작업 유실 |

여기서는 `AbortPolicy`를 유지했다. 실패를 호출부에서 알 수 있어서, 기존의 fail-open, fail-closed 정책에 따라 처리를 이어갈 수 있다. `CallerRunsPolicy`는 요청 스레드로 부하가 번지므로 쓰지 않았다.

{% raw %}
```java
private ThreadPoolTaskExecutor newBoundedExecutor(int core, int max, int queue, String prefix) {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(core);
    executor.setMaxPoolSize(max);
    executor.setQueueCapacity(queue);
    executor.setThreadNamePrefix(prefix);
    executor.setKeepAliveSeconds(30);
    executor.setAllowCoreThreadTimeOut(true);
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
    executor.setWaitForTasksToCompleteOnShutdown(true);
    executor.setAwaitTerminationSeconds(30);
    return executor;
}
```
{% endraw %}

`setAllowCoreThreadTimeOut(true)`이면 유휴 core 스레드도 keepAlive 이후 정리된다. 그래서 `core=32`여도 평소 스레드가 항상 32개 떠 있는 것은 아니다. 필요할 때 만들어지고 한가하면 줄어든다.

---

## 5. 해결 3: 장애가 번지지 않게 pool을 나눈다

pool 크기만 올리면 해결되지 않는 문제가 하나 더 있었다. 이 pool에는 성격이 다른 작업이 섞여 있었다.

- 주문 상태 조회와 주문 검증: 짧고 예산이 빠듯한 작업
- 상품 정보 조회/저장: 외부 RPC. 장애가 나면 timeout까지 worker를 점유한다

상품 정보 RPC가 느려지면 그 작업들이 worker를 오래 잡고, 같은 pool을 쓰는 주문 검증 작업도 큐에서 기다리게 된다. **한 종류의 장애가 다른 경로의 지연으로 번진다.**

그래서 pool을 둘로 나눴다.

| pool | core / max / queue | 용도 |
|---|---|---|
| 검증 pool | 32 / 32 / 200 | 주문 검증, 상태 기반 검증 |
| 상품 정보 pool | 16 / 16 / 200 | 외부 상품 정보 조회, 저장 |

분리의 목표는 상품 정보 호출의 성공률을 높이는 것이 아니다. **상품 정보에 문제가 생겨도 주문 검증 worker를 지키는 것**이다.

---

## 6. 두 pool이 서로 기다리지 않게 한다

pool을 나눌 때 흔한 실수가 있다. A pool의 작업이 B pool의 작업을 `Future.get()`으로 기다리면, 부하가 걸릴 때 서로의 worker를 잡고 교착에 가까운 상태가 된다.

이번에는 단계를 연결하는 방식으로 풀었다. 이전 단계가 **다음 단계를 제출하고 바로 반환**한다.

{% raw %}
```java
catalogExecutor.execute(() -> {
    try {
        CatalogItem item = fetchCatalog(request);          // 외부 RPC
        validationExecutor.execute(() -> validate(item)); // 제출만 하고 즉시 반환
    } catch (Exception e) {
        markFailed(request);                            // 실패 시 대기 상태를 종결
    }
});
```
{% endraw %}

이 구조에서 catalog worker는 주문 검증 결과를 기다리지 않는다. 어느 단계가 reject되거나 실패하더라도 **대기 중이던 상태를 오류로 종결**하도록 해서, 요청이 영원히 대기 상태로 남지 않게 했다.

---

## 7. 설정을 외부화할 때

값을 코드에 박아 두면 조정할 때마다 재빌드가 필요하다. 이후 core, max, queue를 설정으로 빼고 환경 변수로 덮어쓸 수 있게 했다. 이때 정한 규칙은 다음과 같다.

- 환경 변수가 없으면 기본값(`32/32/200`, `16/16/200`)이 그대로 동작한다.
- `core > max`이면 기동을 실패시키지 않고 큰 값으로 맞춘 뒤 경고 로그를 남긴다. `core < max`는 허용한다.
- `0` 이하의 값은 바인딩 단계에서 실패시킨다.
- reject 정책과 스레드 이름 prefix는 설정으로 열지 않는다. 계약이기 때문이다.

설정 실수로 배포가 죽는 일을 줄이면서도, 말이 안 되는 값은 일찍 실패시키는 균형이다.

---

## 8. 정리

| 오해 | 실제 |
|---|---|
| max를 올리면 처리량이 늘어난다 | 큐가 가득 찬 뒤에야 max가 열린다 |
| reject가 없으면 pool이 충분하다 | 큐에서 기다리다 timeout이 날 수 있다 |
| 큰 pool이면 장애에 강하다 | 하류에 부하를 더하고, 느린 작업이 다른 작업을 막을 수 있다 |
| `CallerRunsPolicy`가 안전하다 | 요청 스레드가 느린 작업에 묶인다 |

pool을 조정할 때의 체크리스트는 다음과 같다.

- [ ] 큐가 차기 전의 병렬도(core)가 필요한 만큼인가
- [ ] core = max로 상한을 고정할지 판단했는가
- [ ] 큐 크기가 응답 예산에 비해 너무 크지 않은가 (큐에 쌓인 작업은 예산을 갉아먹는다)
- [ ] reject 시 호출부가 어떻게 동작하는지 정했는가
- [ ] 성격이 다른 작업(짧은 검증, 느린 외부 호출)이 같은 pool을 쓰고 있지 않은가
- [ ] pool 사이에 `Future.get()` 대기가 없는가

한계도 적어 둔다. 이 변경의 효과는 배포 후 타임아웃 건수, active worker 수, 큐 길이, 하류 오류를 변경 전후로 비교해야 확인할 수 있다. 이 글을 쓰는 시점에는 운영 검증이 끝나지 않았다. 또한 `32`와 `16`은 하류 용량을 충분히 검증해서 정한 값이 아니다. 부하 시나리오와 기존 timeout 로그를 근거로 정한 초기값이므로 모니터링 결과를 보고 조정해야 한다.
