---
title: "Spring Boot 4로 올릴 때 Jackson 3 기본값이 바꾸는 역직렬화 결과"
date: 2026-10-26 10:10:00 +0900
categories: ["Spring", "활용"]
tags: ["spring-boot", "jackson", "마이그레이션", "역직렬화"]
permalink: /posts/spring-boot-4로-올릴-때-jackson-3-기본값이-바꾸는-역직렬화-결과/
---

Spring Boot 3.5에서 4.1로 올리는 작업을 했다. 컴파일 오류는 대부분 import 변경이었다. 문제는 컴파일이 통과한 뒤에 있었다.

Boot 4는 Jackson 3을 기본으로 쓴다. 같은 JSON을 같은 DTO로 읽어도 **Jackson 2와 결과가 달라지는 경우**가 있다. 에러가 나지 않고 값만 조용히 바뀐다는 점이 위험하다.

이 글은 마이그레이션에서 확인한 Jackson 3 관련 함정과 대응 방법을 정리한다.

> 버전에 따라 동작이 다를 수 있다. 이 글의 내용은 Spring Boot 4.1.x, Jackson 3.1.x 기준으로 확인한 결과다.

---

## 1. 바뀐 것 먼저 정리

Jackson 3에서 코드가 직접 영향을 받는 변경은 다음과 같다.

| 항목 | Jackson 2 | Jackson 3 |
|---|---|---|
| 패키지 | `com.fasterxml.jackson.databind` | `tools.jackson.databind` |
| 어노테이션 패키지 | `com.fasterxml.jackson.annotation` | 그대로 유지 |
| 기본 예외 | `JsonProcessingException` (checked) | `JacksonException` (unchecked) |
| Mapper 생성 | `new ObjectMapper()` | `JsonMapper.builder()...build()` (불변) |
| 날짜 모듈 | `JavaTimeModule` 등록 필요 | 기본 포함 |

패키지가 바뀌므로 변경 대상 파일이 많다. 이번 작업에서는 main 코드 약 140개, 테스트 약 70개 파일의 import를 바꿨다. 이 부분은 기계적인 작업이다.

진짜 문제는 **기본 설정값**과 **예외 타입**이다.

---

## 2. Mapper 빈을 직접 정의하면 자동 구성이 물러난다

Boot 4에서는 애플리케이션에 Mapper 빈이 이미 있으면 자동 구성 `JsonMapper`가 만들어지지 않았다. 이 동작도 버전에 따라 다를 수 있으니 업그레이드할 때 확인해야 한다.

기존에 `ObjectMapper` 빈을 직접 정의하고 있었다면, 같은 설정을 `JsonMapper` 빈으로 옮겨야 한다. 이때 `JsonMapper.builder()`만 쓰면 Jackson 3의 새 기본값이 적용된다. 기존 동작을 유지하려면 `builderWithJackson2Defaults()`로 시작한다.

{% raw %}
```java
@Bean
public JsonMapper objectMapper() {
    return JsonMapper.builderWithJackson2Defaults()
            .changeDefaultPropertyInclusion(incl ->
                    incl.withValueInclusion(JsonInclude.Include.NON_NULL)
                        .withContentInclusion(JsonInclude.Include.NON_NULL))
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .disable(DateTimeFeature.WRITE_DATES_AS_TIMESTAMPS)   // Jackson 3에서는 DateTimeFeature로 이동
            .build();
}
```
{% endraw %}

`builderWithJackson2Defaults()`는 Jackson 2의 기본 설정을 복원한 builder를 돌려준다. 기존 명시 설정(null 제외, unknown property 무시, 날짜 문자열 출력)은 그 위에 그대로 얹었다.

---

## 3. 눈에 안 띄는 곳: 기본 코덱과 `new`로 만든 Mapper

앱 Mapper 빈을 맞춰도 끝이 아니다. **Mapper 빈을 쓰지 않는 경로**가 남는다.

- `WebClient`의 기본 JSON 코덱
- `WebClient.create(url)`로 만든 클라이언트
- `RestClient` 기본 설정
- 코드 안에서 직접 만든 Mapper

이 경로들은 Jackson 3 기본값을 그대로 쓴다. 이번 작업에서는 공용 `ExchangeStrategies`가 기본 Jackson 3 코덱을 쓰고 있었고, 외부 API 응답을 읽는 DTO의 결과가 달라졌다.

Spring 6의 기본 JSON 코덱은 `FAIL_ON_UNKNOWN_PROPERTIES`와 `DEFAULT_VIEW_INCLUSION`을 끈 Mapper를 썼다. 이 동작을 복원하려면 코덱에 Mapper를 직접 등록한다.

