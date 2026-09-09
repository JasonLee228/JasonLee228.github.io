---
title: "@Builder, ObjectMapper 역직렬화에서 같은 기본값 사용하기"
date: 2026-03-26 01:49:24 +0000
categories: ["Spring", "활용"]
tags: ["활용", "spring"]
---

### 기본값 설정 방법

본론에 들어가기 전에, Builder와 ObjectMapper에서 기본값을 다루는 기본적인 방법부터 정리한다.

#### Builder에서 기본값 설정하는 방법

Lombok `@Builder`만 사용하면 Builder의 각 메서드를 호출하지 않은 필드는 모두 `null`(또는 원시 타입의 기본값)이 된다.

{% raw %}
```java
@Builder
public class OrderDto {
    private String status;
    private int retryCount;
}

// 기본값 없이 build → null, 0
OrderDto dto = OrderDto.builder().build();
// dto.getStatus()     → null
// dto.getRetryCount() → 0
```
{% endraw %}

`@Builder.Default` 를 사용하면 Builder에서 값을 설정하지 않은 필드에 기본값을 지정할 수 있다.

{% raw %}
```java
@Builder
public class OrderDto {
    @Builder.Default private String status      = "PENDING";
    @Builder.Default private int    retryCount  = 3;
    @Builder.Default private boolean notifyUser = true;
}

// 아무것도 설정하지 않으면 기본값 사용
OrderDto dto1 = OrderDto.builder().build();
// status = "PENDING", retryCount = 3, notifyUser = true

// 일부만 명시적으로 설정하면 나머지는 기본값 유지
OrderDto dto2 = OrderDto.builder()
    .status("PROCESSING")
    .build();
// status = "PROCESSING", retryCount = 3 (기본값 유지)
```
{% endraw %}

> **주의**: `@Builder.Default`를 선언하면 Lombok이 필드 초기화 코드를 Builder 내부로 옮긴다.

---

#### ObjectMapper에서 기본값을 다루는 방법들

Jackson ObjectMapper로 JSON 또는 Map을 역직렬화할 때, 누락된 필드에 기본값을 부여하는 방법은 여러 가지가 있다.

#### 방법 1: 필드 초기화 (가장 단순)

{% raw %}
```java
public class OrderDto {
    private String status = "PENDING";  // 필드 선언과 함께 초기화
    private int retryCount = 3;
}

// ObjectMapper는 no-args 생성자 호출 후 필드를 주입한다.
// JSON에 없는 키는 생성자 시점의 초기값이 그대로 유지된다.
String json = """{ "retryCount": 5 }""";
OrderDto dto = objectMapper.readValue(json, OrderDto.class);
// status = "PENDING" (초기값 유지), retryCount = 5 (JSON 값 적용)
```
{% endraw %}

**한계**: `@Builder.Default`와 함께 사용하면 동작하지 않는다. Lombok이 필드 초기화 코드를 제거하기 때문이다.

#### 방법 2: `@JsonProperty` + `defaultValue` (문서용, 런타임 미적용)

{% raw %}
```java
public class OrderDto {
    @JsonProperty(defaultValue = "PENDING")  // 문서/스키마 생성 목적
    private String status;
}
```
{% endraw %}

> **주의**: `@JsonProperty`의 `defaultValue`는 **런타임 역직렬화에 적용되지 않는다**.

#### 방법 3: `@JsonSetter(nulls = Nulls.SKIP)`

{% raw %}
```java
public class OrderDto {
    private String status = "PENDING";

    @JsonSetter(nulls = Nulls.SKIP)  // JSON 값이 null이면 setter를 건너뜀
    public void setStatus(String status) {
        this.status = status;
    }
}
```
{% endraw %}

JSON 키가 아예 없으면 필드 초기값이 유지되고, 키가 있지만 값이 `null`이어도 초기값이 유지된다.

{% raw %}
```json
{ "status": null }  // → status = "PENDING" (null 주입 건너뜀)
```
{% endraw %}

#### 방법 4: Builder 경유 역직렬화 (`@JsonDeserialize` + `@JsonPOJOBuilder`)

