---
title: "컨테이너에서 JAVA_OPTS가 안 먹는 이유와 JDK 25 JVM 메모리 점검"
date: 2026-11-16 18:10:00 +0900
categories: ["Java", "JVM"]
tags: ["java", "jvm", "jdk25", "kubernetes", "메모리"]
permalink: /posts/컨테이너에서-java-opts가-안-먹는-이유와-jdk-25-jvm-메모리-점검/
---

## 시작은 "메모리 좀 줄일 수 있나"

JDK 25로 올린 Spring Boot 서비스의 메모리를 줄일 수 있는지 검토했다. 후보로 나온 것은 흔한 세 가지였다.

- GraalVM Native Image
- 세대별 ZGC(`-XX:+UseZGC -XX:+ZGenerational`)
- 가상 스레드(`spring.threads.virtual.enabled=true`)

조건은 "기능 동작에 영향이 없을 것"이었다. 실제 pod를 재 보니 세 후보보다 먼저 고칠 것이 보였다. 이 글은 그 측정과 판단을 정리한다.

---

## 측정값

pod 4개(개발 2, 사내 2)의 컨테이너 메모리는 1,142~1,324MiB였다. request는 2Gi, limit은 4Gi다. 아래 표는 개발 pod 하나(RSS 약 1.2GB)의 JVM 안을 나눈 것이다.

| 영역 | 크기 |
|---|---|
| ZGC heap committed | 약 610MB (사용 500MB, GC 후 생존 객체 342MB) |
| Metaspace + Compressed Class Space (클래스 34,102개) | 약 208MB |
| Code cache | 약 40MB |
| 스레드 스택 (스택 2,142개, 평균 49KB) | 약 104MB |
| 커널 메모리 (커널 스택, 페이지 테이블) | 약 77MB |
| 그 외 native | 약 215MB (Native Memory Tracking이 꺼져 있어 세부는 모름) |

눈에 띄는 것이 두 개다. 스레드가 2,000개를 넘는다. 그리고 설정한 heap 크기가 보이지 않는다.

---

## 1. `JAVA_OPTS`는 아무도 읽지 않았다

Deployment에는 이런 env가 있었다.

{% raw %}
```yaml
env:
  - name: JAVA_OPTS
    value: "-Xms2g -Xmx2g"
```
{% endraw %}

Dockerfile은 exec 형식이었다.

{% raw %}
```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```
{% endraw %}

`JAVA_OPTS`는 JVM이 아는 변수가 아니다. 셸 스크립트나 실행 스크립트가 `java $JAVA_OPTS ...`처럼 펼쳐 줄 때만 의미가 있다. exec 형식 ENTRYPOINT는 셸을 거치지 않으므로 아무도 펼치지 않는다. 결과적으로 heap 상한은 기본값으로 정해졌다. 기본값은 컨테이너 메모리 limit의 25%다.

JDK 25(Corretto 25.0.5)에서 직접 확인했다.

{% raw %}
```text
$ java -XX:+PrintFlagsFinal -version | grep -E " MaxRAMPercentage | InitialRAMPercentage "
   double InitialRAMPercentage = 1.562500   {product} {default}
   double MaxRAMPercentage     = 25.000000  {product} {default}

$ JAVA_OPTS=-Xmx64m java -XshowSettings:vm -version
    Max. Heap Size (Estimated): 15.87G     # 무시됨. 이 PC 메모리의 25%

$ JDK_JAVA_OPTIONS=-Xmx64m java -XshowSettings:vm -version
NOTE: Picked up JDK_JAVA_OPTIONS: -Xmx64m
    Max. Heap Size: 64.00M                 # java 런처가 직접 읽음
```
{% endraw %}

limit 4Gi pod라면 실제 최대 heap은 1GiB다. "heap 2GiB 고정"이라고 믿고 있던 설정은 죽은 설정이었다.

선택지는 세 가지다.

- 런처가 직접 읽는 `JDK_JAVA_OPTIONS`를 쓴다(JDK 9 이상).
- `JAVA_TOOL_OPTIONS`를 쓴다. JVM이 읽지만 시작할 때 매번 `Picked up ...` 메시지를 남긴다.
- 고정 `-Xmx` 대신 `-XX:MaxRAMPercentage`로 limit 비율을 정한다.

주의할 점이 있다. 죽은 설정을 "살리는" 것도 변경이다. 지금은 heap이 1GiB 상한으로 잘 돌고 있다. 누가 이 값을 그대로 `JDK_JAVA_OPTIONS`로 옮기면 `-Xms2g` 때문에 heap이 처음부터 2GiB를 잡아 메모리 사용량이 오히려 늘어난다. 이번에는 죽은 env를 지우고 필요한 값만 새로 정하기로 했다.

---

## 2. 스레드 2,000개는 Tomcat `min-spare`였다

같은 pod에서 센 전체 스레드 2,209개 중 2,050개가 `http-nio-...-exec-*` 대기 스레드였다. 위 표의 스택 2,142개와 다른 이유는 두 값을 따로 측정했기 때문이다(측정 방식과 시점이 다르다). 설정은 `server.tomcat.threads.max`와 `min-spare`가 둘 다 2048이었다.

Tomcat 11.0.27 소스를 보면 이유가 바로 나온다. 커넥터의 내부 executor는 `min-spare`를 core 크기로 쓴다.

{% raw %}
```java
// org.apache.tomcat.util.net.AbstractEndpoint
executor = new ThreadPoolExecutor(getMinSpareThreads(), getMaxThreads(), getThreadsMaxIdleTime(),
        TimeUnit.MILLISECONDS, taskqueue, tf);
```
{% endraw %}

