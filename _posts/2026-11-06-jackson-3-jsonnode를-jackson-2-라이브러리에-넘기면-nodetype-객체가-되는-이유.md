---
title: "Jackson 3 JsonNode를 Jackson 2 라이브러리에 넘기면 {\"nodeType\":\"STRING\"} 객체가 되는 이유"
date: 2026-11-06 18:10:00 +0900
categories: ["Spring", "운영"]
tags: ["spring-boot", "jackson", "jsonnode", "마이그레이션"]
permalink: /posts/jackson-3-jsonnode를-jackson-2-라이브러리에-넘기면-nodetype-객체가-되는-이유/
---

## 토큰이 깨졌다

Spring Boot 4로 올린 뒤, 다른 프로세스가 우리 서비스에서 받아 쓰는 JWT 문자열이 깨졌다는 보고가 왔다. 저장소를 열어 보니 토큰 자리에 이런 값이 들어 있었다.

{% raw %}
```json
{"nodeType":"STRING","empty":true,"missingNode":false,"embeddedValue":false,"array":false,"null":false,"object":false,"valueNode":true,"textual":true,"string":true, ...}
```
{% endraw %}

문자열이어야 할 자리에 **JsonNode 객체의 getter 목록**이 들어갔다. 원인은 Jackson 버전 경계였다. 우리 서비스는 Jackson 3(`tools.jackson`)으로 요청을 읽었고, 값을 받아 저장하는 라이브러리는 Jackson 2(`com.fasterxml.jackson`)였다.

이전 글 [Spring Boot 4로 올릴 때 Jackson 3 기본값이 바꾸는 역직렬화 결과](/posts/spring-boot-4로-올릴-때-jackson-3-기본값이-바꾸는-역직렬화-결과/)는 한 프로세스 안의 기본값 변화를 다뤘다. 이 글은 **두 Jackson이 한 JVM에 공존할 때** 생기는 문제다.

---

## 재현

Jackson 3 databind 3.1.5와 Jackson 2 databind 2.21.7을 같은 classpath에 올렸다. 두 라이브러리는 패키지가 다르므로(`tools.jackson` / `com.fasterxml.jackson`) 충돌 없이 함께 로드된다. 이것이 문제의 전제다.

{% raw %}
```java
import tools.jackson.databind.json.JsonMapper;

JsonMapper j3 = JsonMapper.builder().build();
tools.jackson.databind.JsonNode tree = j3.readTree(
        "{\"token\":\"eyJhbGciOi...\",\"inspection\":\"ON\",\"count\":3}");
tools.jackson.databind.JsonNode tokenNode = tree.get("token");

// 값을 받아 저장하는 쪽은 Jackson 2다. 받은 Object를 valueToTree로 트리에 넣는다.
com.fasterxml.jackson.databind.ObjectMapper j2 = new com.fasterxml.jackson.databind.ObjectMapper();
System.out.println(j2.valueToTree(tokenNode));
```
{% endraw %}

출력:

{% raw %}
```text
{"nodeType":"STRING","empty":true,"missingNode":false,"embeddedValue":false,"array":false,"null":false,"object":false,"float":false,"floatingPointNumber":false,"bigDecimal":false,"valueNode":true,"integralNumber":false,"container":false,"bigInteger":false,"number":false,"short":false,"long":false,"int":false,"pojo":false,"double":false,"textual":true,"boolean":false,"binary":false,"string":true}
```
{% endraw %}

객체 노드를 통째로 넘겨도 같다. 필드 값은 사라지고 `{"empty":false,"object":true,"nodeType":"OBJECT",...}`만 남는다.

반대 방향도 똑같이 깨진다. Jackson 2 `JsonNode`를 Jackson 3 `valueToTree`에 넣으면 `{"array":false,"bigDecimal":false,...,"nodeType":"STRING",...}`가 나온다.

---

## 왜 이렇게 되나

Jackson은 직렬화할 객체의 타입을 보고 serializer를 고른다. 자기 쪽 `JsonNode`(`com.fasterxml.jackson.databind.JsonNode`)는 전용 serializer가 있어 **트리 그대로** 출력한다.

그런데 Jackson 3의 `JsonNode`는 `tools.jackson.databind.JsonNode`다. Jackson 2 입장에서는 **모르는 클래스**다. 모르는 클래스는 bean으로 취급한다. bean 직렬화는 `isXxx()`, `getXxx()`, Jackson 3에서 추가된 `asString()` 같은 public getter를 전부 훑어 프로퍼티로 만든다. 그래서 `nodeType`, `empty`, `textual`, `string` 같은 이름이 나온다. 실제 값은 getter 이름이 아니므로 어디에도 없다.

컴파일은 통과한다. 두 라이브러리 모두 `Object`를 받기 때문이다. 런타임 예외도 없다. 저장이 되고 읽을 때 문자열이 아니라 객체가 나올 뿐이다. 그래서 테스트 없이는 배포 뒤에야 드러난다.