`@Builder.Default` 기본값을 ObjectMapper 역직렬화에도 적용하고 싶을 때 사용하는 방법이며, 이 글의 핵심 주제다.

{% raw %}
```java
@Builder
@JsonDeserialize(builder = OrderDto.OrderDtoBuilder.class)
public class OrderDto {
    @Builder.Default private String status     = "PENDING";
    @Builder.Default private int    retryCount = 3;

    @JsonPOJOBuilder(withPrefix = "")
    public static class OrderDtoBuilder { }
}
```
{% endraw %}

ObjectMapper가 no-args 생성자 대신 Builder를 통해 객체를 생성하므로, `@Builder.Default` 기본값이 그대로 적용된다.

---

### 문제 상황

`@Builder`와 `@Builder.Default`로 DTO의 기본값을 선언했는데, **Builder로 생성할 때는 기본값이 잘 적용되지만 ObjectMapper로 역직렬화하면 **`null`**이 되는** 문제가 발생했다.

{% raw %}
```java
// 의도한 동작
NotificationPolicyDto dto = objectMapper.convertValue(map, NotificationPolicyDto.class);
dto.getEmailEnabled(); // "ON" 을 기대했지만 → null
```
{% endraw %}

이 글에서는 이 문제가 발생하는 이유와, Builder와 ObjectMapper 양쪽에서 모두 기본값이 동작하도록 만드는 방법을 단계별로 설명한다.

---

### 1단계: 문제의 원인 파악

#### Lombok `@Builder.Default` 의 동작 방식

`@Builder.Default`를 선언하면 Lombok은 다음과 같은 코드를 **컴파일 타임에 생성**한다.

{% raw %}
```java
// 우리가 작성한 코드
@Builder
public class NotificationPolicyDto {
    @Builder.Default
    private String emailEnabled = "ON";
}

// Lombok이 생성하는 실제 바이트코드 (개념적 표현)
public class NotificationPolicyDto {
    private String emailEnabled;

    public static class NotificationPolicyDtoBuilder {
        private boolean emailEnabled$set = false;   // 명시적 설정 여부 추적 플래그
        private String  emailEnabled$value;

        public NotificationPolicyDtoBuilder emailEnabled(String val) {
            this.emailEnabled$value = val;
            this.emailEnabled$set = true;
            return this;
        }

        public NotificationPolicyDto build() {
            // 플래그가 false이면 기본값 "ON" 사용
            String emailEnabled = this.emailEnabled$set
                ? this.emailEnabled$value
                : "ON";
            return new NotificationPolicyDto(emailEnabled);
        }
    }
}
```
{% endraw %}

핵심은 기본값 로직이 **Builder의 **`build()`** 메서드 안에만** 존재한다는 것이다.

#### ObjectMapper의 기본 역직렬화 전략

Jackson ObjectMapper는 별도 설정이 없으면 다음 순서로 객체를 생성한다.

{% raw %}
```text
1. no-args 생성자 호출 → 빈 객체 생성
2. JSON/Map의 각 키에 대응하는 setter 또는 필드에 값 주입
3. JSON/Map에 없는 키 → 주입하지 않음 (필드는 생성자 시점의 초기값 유지)
```
{% endraw %}

`@Builder.Default`를 사용하면 Lombok이 필드 초기화 코드를 **필드 선언부에서 제거하고 Builder 내부로 옮긴다**. 따라서 no-args 생성자로 객체를 만들면 해당 필드는 `null`이 된다.

{% raw %}
```java
// @Builder.Default 사용 시 Lombok이 필드 초기값을 제거함
// 아래는 컴파일 후 no-args 생성자의 실질적 동작
public NotificationPolicyDto() {
    // emailEnabled 초기화 없음 → null
}
```
{% endraw %}

**결론**: ObjectMapper가 no-args 생성자를 사용하는 한, `@Builder.Default` 기본값은 절대 적용되지 않는다.

---

### 2단계: 해결 전략

ObjectMapper가 no-args 생성자 대신 **Builder를 통해 객체를 생성하도록** 강제하면 된다.

Jackson은 `@JsonDeserialize(builder = ...)` 어노테이션으로 이를 지원한다.

