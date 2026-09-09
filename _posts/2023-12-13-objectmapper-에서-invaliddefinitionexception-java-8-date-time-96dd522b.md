---
title: "ObjectMapper 에서 InvalidDefinitionException: Java 8 date/time type 오류가 발생할 경우"
date: 2023-12-13 06:38:27 +0000
categories: ["Spring-Boot"]
---

ObjectMapper 에서는 날짜 타입을 처리하기 위해 별도의 라이브러리를 포함해 주어야 하는데, jsr310 라이브러리가 바로 그것이다.

#### 라이브러리 의존성 추가

Jackson-datatype-jsr310 의존성 추가: ObjectMapper가 Java 8의 날짜/시간 타입을 인식할 수 있도록 하려면, Jackson-datatype-jsr310 의존성을 추가해야 합니다. 

- maven

{% raw %}
```java
<dependency>
    <groupId>com.fasterxml.jackson.datatype</groupId>
    <artifactId>jackson-datatype-jsr310</artifactId>
    <version>2.13.3</version>
</dependency>
```
{% endraw %}

- gradle

{% raw %}
```java
dependencies {
    implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310:2.13.3'
}
```
{% endraw %}

* 버전은 최신 버전 또는 자바 버전에 알맞는 버전 사용

#### 라이브러리를 추가만 하면 되는가?

단순히 의존성만 추가한다고 ObjectMapper 에서 날짜 타입 등을 바로 처리할 수 있게 되는 것은 아니다. ObjectMapper 생성 이후 별도의 설정을 해 주어야 한다.

{% raw %}
```java
ObjectMapper mapper = new ObjectMapper();

mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
mapper.registerModule(new JavaTimeModule());
mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
```
{% endraw %}

- **각 설정 설명**

- `mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);`
    - 직렬화할 때 null 값을 포함하지 않도록 설정합니다. 즉, 객체의 필드 값이 null이면 JSON 출력에 포함되지 않습니다.

    - 예시**:**
          - 객체 `{ "name": "John", "age": null }`

          - JSON 출력: `{ "name": "John" }`

- `mapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);`
    - JSON 데이터에 정의되지 않은 필드가 존재하더라도 오류를 발생시키지 않도록 설정합니다.

    - 예시**:**
          - JSON 데이터: `{ "name": "John", "unknownField": "value" }`

          - 객체: `{ "name": "John" }`

- `mapper.registerModule(new JavaTimeModule());`
    - Java 8의 `java.time` 패키지에서 제공되는 날짜 및 시간 클래스를 JSON으로 변환 및 역변환할 수 있도록 `jackson-datatype-jsr310` 모듈을 등록합니다.

    - 예시**:**
          - 객체: `{ "date": LocalDateTime.now() }`

          - JSON 출력: `{ "date": "2023-12-12T15:44:00" }`

- `mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);`
    - `java.time` 클래스를 밀리초 타임스탬프 대신 ISO 8601 형식의 문자열로 직렬화하도록 설정합니다.

    - 예시**:**
          - 객체: `{ "date": LocalDateTime.now() }`

          - JSON 출력: `{ "date": "2023-12-12T15:44:00" }`

          - (WRITE_DATES_AS_TIMESTAMPS 옵션 활성화 시)

          - JSON 출력: `{ "date": 1713101440000 }`