{% raw %}
```java
JsonMapper codecMapper = JsonMapper.builderWithJackson2Defaults()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .disable(MapperFeature.DEFAULT_VIEW_INCLUSION)
        .build();

ExchangeStrategies strategies = ExchangeStrategies.builder()
        .codecs(c -> {
            c.defaultCodecs().jacksonJsonDecoder(new JacksonJsonDecoder(codecMapper));
            c.defaultCodecs().jacksonJsonEncoder(new JacksonJsonEncoder(codecMapper));
        })
        .build();
```
{% endraw %}

코덱 클래스 이름은 Spring Framework 7 기준이다. 버전에 따라 이름이 다를 수 있으니 사용하는 버전의 API를 확인한다.

앱의 Mapper 빈과 코덱용 Mapper를 일부러 분리했다. 앱 빈은 응답 직렬화 정책(null 제외 등)을 가지고 있고, 외부 API 응답을 읽는 코덱은 다른 정책이 필요하기 때문이다.

---

## 4. 무엇이 어떻게 달라졌나: 생성자 선택

가장 눈에 띄는 차이는 **생성자 선택**이었다.

다음과 같은 DTO가 있다고 하자.

{% raw %}
```java
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderSummary {
    private String id;
    private List<String> tags = new ArrayList<>();
    private int retryCount = 3;
}
```
{% endraw %}

Jackson 2는 기본 생성자로 객체를 만들고 setter나 필드로 값을 채운다. 필드 초기화(`new ArrayList<>()`, `= 3`)가 살아 있다.

기본 Jackson 3 Mapper는 이 클래스에서 all-args 생성자를 properties creator로 고를 수 있었다. 파라미터 이름 감지 기능이 켜져 있기 때문이다. 이 경우 JSON에 없는 필드는 필드 초기화를 거치지 않고 생성자 인자의 기본값(`null`, `0`)이 들어간다.

{% raw %}
```text
입력:  {"id": "o-1"}

Jackson 2        → tags = [], retryCount = 3
기본 Jackson 3   → tags = null, retryCount = 0   (생성자 경로를 탄 경우)
```
{% endraw %}

위 예시는 개념을 보이기 위한 것이다. 실제로 어떤 생성자가 선택되는지는 DTO의 어노테이션과 컴파일 옵션(`-parameters`)에 따라 달라질 수 있다.

`builderWithJackson2Defaults()`는 이 파라미터 이름 감지를 꺼서 Jackson 2와 같은 경로를 타게 한다. 운영 Mapper를 이 builder로 만든 이유다.

---

## 5. 차이를 어떻게 확인했나: DTO 스윕

차이가 있다는 것은 알았지만 **어느 DTO가 영향을 받는지**는 코드를 읽어서는 알 수 없었다. DTO가 수백 개였기 때문이다.

그래서 모든 DTO에 대해 두 Mapper의 결과를 비교하는 방식으로 확인했다. 아이디어는 단순하다.

{% raw %}
```java
// 개념 예시: DTO마다 같은 입력을 두 Mapper로 읽고 결과를 비교한다
JsonMapper expected = JsonMapper.builderWithJackson2Defaults().build();
JsonMapper actual   = JsonMapper.builder().build();

for (Class<?> dto : dtoClasses) {
    String json = sampleJsonFor(dto);   // 필드 일부만 채운 JSON
    Object a = expected.readValue(json, dto);
    Object b = actual.readValue(json, dto);
    if (!expected.writeValueAsString(a).equals(expected.writeValueAsString(b))) {
        report(dto);
    }
}
```
{% endraw %}

결과는 다음과 같았다.

| 대상 Mapper | DTO 577개 중 Jackson 2와 결과가 다른 수 |
|---|---|
| `builderWithJackson2Defaults()` 기반 운영 Mapper | 0 |
| 기본 Jackson 3 Mapper | 110 |

숫자가 보이면 판단이 쉬워진다. 110개를 DTO마다 고치는 방법도 있지만, **Mapper 기본값을 복원하는 쪽**이 훨씬 작은 변경이다. 이 결과로 운영 코드 변경 없이 Mapper 설정만으로 해결할 수 있다고 판단했다.

> 위 스윕 코드는 방식을 보이기 위한 예시다. 실제 비교에서는 샘플 JSON을 어떻게 만들지가 결과 품질을 좌우한다.

---

## 6. 예외 타입이 바뀌면 catch가 조용히 죽는다

두 번째로 중요한 변경은 예외다. `ObjectMapper.convertValue()`는 변환에 실패하면 Jackson 2에서 `IllegalArgumentException`을 던졌다. Jackson 3에서는 `JacksonException`을 던진다.