{% raw %}
```text
기존: ObjectMapper → no-args 생성자 → @Builder.Default 무시 → null
변경: ObjectMapper → Builder → build() 호출 → @Builder.Default 적용 → "ON"
```
{% endraw %}

---

### 3단계: 구현

#### 전체 코드

{% raw %}
```java
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.annotation.JsonPOJOBuilder;
import lombok.*;

@Getter
@Setter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@JsonDeserialize(builder = NotificationPolicyDto.NotificationPolicyDtoBuilder.class) // ①
public class NotificationPolicyDto {

    @Builder.Default private String emailEnabled   = "ON"; // ②
    @Builder.Default private String smsEnabled     = "ON";
    @Builder.Default private String pushEnabled    = "ON";
    @Builder.Default private String slackEnabled   = "OFF";

    @JsonPOJOBuilder(withPrefix = "") // ③
    public static class NotificationPolicyDtoBuilder {
        // ④ 비워두면 Lombok이 구현을 채워줌
    }
}
```
{% endraw %}

#### 각 구성 요소 설명

#### ① `@JsonDeserialize(builder = ...Builder.class)`

클래스 레벨에 선언하여 Jackson에게 이 DTO를 역직렬화할 때 **지정된 Builder 클래스를 사용하라**고 지시한다.

{% raw %}
```java
// Jackson 내부의 역직렬화 흐름 (개념적 표현)
BuilderBasedDeserializer.deserialize(map) {
    NotificationPolicyDtoBuilder builder = new NotificationPolicyDtoBuilder();
    for (Entry<String, Object> entry : map.entrySet()) {
        // 각 키에 해당하는 Builder 메서드 호출
        builder.invoke(entry.getKey(), entry.getValue());
    }
    return builder.build(); // @Builder.Default 기본값 여기서 적용
}
```
{% endraw %}

#### ② `@Builder.Default private String field = "ON"`

Builder 패턴 사용 시 미설정 필드의 기본값을 지정한다.

ObjectMapper도 이제 Builder를 경유하므로, JSON/Map에 없는 키는 이 기본값을 사용한다.

#### ③ `@JsonPOJOBuilder(withPrefix = "")`

Jackson이 Builder 메서드를 찾을 때 사용할 **접두사 규칙**을 설정한다.

| `withPrefix` 값 | Jackson이 찾는 메서드명 | Lombok Builder 실제 메서드명 | 결과 |
| --- | --- | --- | --- |
| `"with"` (Jackson 기본) | `withEmailEnabled(...)` | `emailEnabled(...)` | ❌ 매핑 실패 |
| `""` (우리 설정) | `emailEnabled(...)` | `emailEnabled(...)` | ✅ 매핑 성공 |

#### ④ 빈 스텁(Stub) 클래스

`@JsonPOJOBuilder`를 **Lombok이 생성할 Builder 클래스에 직접 붙일 수 없다**. 소스코드 상에는 해당 클래스가 존재하지 않기 때문이다.

같은 이름의 스텁 클래스를 선언해두면, Lombok이 컴파일 타임에 해당 클래스 내부를 채워준다. 어노테이션은 스텁에 선언된 것이 유지된다.

{% raw %}
```text
컴파일 전 (소스코드)                 컴파일 후 (바이트코드)
────────────────────────           ──────────────────────────────────────────
@JsonPOJOBuilder(withPrefix="")    @JsonPOJOBuilder(withPrefix="")  ← 유지됨
public static class                public static class
  NotificationPolicyDtoBuilder {     NotificationPolicyDtoBuilder {
  // 비어있음                           // Lombok이 아래 내용을 생성
}                                      private boolean emailEnabled$set = false;
                                       private String  emailEnabled$value;

                                       public NotificationPolicyDtoBuilder
                                           emailEnabled(String val) { ... }

                                       public NotificationPolicyDto build() { ... }
                                   }
```
{% endraw %}

---

### 4단계: 동작 검증

#### Builder 사용 시

