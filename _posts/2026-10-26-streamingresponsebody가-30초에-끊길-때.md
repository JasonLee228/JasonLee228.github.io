---
title: "StreamingResponseBody가 30초에 끊길 때"
date: 2026-10-26 11:10:00 +0900
categories: ["Spring", "운영"]
tags: ["spring-mvc", "streamingresponsebody", "timeout", "ingress"]
permalink: /posts/streamingresponsebody가-30초에-끊길-때/
---

대용량 파일 다운로드 API가 있었다. 작은 파일은 문제가 없는데, 큰 파일은 **정확히 30초 부근에서 실패**한다는 제보가 들어왔다. 서버 로그에는 `AsyncRequestTimeoutException`이 있었고 그 뒤로 이상한 메시지가 몇 줄 더 따라붙어 있었다.

원인은 설정 한 줄이 없는 것이었다. 하지만 그 설정만 넣어서는 끝나지 않는다. 이 글은 원인, 설정 방법, 그리고 반드시 함께 확인해야 하는 앞단 프록시의 timeout을 정리한다.

---

## 1. 증상과 로그

컨트롤러는 `StreamingResponseBody`를 반환한다.

{% raw %}
```java
@PostMapping("/reports/download/stream")
public ResponseEntity<StreamingResponseBody> download(@RequestBody ReportDownloadRequest request) {
    StreamingResponseBody body = out -> reportService.stream(request, out);
    return ResponseEntity.ok()
            .contentType(MediaType.APPLICATION_OCTET_STREAM)
            .body(body);
}
```
{% endraw %}

큰 파일에서 남은 로그는 다음과 같은 종류였다.

{% raw %}
```text
AsyncRequestTimeoutException
Thread interrupted while sleeping
Response not usable after async request completion.
```
{% endraw %}

첫 줄이 원인이고, 나머지 둘은 2차 메시지다. timeout으로 요청이 이미 종료 처리되었는데 작업 스레드가 계속 돌다가 인터럽트되거나, 이미 끝난 응답에 쓰려다 남기는 로그다. 2차 메시지에 이끌려 다른 원인을 찾기 시작하면 시간을 낭비한다.

---

## 2. 원인: 비동기 요청 timeout 기본값

`StreamingResponseBody`는 서블릿 비동기 처리로 실행된다. 이때 비동기 요청에는 timeout이 있고, 별도로 설정하지 않으면 **서블릿 컨테이너의 기본값**을 쓴다. Tomcat 기준으로 30초다.

Spring Boot 문서의 `spring.mvc.async.request-timeout` 설명도 같은 취지다. 값을 정하지 않으면 하부 구현의 기본 timeout을 사용한다.

여기서 중요한 점은 이 timeout이 **전송 구간만이 아니라 요청 전체 처리 시간**에 걸린다는 것이다. 이번 다운로드 흐름은 다음과 같았다.

{% raw %}
```text
요청
  → 원본 시스템에서 파일을 읽어 서버의 임시 파일에 전체 저장
  → 권한 확인(외부 시스템 조회)
  → 임시 파일을 사용자 응답으로 전송
  → 임시 파일 삭제
```
{% endraw %}

따라서 30초에는 세 구간의 시간이 모두 합산된다.

{% raw %}
```text
원본 → 서버 임시 저장 시간
+ 확인 시간
+ 서버 → 사용자 전송 시간
```
{% endraw %}

사용자 입장에서는 "다운로드가 30초 만에 끊긴다"로 보이지만, 실제로는 내려받기 시작 전의 준비 구간도 같은 시계에서 흐르고 있었다.

---

## 3. 해결: 설정 한 줄

공통 설정 파일에 한 줄을 추가한다.

{% raw %}
```yaml
spring:
  mvc:
    async:
      request-timeout: ${APP_ASYNC_REQUEST_TIMEOUT:10m}
```
{% endraw %}

몇 가지 결정 사항이 있다.

