---
title: "java.net.URL 생성자 deprecated(JDK 20) 대응: 바로 바꾸지 않고 관찰하며 옮기기"
date: 2026-11-16 18:20:00 +0900
categories: ["Java", "API"]
tags: ["java", "url", "uri", "jdk25", "마이그레이션"]
permalink: /posts/java-net-url-생성자-deprecated-대응-바로-바꾸지-않고-관찰하며-옮기기/
---

## 경고가 생겼다

JDK 17에서 25로 올린 뒤 빌드에 deprecation 경고가 생겼다.

{% raw %}
```text
warning: [deprecation] URL(String) in URL has been deprecated
```
{% endraw %}

`java.net.URL`의 public 생성자는 **JDK 20부터 전부** deprecated다. reflection으로 annotation을 보면 6개 모두 `since="20"`이다.

{% raw %}
```text
public java.net.URL(java.lang.String) since=20
public java.net.URL(java.lang.String,java.lang.String,int,java.lang.String) since=20
public java.net.URL(java.lang.String,java.lang.String,java.lang.String) since=20
public java.net.URL(java.net.URL,java.lang.String) since=20
... (6개 모두)
```
{% endraw %}

이유는 `URL` 생성자가 입력을 거의 검증하지 않기 때문이다. 공식 대안은 `URI`로 파싱한 뒤 `toURL()`을 부르는 것이다.

{% raw %}
```java
URL url = URI.create(s).toURL();   // 또는 new URI(s).toURL()
```
{% endraw %}

한 줄짜리 치환처럼 보인다. 실제로는 **허용하는 입력이 다르다.**

---

## 무엇이 달라지나

JDK 25(Corretto 25.0.5)에서 같은 입력을 `new URL(s)`와 `new URI(s).toURL()` 두 방식으로 돌렸다. `URI.create(s).toURL()`도 함께 돌렸는데 결과는 표 아래에 따로 적었다.

| 입력 | `new URL(s)` | `new URI(s).toURL()` |
|---|---|---|
| `http://a.com/a/b` | OK | OK |
| `http://my_host.com/x` | OK | OK |
| `http://한글.com/경로` | OK | OK |
| `http://a.com/path with space` | OK, path=`/path with space` | `URISyntaxException: Illegal character in path at index 17` |
| `http://a.com/x\|y` | OK | `URISyntaxException: Illegal character in path` |
| `http://a.com/{id}` | OK | `URISyntaxException: Illegal character in path` |
| `http://a.com/%ZZ` | OK | `URISyntaxException: Malformed escape pair` |
| `example.com/x` | `MalformedURLException: no protocol` | `IllegalArgumentException: URI is not absolute` |
| `foo://a.com/x` | `MalformedURLException: unknown protocol: foo` | 같음 |

`URI.create(s).toURL()`은 `URISyntaxException` 대신 `IllegalArgumentException`을 던진다는 점만 다르고 판정은 같다.

차이는 두 종류다.

1. **RFC를 어긴 path를 `URL`은 받고 `URI`는 거부한다.** 공백, `|`, `{}`, 잘못된 `%` 인코딩이 그렇다.
2. **예외 타입이 바뀐다.** scheme이 없는 입력에서 `URL`은 `MalformedURLException`(checked)을 던졌다. `URI` 경로는 `IllegalArgumentException`(unchecked)을 던진다. 기존 코드가 `catch (MalformedURLException e)`로 "잘못된 주소면 기본값" 처리를 했다면, 이 입력은 더 이상 잡히지 않고 위로 올라간다.

---

## 비표준 입력을 지켜 줘야 하나

처음 든 생각은 "RFC를 어긴 URL을 왜 받아 주나"였다. 맞는 말이지만 판단에 필요한 정보가 없었다.

- 이 문자열은 사용자가 입력한 정책 URL, 외부에서 들어온 요청 URL 등 여러 곳에서 온다.
- 설치형 고객 환경이 있어서 실제로 어떤 값이 들어오는지 모은 적이 없다.
- 기존 동작을 바꾸면 "어제까지 되던 정책이 오늘 안 맞는다"가 된다. 이것은 조용히 생기는 장애다.

그래서 바로 엄격하게 바꾸지 않았다. **RFC 입력은 새 방식으로, 비표준 입력은 경고를 남기고 기존 방식으로** 처리했다.

---

## 구현: URI 우선, 실패하면 warn 후 fallback

{% raw %}
```java
// TODO java.net.URL 생성자 deprecated 대응: [NON_RFC_URL] warn이 더 이상 나오지 않으면 fallback 삭제
@SuppressWarnings("deprecation")
public static URL toUrl(String url) throws MalformedURLException {
    String reason;
    int index;
    try {
        return new URI(url).toURL();
    } catch (URISyntaxException e) {
        reason = e.getReason();
        index = e.getIndex();
    } catch (IllegalArgumentException e) {
        reason = e.getMessage();
        index = -1;
    }

    URL legacyUrl = new URL(url);   // 기존 동작 유지. 이것도 실패하면 예전처럼 MalformedURLException
    log.warn("[NON_RFC_URL] reason={}, index={}, url={}", reason, index, removeQuery(url));
    return legacyUrl;
}
```
{% endraw %}