{% raw %}
```java
// 아무것도 설정하지 않으면 전부 기본값
NotificationPolicyDto dto1 = NotificationPolicyDto.builder().build();
// emailEnabled = "ON", smsEnabled = "ON", pushEnabled = "ON", slackEnabled = "OFF"

// 일부만 명시적으로 설정
NotificationPolicyDto dto2 = NotificationPolicyDto.builder()
    .emailEnabled("OFF")
    .build();
// emailEnabled = "OFF", smsEnabled = "ON" (기본값 유지)
```
{% endraw %}

#### ObjectMapper 사용 시

{% raw %}
```java
ObjectMapper objectMapper = new ObjectMapper();

// 케이스 1: 빈 Map → 모든 필드 기본값
Map<String, Object> emptyMap = new HashMap<>();
NotificationPolicyDto dto3 = objectMapper.convertValue(emptyMap, NotificationPolicyDto.class);
// emailEnabled = "ON", slackEnabled = "OFF"

// 케이스 2: 일부 키만 있는 Map
Map<String, Object> partialMap = Map.of("emailEnabled", "OFF");
NotificationPolicyDto dto4 = objectMapper.convertValue(partialMap, NotificationPolicyDto.class);
// emailEnabled = "OFF" (Map 값 적용), smsEnabled = "ON" (기본값 유지)

// 케이스 3: JSON 문자열 역직렬화
String json = """
    {
        "slackEnabled": "ON"
    }
    """;
NotificationPolicyDto dto5 = objectMapper.readValue(json, NotificationPolicyDto.class);
// emailEnabled = "ON" (기본값), slackEnabled = "ON" (JSON 값 적용)
```
{% endraw %}

---

### 정리: 전체 동작 원리 요약

{% raw %}
```text
┌─────────────────────────────────────────────────────────────────────┐
│                     역직렬화 요청 진입                               │
│         objectMapper.convertValue(map, NotificationPolicyDto.class) │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  @JsonDeserialize(builder = ...Builder.class) 감지                  │
│  → no-args 생성자 대신 Builder 전략으로 전환                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  새 Builder 인스턴스 생성                                            │
│  → @Builder.Default: 내부 플래그($set) 전부 false로 초기화           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Map/JSON의 각 키에 대해:                                            │
│  @JsonPOJOBuilder(withPrefix="") 규칙으로 Builder 메서드 찾기        │
│  → "emailEnabled" 키 → builder.emailEnabled("OFF") 호출             │
│  → 해당 필드의 $set 플래그 = true                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  builder.build() 호출                                               │
│  → $set = true 인 필드: 입력값 사용                                 │
│  → $set = false 인 필드: @Builder.Default 기본값 "ON" 사용           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  완성된 DTO 반환                                                     │
│  (Map에 없던 키는 모두 "ON", 있던 키는 Map의 값)                      │
└─────────────────────────────────────────────────────────────────────┘
```
{% endraw %}

#### 체크리스트

| 항목 | 적용 여부 | 효과 |
| --- | --- | --- |
| `@Builder.Default` | ✅ | Builder에서 미설정 필드 기본값 적용 |
| `@JsonDeserialize(builder = ...Builder.class)` | ✅ | ObjectMapper가 Builder 경유하도록 강제 |
| `@JsonPOJOBuilder(withPrefix = "")` | ✅ | Jackson ↔ Lombok Builder 메서드명 매핑 |
| 빈 스텁 내부 클래스 선언 | ✅ | `@JsonPOJOBuilder` 어노테이션 부착 대상 제공 |

---

### 주의 사항

`@NoArgsConstructor`**의 기본값**

`@Builder.Default` 적용 시 no-args 생성자로 생성한 객체의 해당 필드는 `null`이다. `@NoArgsConstructor(access = AccessLevel.PROTECTED)`로 외부 접근을 막아두면 실수를 방지할 수 있다.

`@AllArgsConstructor`**와의 관계**

`@AllArgsConstructor`는 모든 필드를 인자로 받으므로 기본값과 무관하게 동작한다. 팩토리 메서드 또는 테스트 코드에서 전체 필드를 명시적으로 주입할 때 사용한다.

**Spring **`@RequestBody`** 와의 호환성**

`HttpMessageConverter`도 내부적으로 ObjectMapper를 사용하므로, `@RequestBody`로 받는 JSON 요청에도 동일하게 기본값이 적용된다.
