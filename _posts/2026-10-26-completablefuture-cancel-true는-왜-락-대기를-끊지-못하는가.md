---
title: "CompletableFuture.cancel(true)는 왜 락 대기를 끊지 못하는가"
date: 2026-10-26 09:20:00 +0900
categories: ["Java", "문법"]
tags: ["java", "completablefuture", "동시성", "timeout", "cas"]
permalink: /posts/completablefuture-cancel-true는-왜-락-대기를-끊지-못하는가/
---

## 50ms timeout인데 300ms 뒤에도 응답하지 않았다

외부 시스템 판정이 오래 걸릴 수 있는 작업에 timeout을 걸었다. 코드는 흔한 형태였다.

{% raw %}
```java
public CheckResult evaluateWithTimeout(String key) {
    CompletableFuture<CheckResult> future =
            CompletableFuture.supplyAsync(() -> evaluate(key), executor);
    try {
        return future.get(50, TimeUnit.MILLISECONDS);
    } catch (TimeoutException e) {
        future.cancel(true);              // worker를 멈췄다고 생각했다
        return saveTimeoutError(key);     // timeout 결과를 저장하고 반환
    }
}
```
{% endraw %}

단위 테스트는 통과했다. 그런데 리뷰 중에 실제 서비스 메서드로 재현해 보니 이상한 결과가 나왔다.

- timeout 예산은 50ms였다.
- 300ms가 지나도 호출자는 반환하지 못하고 `BLOCKED` 상태였다.
- worker를 풀어 주자 총 370ms 뒤에 반환했다.
- 저장된 결과는 timeout 에러가 아니라 **늦게 끝난 정상 결과**였다.

기존 테스트는 worker를 실제로 실행하지 않는 mock 기반이라 이 경우를 잡지 못했다. 이 글은 왜 이런 일이 생기는지, 그리고 어떻게 고쳤는지를 정리한다.

---

## 원인 1. `CompletableFuture.cancel(true)`는 interrupt하지 않는다

`Future.cancel(boolean mayInterruptIfRunning)`의 인자는 "실행 중인 스레드를 interrupt할지"를 뜻한다. 하지만 `CompletableFuture`는 이 인자를 **무시한다.** JDK 문서에도 이 구현에서는 interrupt로 처리를 제어하지 않으므로 값이 영향을 주지 않는다고 적혀 있다.

`CompletableFuture.cancel`이 하는 일은 하나다. **future를 `CancellationException`으로 완료 상태로 만드는 것**이다. `supplyAsync`로 이미 실행 중인 람다는 계속 돈다.

{% raw %}
```java
CompletableFuture<String> f = CompletableFuture.supplyAsync(() -> {
    try {
        Thread.sleep(1_000);
        System.out.println("worker 계속 실행 중이었다");
    } catch (InterruptedException e) {
        System.out.println("interrupt 받음");   // 출력되지 않는다
    }
    return "done";
});

Thread.sleep(100);
f.cancel(true);
System.out.println(f.isCancelled());            // true
Thread.sleep(1_200);                            // "worker 계속 실행 중이었다"가 출력된다
```
{% endraw %}

`ExecutorService.submit()`이 돌려주는 `FutureTask`는 다르다. `FutureTask.cancel(true)`는 worker 스레드에 실제로 `interrupt()`를 건다. 그래서 "executor 종류를 바꾸면 해결되지 않을까"라는 의문이 생길 수 있다. 다음 절에서 보듯이 그것만으로는 충분하지 않다.

---

## 원인 2. interrupt가 있어도 락 대기는 안 풀린다

worker가 락을 쥐고 오래 일하는 구조였다고 하자. timeout 처리도 같은 락을 잡는다.

{% raw %}
```java
private CheckResult evaluate(String key) {
    synchronized (lockFor(key)) {          // worker가 락을 잡고 느린 평가를 한다
        CheckResult d = slowEvaluate(key);
        store.save(key, d);
        return d;
    }
}

private CheckResult saveTimeoutError(String key) {
    synchronized (lockFor(key)) {          // timeout 처리도 같은 락을 기다린다
        store.save(key, CheckResult.error("TIMEOUT"));
        return CheckResult.error("TIMEOUT");
    }
}
```
{% endraw %}

