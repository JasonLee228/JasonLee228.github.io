---
title: "Spring Boot 4 STOMP 메시지의 JSON 설정은 어디서 오나: WebSocket 메시지 변환기와 JsonMapper 빈"
date: 2026-11-06 18:40:00 +0900
categories: ["Spring", "웹서비스"]
tags: ["spring-boot", "stomp", "websocket", "jackson", "자동구성"]
permalink: /posts/spring-boot-4-stomp-메시지의-json-설정은-어디서-오나-websocket-메시지-변환기와-jsonmapper-빈/
---

## 리뷰에서 나온 질문

STOMP로 내려보내는 상태 메시지에 새 필드를 추가하는 변경을 리뷰받았다. 리뷰어가 물었다.

> 이 필드가 `null`일 때 STOMP 메시지에 `"reason":null`로 나가나, 아니면 빠지나? REST 응답은 `NON_NULL`로 빠지는데 WebSocket 쪽도 같은 설정을 타는지 확인했나?

REST는 `JsonMapper` 빈에 `NON_NULL`을 걸어 두었으니 빠진다. 그런데 STOMP 메시지 변환기가 **그 빈을 쓰는지**는 당연하지 않다. Spring Framework의 WebSocket 메시지 브로커 설정은 기본적으로 자기 변환기를 만들기 때문이다.

답은 Spring Boot 자동 구성 소스에 있다.

---

## Boot 4.1의 WebSocketMessagingAutoConfiguration

`spring-boot-websocket` 4.1.1의 `WebSocketMessagingAutoConfiguration`에서 Jackson 3 부분만 보면 이렇다.

{% raw %}
```java
@AutoConfiguration(afterName = {
        "org.springframework.boot.jackson.autoconfigure.JacksonAutoConfiguration",
        "org.springframework.boot.jackson2.autoconfigure.Jackson2AutoConfiguration" })
@ConditionalOnWebApplication(type = Type.SERVLET)
@ConditionalOnClass({ WebSocketMessageBrokerConfigurer.class,
        DelegatingWebSocketMessageBrokerConfiguration.class })
@ConditionalOnBean(DelegatingWebSocketMessageBrokerConfiguration.class)
public final class WebSocketMessagingAutoConfiguration {

    @Order(1)
    @Configuration(proxyBeanMethods = false)
    @ConditionalOnProperty(name = "spring.websocket.messaging.preferred-json-mapper",
            havingValue = "jackson", matchIfMissing = true)
    @ConditionalOnBean(JsonMapper.class)
    @ConditionalOnClass(JsonMapper.class)
    static class JacksonWebSocketMessageConverterConfiguration
            implements WebSocketMessageBrokerConfigurer {

        private final JsonMapper jsonMapper;

        JacksonWebSocketMessageConverterConfiguration(JsonMapper jsonMapper) {
            this.jsonMapper = jsonMapper;
        }

        @Override
        public boolean configureMessageConverters(List<MessageConverter> messageConverters) {
            JacksonJsonMessageConverter converter = new JacksonJsonMessageConverter(this.jsonMapper);
            DefaultContentTypeResolver resolver = new DefaultContentTypeResolver();
            resolver.setDefaultMimeType(MimeTypeUtils.APPLICATION_JSON);
            converter.setContentTypeResolver(resolver);
            messageConverters.add(converter);
            return false;
        }
    }
    ...
}
```
{% endraw %}

세 줄만 읽으면 된다.

1. 생성자가 **`JsonMapper` 빈을 주입**받는다. 이 빈은 `JacksonAutoConfiguration`이 만들거나, 우리가 `@Bean`으로 정의한 그 빈이다. `afterName`으로 Jackson 자동 구성 뒤에 실행되도록 순서를 잡는다.
2. 그 빈으로 `JacksonJsonMessageConverter`를 만들어 변환기 목록에 넣는다.
3. **`return false`**. 이 반환값은 "Framework 기본 변환기를 추가로 등록하지 말라"는 뜻이다. `true`를 돌려주면 Framework가 자기 기본 Jackson 변환기(새 mapper)를 뒤에 또 붙인다.

그래서 `JsonMapper` 빈에 `NON_NULL`을 걸었다면 STOMP 메시지에서도 `null` 필드가 빠진다. REST와 WebSocket이 **같은 mapper 인스턴스**를 쓴다.

---

## 조건이 셋 있다

위 설정이 적용되려면 다음이 모두 맞아야 한다.

**`spring.websocket.messaging.preferred-json-mapper`가 `jackson`이거나 비어 있다.** 기본값이다. Jackson 2를 계속 쓰는 프로젝트가 `jackson2`로 바꾸면 아래의 `Jackson2WebSocketMessageConverterConfiguration`이 대신 켜진다. 그쪽은 `ObjectMapper` 빈을 주입받아 `MappingJackson2MessageConverter`를 만든다. 구조는 같고 mapper만 다르다. Boot 4.0부터 deprecated다.

