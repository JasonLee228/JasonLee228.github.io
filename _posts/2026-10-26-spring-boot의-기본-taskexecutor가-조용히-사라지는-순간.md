---
title: "Spring Boot의 기본 TaskExecutor가 조용히 사라지는 순간"
date: 2026-10-26 09:00:00 +0900
categories: ["Spring", "운영"]
tags: ["spring", "taskexecutor", "async", "운영"]
permalink: /posts/spring-boot의-기본-taskexecutor가-조용히-사라지는-순간/
---

## `spring.task.execution.pool.*`를 설정했는데 적용되지 않았다

파일 다운로드를 `StreamingResponseBody`로 스트리밍하는 API의 스레드 사용량을 검토하고 있었다. 설정 파일에는 아래 값이 있었다.

{% raw %}
```yaml
spring:
  task:
    execution:
      pool:
        core-size: 10
```
{% endraw %}

처음에는 "비동기 작업 스레드는 10개 정도로 제한되어 있다"고 이해했다. 그런데 코드를 확인해 보니 이 설정은 **어디에도 적용되지 않고 있었다.** 에러도 경고도 없었다. 설정은 조용히 무시되고, 실제 작업은 상한이 없는 executor에서 돌고 있었다.

이 글은 그 원인인 "사용자 정의 `Executor` bean이 하나라도 있으면 Spring Boot의 기본 `applicationTaskExecutor`가 만들어지지 않는다"는 조건을 정리한다.

> 아래 내용은 Spring Boot 3.5.x, Spring Framework 6.2.x jar를 직접 확인한 결과를 기준으로 한다. 조건 클래스와 속성은 버전에 따라 다를 수 있다.

---

## `applicationTaskExecutor`는 무조건 생기는 bean이 아니다

Spring Boot는 `TaskExecutionAutoConfiguration`에서 `applicationTaskExecutor`라는 이름의 `ThreadPoolTaskExecutor`를 자동 구성한다. `spring.task.execution.pool.*` 속성은 이 bean을 만들 때 쓰인다.

여기서 중요한 점은 이 bean의 생성 조건이다. 3.5 기준으로 확인한 조건은 다음과 같다.

| 상황 | `applicationTaskExecutor` 생성 |
|---|---|
| `Executor` 타입 bean이 하나도 없다 | 생성된다 |
| `Executor` 타입 bean이 하나라도 있다 | 생성되지 않는다 |
| `spring.task.execution.mode=force` | 다른 `Executor`가 있어도 생성된다 |

`ThreadPoolTaskExecutor`, `ThreadPoolTaskScheduler`, `ExecutorService` 같은 타입은 모두 `Executor`를 구현한다. 그래서 아래처럼 용도별 executor를 하나만 정의해도 조건이 깨진다.

{% raw %}
```java
@Configuration
public class ExecutorConfig {

    @Bean
    public ThreadPoolTaskExecutor reportTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(4);
        executor.setThreadNamePrefix("report-");
        return executor;
    }
}
```
{% endraw %}

위 bean은 리포트 생성 전용이다. 하지만 이 bean이 등록되는 순간 Boot는 "사용자가 executor를 직접 구성했다"고 판단하고 기본 executor를 포기한다. 이 프로젝트에는 이런 bean이 열 개가 넘었고, `mode=force`는 설정되어 있지 않았다.

---

## 무엇이 `applicationTaskExecutor`에 의존하고 있는가

기본 executor가 없어지면 그것을 쓰던 쪽이 영향을 받는다. 대표적인 곳이 두 군데다.

1. `@Async`
   - executor 이름을 지정하지 않은 `@Async` 메서드는 기본 executor를 찾는다.
2. Spring MVC의 비동기 요청 처리
   - `StreamingResponseBody`, `Callable`, `DeferredResult`의 작업 스레드가 여기에 해당한다.

특히 MVC 쪽이 문제였다. Boot의 `WebMvcAutoConfiguration`은 `applicationTaskExecutor` bean이 **있을 때만** MVC 비동기 지원에 그 executor를 넣어 준다. bean이 없으면 아무것도 넣지 않는다. 그러면 Spring MVC가 자체 기본값으로 떨어진다.

{% raw %}
```text
applicationTaskExecutor 있음
  → MVC async 작업이 ThreadPoolTaskExecutor(설정한 풀 크기)에서 실행된다

applicationTaskExecutor 없음
  → RequestMappingHandlerAdapter 기본값인 SimpleAsyncTaskExecutor 사용
```
{% endraw %}

`SimpleAsyncTaskExecutor`는 이름과 달리 풀이 아니다. **작업마다 새 스레드를 만들고**, 기본 `concurrencyLimit`은 무제한이다. 스레드 이름은 `MvcAsync1`, `MvcAsync2`처럼 찍힌다.

Spring 6.2 jar의 `RequestMappingHandlerAdapter`에는 이 상황을 경고하는 문자열도 들어 있다. 첫 비동기 요청에서 한 번 로그로 남는다.

{% raw %}
```text
!!! Performing asynchronous handling through the default Spring MVC SimpleAsyncTaskExecutor.
This executor is not suitable for production use under load.
Please, configure an AsyncTaskExecutor through the WebMvc config.
```
{% endraw %}

---

## 실제로 어떤 위험이 되는가