흐름은 이렇다.

{% raw %}
```text
t=0ms    worker: 락 획득, slowEvaluate 시작
t=50ms   호출자: TimeoutException, cancel(true) (아무 일도 안 함)
t=50ms   호출자: saveTimeoutError → 같은 락을 기다림 (BLOCKED)
...
t=370ms  worker: 평가 끝, ALLOWED 저장, 락 해제
t=370ms  호출자: 락 획득, TIMEOUT 저장 시도
```
{% endraw %}

결과적으로 두 가지가 동시에 깨진다.

1. **응답 상한이 무너진다.** timeout 예산 50ms가 의미 없어지고, 호출자는 worker가 끝날 때까지 기다린다.
2. **결과가 뒤집힌다.** worker의 정상 결과가 먼저 저장되고, timeout 에러는 뒤에 저장되거나 거절된다. 사용자는 timeout이라는 응답을 받았는데 저장소에는 늦은 성공이 남을 수 있다.

`FutureTask.cancel(true)`로 interrupt를 걸어도 `synchronized` 블록 진입 대기와 `ReentrantLock.lock()`은 interrupt에 반응하지 않는다. 반응하려면 `lockInterruptibly()`나 `tryLock(timeout)`을 써야 하고, worker 내부의 `slowEvaluate`도 interrupt를 존중해야 한다. 즉 **interrupt는 협력 방식**이다. 받는 쪽 코드가 응답하도록 짜여 있지 않으면 아무 효과가 없다.

---

## 해결: timeout 저장은 락과 분리하고, 늦은 완료는 CAS로 거절한다

해결 방향은 두 가지를 분리하는 것이다.

1. **timeout 처리 경로는 worker가 쥔 락을 기다리지 않는다.**
2. **늦게 끝난 worker가 timeout 결과를 덮어쓰지 못하게 저장소에서 막는다.**

### 상태 전이를 저장소가 판정하게 한다

평가를 시작할 때 `PENDING` 상태를 sequence와 함께 기록한다. 이후 어떤 경로든 **PENDING인 같은 sequence일 때만** 최종 결과를 저장할 수 있게 한다. 먼저 저장한 쪽이 이기고, 나중에 온 쪽은 CAS 실패로 거절된다.

{% raw %}
```java
public final class CheckResultStore {

    record Entry(long sequence, Status status, CheckResult decision) {}

    private final ConcurrentMap<String, Entry> map = new ConcurrentHashMap<>();

    public long begin(String key) {
        return map.merge(key, new Entry(1, Status.PENDING, null),
                (old, ignored) -> new Entry(old.sequence() + 1, Status.PENDING, null))
                .sequence();
    }

    /** PENDING이고 sequence가 같을 때만 최종 결과를 저장한다. */
    public boolean complete(String key, long sequence, CheckResult decision) {
        boolean[] won = {false};
        map.computeIfPresent(key, (k, cur) -> {
            if (cur.status() == Status.PENDING && cur.sequence() == sequence) {
                won[0] = true;
                return new Entry(sequence, Status.DONE, decision);
            }
            return cur;
        });
        return won[0];
    }
}
```
{% endraw %}

### timeout 경로는 락 없이 CAS만 쓴다

{% raw %}
```java
public CheckResult evaluateWithTimeout(String key) {
    long seq = store.begin(key);
    CompletableFuture<CheckResult> future =
            CompletableFuture.supplyAsync(() -> evaluate(key, seq), executor);
    try {
        return future.get(50, TimeUnit.MILLISECONDS);
    } catch (TimeoutException e) {
        future.cancel(true);
        CheckResult timeout = CheckResult.error("TIMEOUT");
        // 락을 잡지 않는다. CAS에 성공해야 timeout이 최종 결과가 된다.
        return store.complete(key, seq, timeout) ? timeout : store.get(key).decision();
    }
}

private CheckResult evaluate(String key, long seq) {
    synchronized (lockFor(key)) {
        CheckResult d = slowEvaluate(key);
        // 늦게 끝났으면 이미 TIMEOUT이 저장되어 있어 CAS가 실패한다.
        store.complete(key, seq, d);
        return d;
    }
}
```
{% endraw %}