- **기본값은 10분**으로 했다. 무제한은 피한다. 끊긴 요청, 느린 클라이언트, 외부 시스템 지연이 작업 스레드와 임시 파일을 무기한 점유할 수 있기 때문이다.
- **환경 변수로 덮어쓸 수 있게 했다.** 환경별로 코드 배포 없이 조정할 수 있다.
- **공통 설정 파일 한 곳에만 둔다.** 프로파일별 파일은 공통 설정을 상속하므로 같은 값을 복제하지 않는다.
- 값 형식은 Spring Boot의 Duration 바인딩을 쓴다. `10m`, `600s`, `PT10M` 모두 가능하고, 잘못된 값은 시작 시점에 바인딩 오류로 드러난다.

별도 Java 설정(`WebMvcConfigurer.configureAsyncSupport`로 `setDefaultTimeout` 호출)으로도 같은 효과를 낼 수 있다. 하지만 Boot의 설정 속성으로 되는 일에 코드를 추가하는 셈이라 채택하지 않았다. 컨트롤러별로 `WebAsyncTask`를 쓰는 방식도 응답 계약이 바뀌므로 비채택했다.

---

## 4. 설정 계약은 테스트로 고정한다

실제로 30초 넘게 걸리는 다운로드를 단위 테스트에 넣는 것은 좋지 않다. 느리고 불안정하며 실제 경로(원본, 권한 확인 시스템, 프록시)를 검증하지도 못한다. 대신 **설정 계약만** 테스트한다.

{% raw %}
```java
class AsyncTimeoutConfigTest {

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withInitializer(new ConfigDataApplicationContextInitializer())
            .withUserConfiguration(WebMvcProperties.class);

    @Test
    void defaultsToTenMinutes() {
        runner.run(ctx -> assertThat(ctx.getBean(WebMvcProperties.class)
                .getAsync().getRequestTimeout()).isEqualTo(Duration.ofMinutes(10)));
    }

    @Test
    void overridableByEnv() {
        runner.withPropertyValues("APP_ASYNC_REQUEST_TIMEOUT=15m")
              .run(ctx -> assertThat(ctx.getBean(WebMvcProperties.class)
                .getAsync().getRequestTimeout()).isEqualTo(Duration.ofMinutes(15)));
    }

    @Test
    void invalidValueFailsBinding() {
        runner.withPropertyValues("APP_ASYNC_REQUEST_TIMEOUT=invalid")
              .run(ctx -> assertThat(ctx).hasFailed());
    }
}
```
{% endraw %}

위 코드는 방식을 보이기 위한 예시다. 환경 변수를 테스트에서 주입하는 방법과 `WebMvcProperties`의 위치는 Spring Boot 버전에 따라 다를 수 있다.

세 가지 계약을 고정한다.

1. 환경 변수가 없으면 기본값이 바인딩된다.
2. 환경 변수로 지정한 값이 우선한다.
3. 잘못된 값은 시작 단계에서 실패한다.

---

## 5. 앞단 프록시의 timeout이 더 짧으면 소용없다

애플리케이션 timeout을 10분으로 늘렸어도, 앞에 있는 Ingress나 리버스 프록시의 timeout이 더 짧으면 **프록시가 먼저 연결을 끊는다.** 이 경우 서버 로그에는 오류가 보이지 않고 클라이언트만 실패한다.

nginx 계열 프록시의 응답 대기와 전송 timeout 기본값은 일반적으로 60초 수준이다. ingress-nginx에서는 다음 annotation이 관련된다.

{% raw %}
```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
```
{% endraw %}

규칙은 단순하다. **바깥쪽 timeout이 안쪽 timeout보다 짧지 않아야 한다.**

{% raw %}
```text
클라이언트 timeout  ≥  프록시 read/send timeout  ≥  애플리케이션 async timeout
```
{% endraw %}

이번 경우 저장소에는 HTTP 다운로드 경로의 Ingress 리소스가 없었다. 있는 것은 다른 프로토콜(gRPC)용 Ingress의 긴 timeout 설정뿐이었고, 이것은 HTTP 다운로드 API에 적용되지 않는다. 비슷한 이름의 설정이 있다고 해서 해당 경로에도 적용된다고 착각하기 쉽다. 실제 배포 환경의 설정을 직접 조회해서 확인해야 한다.

