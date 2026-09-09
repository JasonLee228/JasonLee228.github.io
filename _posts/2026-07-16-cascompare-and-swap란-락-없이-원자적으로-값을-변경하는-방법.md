---
title: "CAS(Compare-And-Swap)란? — 락 없이 원자적으로 값을 변경하는 방법"
date: 2026-07-16 04:21:18 +0000
categories: ["개발지식", "동시성"]
tags: ["동시성", "개발지식"]
permalink: /posts/cascompare-and-swap란-락-없이-원자적으로-값을-변경하는-방법/
---

CAS(Compare-And-Swap)는 멀티스레드 환경에서 **현재 값이 예상한 값과 같을 때만 새 값으로 변경하는 원자적 연산**이다.

Java의 `AtomicInteger`, `AtomicLong`, `AtomicReference` 같은 클래스가 내부적으로 활용하는 핵심 메커니즘이며, 락을 직접 획득하지 않고도 동시성 문제를 해결할 때 사용된다.

> 핵심 흐름은 **비교 → 조건부 변경 → 실패 시 재시도**다.

### 1. 왜 CAS가 필요한가?

다음과 같은 코드가 있다고 가정해 보자.

{% raw %}
```java
int count = 0;
count++;
```
{% endraw %}

`count++`는 코드상 한 줄이지만 실제로는 다음 단계로 나뉜다.

1. 현재 `count` 값을 읽는다.

1. 읽은 값에 1을 더한다.

1. 계산 결과를 다시 `count`에 저장한다.

두 스레드가 동시에 실행하면 둘 다 같은 값을 읽을 수 있다.

{% raw %}
```text
초기값: count = 0

Thread A: count를 읽음 → 0
Thread B: count를 읽음 → 0
Thread A: 1을 저장
Thread B: 1을 저장

기대 결과: 2
실제 결과: 1
```
{% endraw %}

이처럼 한 스레드의 변경 결과가 다른 스레드에 의해 덮어써지는 현상을 **Lost Update(갱신 손실)**라고 한다.

### 2. CAS의 기본 동작

CAS 연산은 일반적으로 다음 세 값을 사용한다.

- 메모리에 저장된 현재 값

- 호출자가 예상한 값(Expected Value)

- 변경하려는 새 값(New Value)

개념적으로는 다음과 같다.

{% raw %}
```text
CAS(메모리 위치, 예상값, 새 값)
```
{% endraw %}

동작 규칙은 단순하다.

{% raw %}
```text
현재 값 == 예상값
    → 새 값으로 변경하고 성공 반환

현재 값 != 예상값
    → 변경하지 않고 실패 반환
```
{% endraw %}

예를 들어 현재 값이 `10`이라고 예상하고 `11`로 변경하려는 경우:

{% raw %}
```text
실제 값이 10이면 → 11로 변경 성공
실제 값이 12이면 → 누군가 먼저 변경했으므로 실패
```
{% endraw %}

중요한 점은 **값을 비교하는 과정과 변경하는 과정이 하나의 원자적 연산으로 처리된다**는 것이다. 중간에 다른 스레드가 끼어들 수 없다.

### 3. Java에서의 CAS

Java에서는 `java.util.concurrent.atomic` 패키지의 클래스들을 통해 CAS를 사용할 수 있다.

{% raw %}
```java
AtomicInteger count = new AtomicInteger(0);

boolean success = count.compareAndSet(0, 1);
```
{% endraw %}

`compareAndSet(expectedValue, newValue)`는 현재 값이 `expectedValue`와 같으면 값을 변경하고 `true`를 반환한다.

{% raw %}
```java
AtomicInteger count = new AtomicInteger(10);

boolean first = count.compareAndSet(10, 11); // true
boolean second = count.compareAndSet(10, 12); // false

System.out.println(count.get()); // 11
```
{% endraw %}

첫 번째 CAS가 성공하면서 값이 `11`이 되었기 때문에, 두 번째 CAS에서 기대한 값 `10`과 실제 값 `11`이 달라 실패한다.