그리고 Tomcat의 `ThreadPoolExecutor`는 생성자 끝에서 `prestartAllCoreThreads()`를 부른다. core 스레드를 **기동 시점에 전부** 만든다는 뜻이다. `threadsMaxIdleTime` 기본값은 60,000ms라서, core를 넘는 스레드만 60초 유휴 뒤에 회수된다.

정리하면 `min-spare=2048`은 "요청이 없어도 스레드 2,048개를 항상 띄워 둔다"는 설정이다. 스레드 스택은 실제로 쓴 만큼만 RSS에 잡히지만, 이 서비스에서는 그것만 약 100MB였다.

처방은 `max`는 그대로 두고 `min-spare`만 64 정도로 낮추는 것이다. 최대 동시 처리량은 같다. 부하가 오면 max까지 늘고, 끝나면 60초 뒤 줄어든다.

---

## 3. 세 후보의 판단

| 후보 | 판단 | 이유 |
|---|---|---|
| 세대별 ZGC | 할 일 없음 | JDK 25의 `-XX:+UseZGC`는 이미 세대별이다. `-XX:+ZGenerational`을 주면 `Ignoring option ZGenerational; support was removed in 24.0` 경고만 나온다 |
| 가상 스레드 | 보류 | 줄어드는 것은 대기 스레드 비용뿐이다. 대신 스레드 수가 사실상 동시 요청 상한 역할을 하던 것이 사라져, 동시 요청이 DB 커넥션 풀(10개)로 바로 몰린다. 부하 동작이 바뀐다 |
| Native Image | 권장 안 함 | 아래 참고 |

Native Image를 뺀 이유는 이렇다.

- Spring AOT가 빌드 시점에 `@ConditionalOnProperty`와 profile을 고정한다. 환경별 설정(ConfigMap)으로 bean 구성을 바꾸던 방식이 깨진다.
- reflection을 많이 쓰는 라이브러리는 메타데이터를 직접 써야 한다.
- Native Image는 ZGC를 지원하지 않는다. 기본은 Serial GC이고, G1(`--gc=G1`)은 Oracle GraalVM에서만 쓸 수 있다.
- 빌드에 수 GB 메모리가 필요해 CI 빌드 환경도 바꿔야 한다.

---

## 4. 영향 없이 효과가 있는 것: Compact Object Headers

JDK 25에서 `-XX:+UseCompactObjectHeaders`는 정식(product) 옵션이다. 64비트에서 객체 헤더를 12바이트에서 8바이트로 줄인다. unlock 옵션 없이 켜진다.

{% raw %}
```text
$ java -XX:+PrintFlagsFinal -version | grep UseCompactObjectHeaders
     bool UseCompactObjectHeaders = false   {product lp64_product} {default}
```
{% endraw %}

작은 객체가 많은 서비스일수록 효과가 크다. 공개된 벤치마크에서는 heap 사용량이 10~20% 줄었다고 한다. 이 서비스의 생존 객체 342MB에 대입하면 30~60MB 정도로 추정한다. 이 숫자는 추정이다. 적용 전후를 같은 부하로 재야 한다.

---

## 권장 순서

1. 죽은 `JAVA_OPTS` env를 지운다. heap 설정이 필요하면 `JDK_JAVA_OPTIONS`나 `MaxRAMPercentage`로 새로 정한다.
2. Tomcat `min-spare`를 낮춘다. `max`는 그대로 둔다.
3. `-XX:+UseCompactObjectHeaders`를 켜고 전후를 잰다.
4. 메모리 request를 실제 사용량에 맞춘다. 사용량이 최대 1,324MiB(약 1.3Gi)인데 request가 2Gi면 노드 예약량에서 가장 큰 낭비가 이것이다.

그다음 단계는 비교 측정이 필요하다. 두 방향이 있다.

- ZGC를 유지하고 `-XX:SoftMaxHeapSize`를 조정한다. 이 값은 ZGC가 heap을 그 아래로 유지하려는 목표다. GC가 더 자주 돌아 CPU 사용량이 늘 수 있다.
- G1으로 바꾼다. ZGC는 compressed oops를 쓰지 못하고 G1은 쓸 수 있어 heap이 더 작아질 수 있다. 대신 GC 정지 시간이 늘 수 있다. G1은 `SoftMaxHeapSize`로 heap 크기를 조절하지 않는다. JDK 25에서 옵션 자체는 오류 없이 받지만, 그 동작은 직접 확인하지 않았다.

---

## 정리

| 항목 | 내용 |
|---|---|
| `JAVA_OPTS` | JVM이 읽지 않는다. exec 형식 ENTRYPOINT에서는 아무도 펼치지 않는다 |
| 실제 heap 상한 | 기본 `MaxRAMPercentage=25`, limit 4Gi면 1GiB |
| JVM이 직접 읽는 env | `JDK_JAVA_OPTIONS`(런처), `JAVA_TOOL_OPTIONS`(JVM) |
| 스레드 2,000개 | Tomcat `min-spare`가 core 크기이고 기동 시 전부 생성됨 |
| 세대별 ZGC | JDK 25에서 기본. `ZGenerational`은 제거된 옵션 |
| 바로 쓸 만한 옵션 | `-XX:+UseCompactObjectHeaders`(JDK 25 정식) |

플래그와 env 동작은 Corretto 25.0.5에서, Tomcat 동작은 tomcat-embed-core 11.0.27 소스에서 확인했다. JVM 내부 수치는 개발 pod 하나 기준이고, 컨테이너 메모리 사용량은 pod 4개의 값이다.