---

## 6. 10분이 충분한가

`10m`은 30초 제한을 걷어 내기 위한 운영 초기값이다. 모든 파일 크기와 모든 전송 속도를 보장하는 상한이 아니다. 앞의 합산 식을 다시 보자.

{% raw %}
```text
원본 전체 수신 + 확인 + 사용자 전체 송신  ≤  10분
```
{% endraw %}

이 흐름은 수신과 송신이 직렬이다. 파일이 크고 사용자 네트워크가 느리면 이 합이 10분을 넘을 수 있다. 운영 값을 정할 때는 다음을 측정해야 한다.

- 지원할 최대 파일 크기
- 하위 사용자의 전송 속도(백분위수)
- 권한 확인 시스템 응답 시간의 상위 백분위수

그 값으로 환경 변수만 조정하면 된다. 구조 자체(임시 파일에 전체 저장 후 전송)를 바꾸는 것은 이번 범위가 아니었다.

또 timeout을 늘리면 **장시간 작업이 스레드, 임시 디스크, 커넥션을 오래 점유**한다. 동시 대용량 다운로드가 많아지면 이 자원이 먼저 부족해질 수 있다. timeout 증가는 처리량을 늘리지 않는다. 실패를 늦출 뿐이다.

---

## 7. 이 설정으로 해결되지 않는 것들

다음은 timeout과 별개로 장시간 다운로드에 영향을 줄 수 있는 요소다. 이번 변경 범위 밖이었고, 재현되면 별도 원인으로 다뤄야 한다.

| 요소 | 설명 |
|---|---|
| 내부 호출 timeout | 서비스 내부의 다른 호출이 60초 같은 자체 제한을 가질 수 있다 |
| Pod 종료 유예 | 배포 중 종료 유예 시간(기본 30초)이 짧으면 진행 중인 다운로드가 끊긴다 |
| 파일 크기 제한 | 설정된 최대 크기를 넘으면 timeout과 무관하게 거부된다 |
| 클라이언트 연결 종료 | 사용자가 중간에 끊으면 `Broken pipe`가 난다. timeout 오류와 구분해야 한다 |

특히 `Broken pipe`는 같은 로그 시기에 나타나도 원인이 다르다. 클라이언트가 스스로 끊은 것이므로 이 글의 timeout 설정과 무관하다.

---

## 8. 정리

| 질문 | 답 |
|---|---|
| 왜 30초에 끊기나 | 비동기 요청 timeout 기본값이 컨테이너 기본(Tomcat 30초)이기 때문 |
| 무엇에 걸리는 시간인가 | 준비 구간과 전송 구간의 합산 시간 |
| 어떻게 고치나 | `spring.mvc.async.request-timeout` 지정 |
| 값은 어떻게 정하나 | 유한한 기본값(예: 10분) + 환경 변수 override |
| 설정만으로 충분한가 | 아니다. 앞단 프록시 read/send timeout도 같거나 길어야 한다 |
| 어떻게 검증하나 | 설정 계약은 자동 테스트, 대용량 성공과 프록시 정렬은 통합 검증 |

체크리스트는 다음과 같다.

- [ ] 오류 로그의 첫 줄이 `AsyncRequestTimeoutException`인가 (2차 메시지에 속지 않는다)
- [ ] `spring.mvc.async.request-timeout`이 명시되어 있는가
- [ ] 요청 처리에 준비 구간(임시 저장, 권한 확인 등)이 포함되어 있지 않은가
- [ ] 프록시 `read`, `send` timeout이 애플리케이션 timeout 이상인가
- [ ] 무제한 대신 환경 변수로 조정 가능한 유한한 값을 쓰는가
- [ ] 30초 이상 걸리는 실제 다운로드와 작은 파일 다운로드를 모두 확인했는가

이 글을 쓰는 시점에는 설정 계약 테스트까지만 확인했다. 실제 배포 환경의 프록시 timeout 값과 30초를 넘는 대용량 다운로드 성공은 운영 환경에서 별도로 확인해야 한다.