이 사례에서는 큰 파일 다운로드가 `StreamingResponseBody`로 처리되고 있었다. 실제 파일 송수신은 요청 스레드가 아니라 MVC async 스레드가 끝까지 맡는다.

1. Tomcat 요청 스레드는 controller가 return하면 바로 반납된다.
2. 실제 작업은 `MvcAsyncN` 스레드가 다운로드 한 건당 한 개씩 맡는다.
3. 풀 상한이 없으므로 대형 다운로드가 몰리면 스레드, 메모리, 임시 디스크가 같이 늘어난다.

요약하면 위험은 "스레드 고갈"이 아니라 **"스레드가 무제한으로 늘어나는 것"**이다. 풀 크기를 10으로 설정했다고 믿었기 때문에 상한이 있다고 착각하기 쉽다는 점이 더 위험하다.

한 가지 주의할 점이 있다. 요청 timeout이 지나면 응답은 끝나지만, 작업 스레드가 interrupt로 멈춘다는 보장은 없다. 블로킹 read 중이면 응답이 끝난 뒤에도 스레드가 남을 수 있다. 이 부분은 코드만으로는 단정할 수 없고 런타임 확인이 필요하다.

---

## 지금 내 앱에서 확인하는 방법

### 1. 코드와 설정으로 확인한다

- 프로젝트에서 `Executor`를 구현하는 `@Bean`이 있는지 찾는다.
- `spring.task.execution.mode` 설정이 있는지 본다.

### 2. 기동 시 조건 평가 리포트를 본다

{% raw %}
```bash
java -jar app.jar --debug
```
{% endraw %}

출력의 `CONDITIONS EVALUATION REPORT`에서 `TaskExecutionAutoConfiguration`의 `applicationTaskExecutor`가 `Negative matches`에 있는지 확인한다.

### 3. bean 존재 여부를 직접 확인한다

{% raw %}
```java
@Component
class ExecutorCheck implements ApplicationRunner {
    private final ApplicationContext context;

    ExecutorCheck(ApplicationContext context) {
        this.context = context;
    }

    @Override
    public void run(ApplicationArguments args) {
        System.out.println("applicationTaskExecutor = "
                + context.containsBean("applicationTaskExecutor"));
    }
}
```
{% endraw %}

### 4. 운영 로그에서 경고와 스레드 이름을 찾는다

- `Performing asynchronous handling through the default Spring MVC SimpleAsyncTaskExecutor` 로그가 있는가
- 스레드 덤프나 로그에 `MvcAsync` 접두사 스레드가 있는가

---

## 해결 방법

상황에 따라 세 가지 중 하나를 고른다.

### 방법 1. `mode=force`로 기본 executor를 되살린다

{% raw %}
```yaml
spring:
  task:
    execution:
      mode: force
      pool:
        core-size: 10
        max-size: 20
        queue-capacity: 100
```
{% endraw %}

기존 설정을 그대로 살리는 가장 작은 변경이다. 다만 `mode` 속성은 Boot 버전에 따라 없을 수 있으므로 사용하는 버전의 문서를 먼저 확인한다.

### 방법 2. MVC 비동기용 executor를 명시한다

기본 executor에 기대지 않고, MVC async 전용 executor를 직접 지정한다. 용도가 분명해서 가장 읽기 쉽다.

{% raw %}
```java
@Configuration
public class AsyncWebConfig implements WebMvcConfigurer {

    private final ThreadPoolTaskExecutor downloadTaskExecutor;

    public AsyncWebConfig(@Qualifier("downloadTaskExecutor")
                          ThreadPoolTaskExecutor downloadTaskExecutor) {
        this.downloadTaskExecutor = downloadTaskExecutor;
    }

    @Override
    public void configureAsyncSupport(AsyncSupportConfigurer configurer) {
        configurer.setTaskExecutor(downloadTaskExecutor);
    }
}
```
{% endraw %}

이때 풀이 가득 찼을 때의 정책(큐 크기, `RejectedExecutionHandler`)도 같이 정해야 한다. 상한을 두면 "무제한 증가" 대신 "대기 또는 거절"이 생기기 때문이다.

### 방법 3. `@Async`는 executor 이름을 명시한다

{% raw %}
```java
@Async("reportTaskExecutor")
public void generateReport() { ... }
```
{% endraw %}

이름을 지정하지 않은 `@Async`는 어떤 executor를 쓰는지 읽어서는 알 수 없다. 이름을 적어 두면 기본 executor 유무와 무관해진다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 함정 | `Executor` bean이 하나라도 있으면 `applicationTaskExecutor`가 생성되지 않는다 |
| 증상 | `spring.task.execution.pool.*`가 에러 없이 무시된다 |
| 결과 | MVC async가 `SimpleAsyncTaskExecutor`로 떨어져 요청마다 스레드가 늘어난다 |
| 확인 | `--debug` 조건 리포트, bean 존재 확인, `MvcAsync` 스레드 이름, 첫 async 요청의 경고 로그 |
| 대응 | `mode=force`, `configureAsyncSupport`로 명시, `@Async("이름")` |

설정 파일에 값이 있다고 해서 그 값이 적용된다는 뜻은 아니다. 특히 자동 구성이 조건부 bean인 경우에는 **"이 설정을 읽는 bean이 실제로 만들어졌는가"**를 한 번은 확인해 두는 것이 좋다.