---

## 어디서 섞이나

우리 코드에서는 이런 경로였다.

1. HTTP 요청 본문을 Jackson 3 `JsonNode`로 받는다. 키가 가변이라 DTO 대신 트리로 받았다.
2. 트리를 돌면서 `field.getValue()`를 라이브러리 메서드 `set(connectionId, key, Object value)`에 넘긴다.
3. 라이브러리는 Jackson 2 `ObjectMapper.valueToTree(value)`로 저장한다.

Spring Boot 3에서는 1번도 Jackson 2였다. 그래서 같은 코드가 그대로 동작했다. Boot 4로 올리면서 1번만 Jackson 3으로 바뀌었고, 2번의 `Object` 파라미터가 그 차이를 가렸다.

같은 함정이 생기는 자리는 더 있다.

- Jackson 2를 쓰는 외부 SDK, 메시징 클라이언트, 캐시 라이브러리에 `JsonNode`를 그대로 넘기는 곳
- 반대로 Jackson 2 라이브러리가 돌려준 `JsonNode`를 Boot 4의 `JsonMapper`로 응답에 싣는 곳
- `Map<String, Object>`에 `JsonNode`를 섞어 넣고 다른 Jackson으로 직렬화하는 곳

---

## 해결: 경계에서 일반 Java 값으로 바꾼다

가장 단순한 방법은 다른 Jackson에 넘기기 전에 **트리를 일반 Java 값으로 바꾸는 것**이다.

{% raw %}
```java
Object plain = j3.convertValue(tokenNode, Object.class);
// plain은 java.lang.String
System.out.println(j2.valueToTree(plain));   // "eyJhbGciOi..."

Object plainTree = j3.convertValue(tree, Object.class);
// plainTree는 java.util.LinkedHashMap
System.out.println(j2.valueToTree(plainTree));
// {"token":"eyJhbGciOi...","inspection":"ON","count":3}
```
{% endraw %}

`convertValue(node, Object.class)`는 노드 종류에 따라 `String`, `Integer`/`Long`, `Boolean`, `List`, `LinkedHashMap`, `null`을 돌려준다. 이 타입은 어느 Jackson이든 똑같이 직렬화한다.

수정은 라이브러리 호출 직전 한 줄이었다.

{% raw %}
```java
// 라이브러리는 Jackson 2라 Jackson 3 node를 bean으로 직렬화한다. 일반 Java 값으로 바꿔 넘긴다.
Object value = JSON_MAPPER.convertValue(field.getValue(), Object.class);
library.set(connectionId, List.of(field.getKey()), value);
```
{% endraw %}

문자열로 바꿔 넘기는 방법(`node.asString()`)도 있지만, 숫자·불리언·중첩 객체가 올 수 있는 자리라면 타입이 틀어진다. `Object.class` 변환이 범용이다.

### 회귀 테스트는 Jackson 2로 쓴다

고친 뒤 테스트는 **받는 쪽과 같은 Jackson 2**로 결과를 확인해야 의미가 있다.

{% raw %}
```java
ArgumentCaptor<Object> captor = ArgumentCaptor.forClass(Object.class);
verify(library).set(any(), any(), captor.capture());

com.fasterxml.jackson.databind.ObjectMapper j2 = new com.fasterxml.jackson.databind.ObjectMapper();
assertEquals("\"eyJhbGciOi...\"", j2.valueToTree(captor.getValue()).toString());
```
{% endraw %}

Jackson 3 mapper로 검사하면 `JsonNode`를 넘겨도 정상처럼 보인다. 그 mapper는 자기 노드를 알기 때문이다. 수정 전 코드에서 이 테스트가 실패하는 것을 먼저 확인했다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 증상 | 저장된 문자열이 `{"nodeType":"STRING","empty":true,...}` 객체로 바뀜 |
| 원인 | Jackson 3 `JsonNode`를 Jackson 2 `valueToTree`에 넘김. 모르는 클래스라 bean으로 직렬화 |
| 왜 조용한가 | 파라미터가 `Object`라 컴파일·런타임 모두 예외 없음 |
| 해결 | 경계에서 `convertValue(node, Object.class)`로 `String`/`Map`/`List` 등 일반 값으로 변환 |
| 테스트 | 받는 쪽 Jackson 2 `valueToTree` 결과를 단언. Jackson 3 mapper로 검사하면 통과해 버림 |
| 점검 대상 | Jackson 2 SDK·클라이언트에 `JsonNode`나 `Map<String,Object>`를 넘기는 모든 호출 |

재현은 JDK 25, Jackson 3 databind 3.1.5, Jackson 2 databind 2.21.7로 했다. Boot 3와 4 사이의 다른 Jackson 변경은 이전 글에 있다.