설계에서 신경 쓴 점과 주의할 점은 다섯 가지다.

- **`URI`가 거부한 입력만 fallback한다.** 정상 입력은 deprecated 경로를 타지 않는다.
- **예외 계약을 지킨다.** `URI`가 거부하고 `URL`도 거부하는 입력(예: scheme 없음)은 warn 없이 예전과 같은 `MalformedURLException`을 던진다. 호출부의 `catch`가 그대로 동작한다.
- **warn에는 query를 뺀 URL만 남긴다.** query에 토큰이나 개인정보가 있을 수 있다.
- **TODO에 제거 조건을 쓴다.** "언젠가 정리"가 아니라 "이 로그가 더 이상 안 나오면 삭제"다.
- **`null` 입력은 계약이 바뀐다.** `new URL(null)`은 `MalformedURLException`을 던지지만 `new URI(null)`은 `NullPointerException`을 던진다. 위 코드는 NPE를 잡지 않으므로 `toUrl(null)`은 NPE가 된다. 호출부가 `null`을 먼저 거르는지 확인하거나, 첫 줄에서 `null`이면 `MalformedURLException`을 던지게 한다.

로그 없이 fallback만 타게 두지 않고 warn을 남긴 이유도 있다. 우리 프런트엔드가 인코딩하지 않은 값을 보내는 경우도 이 로그로 잡을 수 있다.

---

## 테스트: 바뀌면 안 되는 것을 고정한다

테스트는 "새 방식이 기존과 같은 값을 주는가"를 비교한다.

{% raw %}
```java
@ParameterizedTest
@ValueSource(strings = {
        "http://example.com/a/b",
        "https://a.com:8443/p?q=1#f",
        "http://my_host.com/x",
        "http://*.example.com",
        "http://한글.com/경로",
        "http://[::1]:80/x"
})
void toUrlShouldMatchLegacyUrlForRfcUrl(String url) throws MalformedURLException {
    URL legacy = legacyUrl(url);
    URL result = UrlUtils.toUrl(url);

    assertEquals(legacy.getProtocol(), result.getProtocol());
    assertEquals(legacy.getHost(), result.getHost());
    assertEquals(legacy.getPort(), result.getPort());
    assertEquals(legacy.getPath(), result.getPath());
    assertEquals(legacy.getFile(), result.getFile());
}

@ParameterizedTest
@ValueSource(strings = {
        "http://a.com/path with space",
        "http://a.com/x|y",
        "http://a.com/{id}",
        "http://a.com/%ZZ"
})
void toUrlShouldFallbackForNonRfcPath(String url) throws MalformedURLException {
    assertEquals("a.com", UrlUtils.toUrl(url).getHost());
}

@Test
void toUrlShouldThrowWhenSchemeIsMissing() {
    assertThrows(MalformedURLException.class, () -> UrlUtils.toUrl("example.com/x"));
}
```
{% endraw %}

마지막 테스트가 중요하다. `URI` 경로만 쓰면 이 입력은 `IllegalArgumentException`이 된다. 호출부 계약이 깨지는 것을 이 테스트가 잡는다.

인자 3개짜리 생성자 `new URL(protocol, host, file)`로 `www.` 변형 주소를 만들던 곳은 문자열 결합으로 바꾼 뒤 `toUrl`에 넘겼다.

---

## 정리

| 항목 | 내용 |
|---|---|
| deprecated 범위 | `java.net.URL` public 생성자 전부, `since="20"` |
| 공식 대안 | `new URI(s).toURL()` / `URI.create(s).toURL()` |
| 달라지는 것 | RFC 위반 path(공백, `\|`, `{}`, 잘못된 `%`)를 거부. scheme 없음은 `IllegalArgumentException`으로 바뀜 |
| 이번 전략 | URI 우선. 실패하면 `[NON_RFC_URL]` warn 후 기존 `URL`로 fallback. 둘 다 실패하면 기존 예외 |
| 제거 조건 | warn이 더 이상 나오지 않으면 fallback 삭제(TODO) |
| 주의 | `null` 입력은 `MalformedURLException`에서 `NullPointerException`으로 바뀜 |
| 테스트 | RFC 입력은 기존과 같은 결과, 비표준은 fallback, scheme 없음은 기존 예외 |

입력별 동작 표는 Corretto 25.0.5에서 직접 돌린 결과다. 관찰 기간은 정하지 않았다. 설치형 환경까지 로그가 모여야 판단할 수 있어서다.