### 4. CAS를 이용한 증가 연산

`AtomicInteger.incrementAndGet()`은 개념적으로 다음과 같은 방식으로 구현할 수 있다.

{% raw %}
```java
AtomicInteger count = new AtomicInteger(0);

while (true) {
    int current = count.get();
    int next = current + 1;

    if (count.compareAndSet(current, next)) {
        break;
    }
}
```
{% endraw %}

처리 흐름은 다음과 같다.

1. 현재 값을 읽는다.

1. 새 값을 계산한다.

1. 현재 값이 읽었던 값과 동일하면 변경한다.

1. 다른 스레드가 먼저 값을 변경했다면 CAS가 실패한다.

1. 최신 값을 다시 읽고 재시도한다.

실제 코드에서는 다음처럼 사용할 수 있다.

{% raw %}
```java
AtomicInteger count = new AtomicInteger(0);

count.incrementAndGet();
count.getAndIncrement();
count.addAndGet(10);
```
{% endraw %}

이러한 연산은 단순한 `int` 변수의 `++` 연산과 달리 원자적으로 처리된다.

### 5. CAS와 synchronized의 차이

`synchronized`는 임계 영역에 진입할 수 있는 스레드를 하나로 제한하는 **락 기반 동기화 방식**이다.

{% raw %}
```java
private int count;

public synchronized void increment() {
    count++;
}
```
{% endraw %}

반면 CAS는 락을 획득해 다른 스레드를 대기시키기보다, 변경에 실패하면 값을 다시 읽고 연산을 재시도한다.

| 구분 | CAS | synchronized |
| --- | --- | --- |
| 방식 | 비교 후 조건부 변경 | 임계 영역에 락 적용 |
| 대기 방식 | 실패 시 재시도 | 락이 풀릴 때까지 대기 가능 |
| 문맥 전환 | 상대적으로 적음 | 경합 시 발생할 수 있음 |
| 적합한 작업 | 단일 값의 짧은 연산 | 여러 상태를 함께 변경하는 복합 연산 |
| 주의점 | 반복 실패 시 CPU 사용 증가 | 락 경합, 데드락 가능성 |

CAS가 항상 `synchronized`보다 우수한 것은 아니다.

단일 변수의 짧은 변경에는 CAS가 효과적이지만, 여러 필드를 일관된 상태로 함께 변경해야 한다면 락을 사용하는 편이 더 단순하고 안전할 수 있다.

### 6. CAS와 volatile의 차이

`volatile`과 CAS는 서로 대체 관계가 아니다.

`volatile`은 다음을 보장한다.

- 한 스레드가 변경한 값을 다른 스레드가 볼 수 있도록 하는 **가시성(Visibility)**

- volatile 변수 접근 전후의 일부 연산 재배치 제한

하지만 복합 연산의 원자성은 보장하지 않는다.

{% raw %}
```java
private volatile int count = 0;

public void increment() {
    count++; // 원자적이지 않음
}
```
{% endraw %}

`count`의 최신 값은 볼 수 있지만, `읽기 → 증가 → 쓰기` 전체가 하나의 연산으로 실행되는 것은 아니다.

반면 CAS는 비교와 변경을 원자적으로 수행한다.

정리하면 다음과 같다.

- `volatile`: 최신 값을 다른 스레드가 볼 수 있게 한다.

- CAS: 현재 값을 확인하고 조건부로 변경하는 과정을 원자적으로 수행한다.

- `synchronized`: 임계 영역 전체에 한 스레드만 진입하도록 한다.

Java의 Atomic 클래스 내부 상태는 일반적으로 가시성 보장을 위해 volatile 성격을 가지며, 값 변경에는 CAS를 함께 활용한다.

### 7. CAS의 장점

#### 락 획득과 해제 비용을 줄일 수 있다

경합이 심하지 않은 환경에서는 락을 걸고 스레드를 대기시키는 것보다 CAS가 빠르게 성공할 가능성이 높다.