{% raw %}
```java
// Jackson 2 시절 코드
try {
    return mapper.convertValue(source, Target.class);
} catch (IllegalArgumentException e) {
    log.warn("convert failed", e);
    return null;
}
```
{% endraw %}

이 코드는 컴파일이 된다. 하지만 Jackson 3에서는 `JacksonException`이 `IllegalArgumentException`이 아니므로 catch를 지나쳐 호출자에게 올라간다. 컴파일러도 테스트도 알려주지 않는다. 코드 리뷰에서 발견한 문제였다.

{% raw %}
```java
try {
    return mapper.convertValue(source, Target.class);
} catch (IllegalArgumentException | JacksonException e) {
    log.warn("convert failed", e);
    return null;
}
```
{% endraw %}

비슷한 위험이 있는 곳도 함께 점검했다.

- `JsonNode.asText()`: null 노드와 컨테이너 노드에서 결과가 달라질 수 있다. 값 노드인지 먼저 확인하거나 기본값을 받는 `asText("")` 형태를 쓰도록 바꿨다.
- `fieldNames().forEachRemaining(...)`: Jackson 3에서는 `propertyNames()`가 `Collection<String>`을 돌려준다.
- 변환 호출 앞에 이미 검증이 있는 곳은 그대로 뒀다.

`JsonProcessingException`을 잡던 코드는 컴파일 오류로 드러난다. 반대로 **`IllegalArgumentException`을 잡던 코드는 드러나지 않는다**. `convertValue`, `treeToValue` 호출부를 grep으로 찾는 것이 좋다.

---

## 7. Jackson과 무관했지만 같이 드러난 것들

마이그레이션 중에 다음 항목도 함께 처리했다. Jackson 문제는 아니지만 Boot 4 업그레이드에서 자주 만날 수 있다.

| 증상 | 원인 | 대응 |
|---|---|---|
| 설정 키가 조용히 무시됨 | 에러 페이지 설정 `server.error.*`가 `spring.web.error.*`로 이동 | 설정 키를 새 메타데이터와 대조 |
| `NoClassDefFoundError` | 직접 고정한 kotlin-stdlib 버전이 BOM과 충돌 | 고정 제거, BOM에 맡김 |
| 컨테이너 기동 실패 | 공유 `EntityManager` 빈이 autowire 후보가 아니어서 생성자 주입 실패 | `SharedEntityManagerCreator`로 명시 빈 등록 |
| 보안 목적 버전 고정이 다운그레이드가 됨 | 서버·네트워크 라이브러리 버전 고정이 새 BOM보다 낮음 | 새 BOM 기준으로 재판정 |

특히 세 번째 항목은 단위 테스트가 잡지 못했다. 테스트가 모두 `MOCK` 웹 환경이라 내장 Tomcat 초기화 경로를 거치지 않았기 때문이다. Boot 4에서는 서블릿 컨테이너 초기화가 이 빈들을 먼저 만들면서 문제가 드러났다. 이후 `RANDOM_PORT`로 기동하는 테스트를 하나 추가했다.

---

## 8. 정리

Jackson 3 마이그레이션에서 확인한 것을 체크리스트로 줄이면 다음과 같다.

- [ ] import 치환 후 Mapper 빈을 `builderWithJackson2Defaults()` 기반으로 재정의했는가
- [ ] 자동 구성 Mapper가 물러나는 조건을 사용 중인 버전에서 확인했는가
- [ ] `WebClient`, `RestClient`의 기본 코덱이 Jackson 3 기본값을 쓰고 있지 않은가
- [ ] 코드 안의 `new ObjectMapper()`, `WebClient.create()` 호출을 찾았는가
- [ ] `catch (IllegalArgumentException)`으로 `convertValue` 실패를 처리하는 곳이 있는가
- [ ] DTO 역직렬화 결과를 두 Mapper로 비교해 보았는가
- [ ] 새로 작성하는 코드가 기본 Mapper를 쓰지 않도록 규칙을 남겼는가

마지막 항목이 중요하다. 기본 Jackson 3 Mapper를 쓰는 코드는 앞으로도 쉽게 추가된다. 새 코드는 앱 Mapper 빈을 주입받거나 `builderWithJackson2Defaults()`로 시작한다는 규칙을 문서나 리뷰 기준에 남겨 두는 것이 좋다.

이번 검증의 한계도 적어 둔다. 전체 단위 테스트와 개발 환경 기동은 확인했지만, API 응답 JSON이 3.5 때와 완전히 같은지, 재시도 AOP나 쿼리 DSL이 실제 데이터에서 동일하게 동작하는지는 별도 점검이 필요하다. 기동 성공이 동작 동일을 뜻하지는 않는다.