**`JsonMapper` 빈이 있다.** `JacksonAutoConfiguration`이 기본으로 만든다. 단, 우리가 `JsonMapper`를 `@Bean`으로 직접 정의하면 자동 구성 빈은 물러나고 우리 빈이 STOMP까지 간다. 이전 글 [Spring Boot 4로 올릴 때 Jackson 3 기본값이 바꾸는 역직렬화 결과](/posts/spring-boot-4로-올릴-때-jackson-3-기본값이-바꾸는-역직렬화-결과/)에서 다룬 "mapper 빈을 직접 정의하면 자동 구성이 물러난다"가 여기서도 그대로 적용된다.

**`DelegatingWebSocketMessageBrokerConfiguration` 빈이 있다.** `@EnableWebSocketMessageBroker`를 붙였다는 뜻이다.

---

## 우리 설정이 이걸 덮어쓰지 않았나

자동 구성이 변환기를 넣어도, 우리 `WebSocketMessageBrokerConfigurer`가 `configureMessageConverters`를 **재정의**하면 결과가 달라질 수 있다.

{% raw %}
```java
@Configuration
@EnableWebSocketMessageBroker
public class StompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public boolean configureMessageConverters(List<MessageConverter> converters) {
        converters.add(new JacksonJsonMessageConverter());   // 새 mapper. NON_NULL 없음
        return true;                                          // Framework 기본 변환기까지 추가
    }
}
```
{% endraw %}

이렇게 쓰면 변환기가 여러 개가 되고, 어느 것이 먼저 잡히는지는 configurer의 `@Order`와 목록 순서에 달린다. 자동 구성 쪽은 `@Order(1)`이다. 리뷰에서는 우리 프로젝트의 configurer가 이 메서드를 재정의하지 않는 것을 먼저 확인했다. 그래야 "자동 구성이 넣은 변환기 하나"라고 말할 수 있다.

### 소스로 확인하는 것이 빠르다

이런 질문은 문서보다 소스가 빠르다. 로컬 Maven 저장소에는 sources jar가 함께 받아져 있는 경우가 많다.

{% raw %}
```bash
unzip -p ~/.m2/repository/org/springframework/boot/spring-boot-websocket/4.1.1/spring-boot-websocket-4.1.1-sources.jar \
  org/springframework/boot/websocket/autoconfigure/servlet/WebSocketMessagingAutoConfiguration.java \
  | sed -n 60,120p
```
{% endraw %}

Boot 4부터 자동 구성이 모듈별로 쪼개져 `spring-boot-autoconfigure` 하나가 아니라 `spring-boot-websocket` 같은 개별 jar에 들어 있다. 클래스 이름으로 jar를 찾을 때 참고한다.

---

## Boot 3과 다른 점

Boot 3.5.9의 같은 클래스(`spring-boot-autoconfigure`의 `WebSocketMessagingAutoConfiguration`)도 구조는 같다. `ObjectMapper` 빈을 주입받아 `MappingJackson2MessageConverter`를 만들고 `return false`다. 그러니 "STOMP가 전역 mapper를 쓴다"는 사실은 Boot 3에서도 참이었다.

달라진 것은 두 가지다.

- mapper가 Jackson 2 `ObjectMapper`에서 Jackson 3 `JsonMapper`로 바뀌었다. Boot 4 전환 때 `JsonMapper` 빈을 새로 정의했다면, 그 설정이 REST뿐 아니라 STOMP에도 적용된다는 점을 같이 확인해야 한다.
- `spring.websocket.messaging.preferred-json-mapper` 속성이 생겼다. Jackson 2를 유지하는 프로젝트는 이 값을 `jackson2`로 두어야 Jackson 2 변환기가 선택된다. classpath에 Jackson 3이 없으면(`tools.jackson.databind.json.JsonMapper` 클래스 부재) 속성 없이도 Jackson 2 쪽이 켜진다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 질문 | STOMP 메시지의 JSON 직렬화 설정(`NON_NULL` 등)이 REST와 같은가 |
| 답 | 같다. 자동 구성이 `JsonMapper` 빈을 `JacksonJsonMessageConverter`에 직접 주입하고 `return false`로 기본 변환기 추가를 막는다 |
| 조건 1 | `spring.websocket.messaging.preferred-json-mapper`가 `jackson`(기본) |
| 조건 2 | `JsonMapper` 빈 존재. 직접 정의한 빈이 있으면 그 빈이 쓰임 |
| 조건 3 | 우리 configurer가 `configureMessageConverters`를 재정의하지 않음 |
| Boot 3 | 같은 구조. mapper만 `ObjectMapper` |
| 확인 | sources jar를 `unzip -p`로 열어 본다 |

Spring Boot 4.1.1(`spring-boot-websocket`), Spring Framework 7.0.9, Jackson 3.1.5 기준이다. 실제로 STOMP 클라이언트를 붙여 `null` 필드가 빠지는 것을 패킷으로 확인하지는 않았다. 소스 분석과 자동 구성 조건 확인까지다.