#### 블로킹 없이 처리할 수 있다

한 스레드가 락을 오래 보유해 다른 스레드들이 모두 멈추는 구조를 피할 수 있다.

#### 단순한 상태 변경에 적합하다

카운터 증가, 상태 플래그 변경, 참조 교체처럼 하나의 값을 원자적으로 변경하는 작업에 효과적이다.

### 8. CAS의 한계

#### 반복 실패 시 CPU 사용량 증가

여러 스레드가 같은 값에 동시에 접근하면 CAS 실패와 재시도가 반복될 수 있다.

{% raw %}
```text
값 읽기 → 계산 → CAS 실패 → 다시 읽기 → 재계산 → 다시 CAS
```
{% endraw %}

이를 스핀(Spin) 또는 스핀 재시도라고 볼 수 있다. 경합이 매우 심하면 락 기반 방식보다 오히려 비효율적일 수 있다.

#### 여러 변수의 일관성을 보장하기 어렵다

CAS는 기본적으로 하나의 메모리 위치를 대상으로 동작한다.

예를 들어 계좌 잔액과 거래 상태를 반드시 함께 변경해야 한다면, 각각을 별도 CAS로 처리하는 것만으로는 중간 상태가 노출될 수 있다.

이 경우 다음 방법을 고려할 수 있다.

- 여러 값을 하나의 불변 객체로 묶고 `AtomicReference`로 교체

- `synchronized` 또는 `Lock` 사용

- 데이터베이스 트랜잭션 사용

#### ABA 문제

CAS의 대표적인 문제로 ABA 문제가 있다.

{% raw %}
```text
Thread A가 값 A를 읽음
Thread B가 A → B로 변경
Thread B가 다시 B → A로 변경
Thread A가 CAS 수행
```
{% endraw %}

Thread A 입장에서는 현재 값이 처음 읽은 `A`와 같기 때문에 아무 변화도 없었다고 판단한다. 하지만 실제로는 중간에 값이 변경되었다가 되돌아온 것이다.

단순 숫자에서는 문제가 되지 않을 수 있지만, 연결 리스트의 노드 참조나 객체 상태에서는 의미 있는 변경을 놓칠 수 있다.

Java에서는 버전 정보를 함께 관리하는 클래스를 사용할 수 있다.

{% raw %}
```java
AtomicStampedReference<String> reference =
        new AtomicStampedReference<>("A", 0);

int[] stampHolder = new int[1];
String current = reference.get(stampHolder);
int currentStamp = stampHolder[0];

boolean success = reference.compareAndSet(
        current,
        "B",
        currentStamp,
        currentStamp + 1
);
```
{% endraw %}

값뿐 아니라 stamp라는 버전 값까지 비교하므로 `A → B → A`로 돌아왔더라도 중간 변경을 감지할 수 있다.

관련 클래스는 다음과 같다.

- `AtomicStampedReference`: 숫자 형태의 버전 값을 함께 관리

- `AtomicMarkableReference`: boolean 표시 값을 함께 관리

### 9. CPU 수준에서는 어떻게 동작하는가?

CAS는 단순히 Java 코드만으로 원자성을 만드는 것이 아니다.

JVM은 CAS 연산을 실행할 때 CPU가 제공하는 원자적 명령어를 활용한다. CPU 아키텍처에 따라 구현 방식은 다르지만, 대표적으로 compare-and-exchange 계열 명령을 사용할 수 있다.

즉, JVM이 다음 동작을 CPU 수준의 하나의 원자적 연산으로 연결한다.

{% raw %}
```text
메모리 값 비교 + 조건부 쓰기
```
{% endraw %}

이 때문에 다른 CPU 코어나 스레드가 같은 메모리를 동시에 변경하려 해도 비교와 변경 사이에 끼어들 수 없다.

다만 CAS 자체가 공짜인 것은 아니다. 캐시 라인 동기화와 메모리 순서 보장 비용이 발생하며, 여러 코어가 동일한 캐시 라인을 계속 수정하면 캐시 일관성 트래픽이 증가할 수 있다.