이제 같은 시나리오는 이렇게 흐른다.

{% raw %}
```text
t=0ms    worker: 락 획득, 평가 시작
t=50ms   호출자: TimeoutException → 락 없이 TIMEOUT 저장 (CAS 성공) → 즉시 반환
t=370ms  worker: 평가 끝, complete(seq) 시도 → 이미 DONE이라 CAS 실패 (결과 버림)
```
{% endraw %}

운영 환경이 여러 서버라면 JVM 락(`synchronized`, `ReentrantLock`)은 서버 사이를 막지 못한다. 같은 CAS 조건을 Redis Lua 스크립트나 DB 조건부 `UPDATE ... WHERE status='PENDING' AND sequence=?`로 구현하면 된다. 락은 "한 프로세스 안의 평가 순서" 용도로만 두고, **최종 상태 판정은 저장소가 한다**는 원칙이다.

---

## 회귀 테스트는 worker를 실제로 막아서 만든다

기존 테스트가 놓친 이유는 worker가 실행되지 않았기 때문이다. 이 결함을 잡으려면 worker를 `CountDownLatch`로 멈춰 둔 채 호출자를 실행해야 한다.

{% raw %}
```java
@Test
void timeoutDoesNotWaitForRunningWorker() throws Exception {
    CountDownLatch workerStarted = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    when(evaluator.slowEvaluate(any())).thenAnswer(inv -> {
        workerStarted.countDown();
        release.await();                       // worker를 락 안에서 붙잡아 둔다
        return CheckResult.allowed();
    });

    // 실제 단일 스레드 executor, 200ms 예산
    CheckResult result = assertTimeoutPreemptively(Duration.ofSeconds(5),
            () -> service.evaluateWithTimeout("k"));

    assertTrue(workerStarted.await(1, TimeUnit.SECONDS));
    assertEquals("TIMEOUT", result.reason());  // release 전에 TIMEOUT이 저장되어야 한다

    release.countDown();                       // 이제 늦은 worker를 풀어 준다
    // 늦은 ALLOWED는 CAS에 거절되어 저장 결과가 TIMEOUT으로 유지되어야 한다
    awaitIdle(executor);
    assertEquals("TIMEOUT", store.get("k").decision().reason());
}
```
{% endraw %}

검증 항목은 세 가지다.

- worker가 락을 쥔 상태에서도 호출자가 예산 안에 반환한다.
- 반환 시점의 저장 결과가 TIMEOUT이다.
- worker가 늦게 끝나도 저장 결과가 바뀌지 않는다.

---

## 정리

| 오해 | 실제 |
|---|---|
| `cancel(true)`로 worker가 멈춘다 | `CompletableFuture`는 인자를 무시하고 future만 완료시킨다 |
| `FutureTask`면 interrupt가 된다 | 맞다. 하지만 `synchronized`/`lock()` 대기는 interrupt에 반응하지 않는다 |
| timeout 예산이 지켜진다 | timeout 처리가 worker의 락을 기다리면 예산이 무의미해진다 |
| 늦은 결과는 버려진다 | 막지 않으면 늦은 성공이 timeout 결과를 대체할 수 있다 |

체크리스트로 줄이면 다음과 같다.

- timeout 이후 경로가 worker가 쥔 락을 기다리지 않는지 확인한다.
- 최종 상태 저장은 `PENDING + sequence` 같은 CAS 조건으로 한 번만 성공하게 한다.
- 취소를 정말 전파해야 한다면 worker가 `lockInterruptibly()`, `tryLock(timeout)`, 인터럽트 확인 같은 협력 지점을 갖게 한다.
- timeout 테스트는 mock이 아니라 실제 executor와 `CountDownLatch`로 worker를 붙잡아 놓고 만든다.