### 10. AtomicInteger를 사용하면 항상 해결되는가?

다음 코드는 안전하다.

{% raw %}
```java
AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();
```
{% endraw %}

하지만 여러 Atomic 연산을 순서대로 호출한다고 해서 전체 로직이 원자적이 되는 것은 아니다.

{% raw %}
```java
if (count.get() < 100) {
    count.incrementAndGet();
}
```
{% endraw %}

`get()`과 `incrementAndGet()` 사이에 다른 스레드가 값을 변경할 수 있다. 따라서 최종 값이 100을 초과할 수 있다.

이런 조건부 갱신은 CAS 반복문으로 하나의 논리적 연산으로 묶어야 한다.

{% raw %}
```java
while (true) {
    int current = count.get();

    if (current >= 100) {
        break;
    }

    if (count.compareAndSet(current, current + 1)) {
        break;
    }
}
```
{% endraw %}

또는 Atomic 클래스가 제공하는 함수형 연산을 사용할 수 있다.

{% raw %}
```java
count.updateAndGet(current ->
        current >= 100 ? current : current + 1
);
```
{% endraw %}

### 11. 실무에서는 어디에 쓰이는가?

CAS는 다음과 같은 곳에서 자주 사용된다.

- 요청 수나 처리 건수를 세는 원자적 카운터

- 한 번만 수행되어야 하는 초기화 상태 관리

- `false → true` 형태의 실행 여부 플래그 변경

- 현재 설정 객체나 캐시 참조의 원자적 교체

- Lock-Free 자료구조 구현

- Java 동시성 라이브러리 내부 구현

예를 들어 특정 작업이 한 번만 시작되도록 만들 수 있다.

{% raw %}
```java
private final AtomicBoolean started = new AtomicBoolean(false);

public void start() {
    if (!started.compareAndSet(false, true)) {
        return;
    }

    // 최초 한 스레드만 실행
    initialize();
}
```
{% endraw %}

여러 스레드가 동시에 `start()`를 호출해도 `false → true` 변경에 성공한 하나의 스레드만 초기화 로직을 수행한다.

### 12. CAS를 이해할 때 기억할 것

CAS의 본질은 다음 한 문장으로 정리할 수 있다.

> 내가 마지막으로 확인한 이후 값이 변경되지 않았을 때만 새 값으로 변경한다.

실무 관점에서 다음 내용을 기억하면 된다.

1. `count++`는 원자적이지 않다.

1. CAS는 현재 값과 예상값이 같을 때만 값을 변경한다.

1. 실패하면 최신 값을 읽고 재시도할 수 있다.

1. `volatile`은 가시성을 제공하지만 복합 연산의 원자성을 제공하지 않는다.

1. CAS는 단일 상태의 짧은 변경에 적합하다.

1. 경합이 심하면 반복 재시도로 CPU 사용량이 증가할 수 있다.

1. 값이 변경되었다가 원래 값으로 돌아오는 ABA 문제를 주의해야 한다.

1. 여러 상태를 함께 변경해야 한다면 락이나 트랜잭션이 더 적합할 수 있다.

### 마무리

CAS는 직접 구현해서 사용하는 경우보다 `AtomicInteger`, `AtomicReference`, `ConcurrentHashMap` 같은 동시성 도구 내부에서 간접적으로 접하는 경우가 많다.

하지만 CAS의 원리를 이해하면 다음 내용을 더 명확히 판단할 수 있다.

- `volatile`만으로 충분한지

- Atomic 클래스를 사용해야 하는지

- `synchronized`가 필요한지

- 왜 특정 동시성 코드에서 반복문이 등장하는지

- Lock-Free라는 표현이 실제로 무엇을 의미하는지

결국 CAS는 **락을 사용하지 않고 현재 상태가 예상대로 유지되었는지 검증한 뒤 값을 원자적으로 변경하는 동시성 제어 방식**이다.
