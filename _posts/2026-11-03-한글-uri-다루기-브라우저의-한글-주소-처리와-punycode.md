---
title: "한글 URI 다루기: 브라우저의 한글 주소 처리와 Punycode"
date: 2026-11-03 09:20:00 +0900
categories: ["웹", "URL"]
tags: ["url", "idn", "punycode", "percent-encoding", "java"]
permalink: /posts/한글-uri-다루기-브라우저의-한글-주소-처리와-punycode/
---

## URI에는 원래 한글이 들어갈 수 없다

URI 문법(RFC 3986)은 ASCII 문자만 허용한다. 그런데 주소창에는 `https://한국.kr/경로?q=값`이 그대로 보인다.

브라우저가 보내기 전에 한글을 ASCII로 바꾸기 때문이다. 바꾸는 방식은 **위치에 따라 두 가지**다.

| 위치 | 변환 방식 | 결과 예 |
|---|---|---|
| host (도메인) | IDNA, Punycode | `한국.kr` 은 `xn--3e0b707e.kr` |
| path, query, fragment | UTF-8 바이트를 percent-encoding | `경로` 는 `%EA%B2%BD%EB%A1%9C` |

WHATWG URL 표준(브라우저가 따르는 URL 규칙)을 구현한 Node.js 22의 `URL`로 확인하면 이렇다.

{% raw %}
```js
const u = new URL("https://한국.kr/경로?q=값 1#조각");
u.href;
// https://xn--3e0b707e.kr/%EA%B2%BD%EB%A1%9C?q=%EA%B0%92%201#%EC%A1%B0%EA%B0%81
u.hostname;  // xn--3e0b707e.kr
u.pathname;  // /%EA%B2%BD%EB%A1%9C
```
{% endraw %}

주소창은 사람이 읽기 좋게 한글로 다시 보여 줄 뿐이다. 서버가 받는 `Host` 헤더와 요청 경로, 그리고 페이지 스크립트의 `location.hostname`은 모두 변환된 값이다.

---

## host: IDN과 Punycode

### IDN이란

IDN(Internationalized Domain Name, 국제화 도메인 이름)은 비ASCII 문자가 들어간 도메인이다. DNS는 ASCII만 다루므로, IDN은 label(점으로 나뉜 부분)마다 ASCII로 바꿔서 쓴다.

- 비ASCII 문자가 있는 label만 바꾼다. `한국.kr`에서 `kr`은 그대로다.
- 바꾼 label 앞에는 `xn--`를 붙인다. 이 접두어를 ACE prefix(ASCII Compatible Encoding 접두어)라고 한다.
- 바꾸는 알고리즘이 Punycode(RFC 3492)다.

### Punycode가 하는 일

Punycode는 유니코드 문자열을 `a-z`, `0-9`, `-`만으로 표현한다.

1. 원래 문자열의 ASCII 문자를 순서대로 앞에 그대로 둔다.
2. ASCII 문자가 있었으면 그 뒤에 구분자 `-`를 붙인다.
3. 비ASCII 문자의 코드 값과 위치를 정수 차이(delta)로 계산해 문자로 인코딩해 붙인다.

{% raw %}
```text
bücher   ->  bcher-kva        (ASCII "bcher" + "-" + ü 의 값과 위치)
한국     ->  3e0b707e         (ASCII 문자가 없어 구분자도 없다)
```
{% endraw %}

그래서 `bücher.de`는 `xn--bcher-kva.de`, `한국.kr`은 `xn--3e0b707e.kr`이 된다.

길이 제한은 변환 **뒤의** ASCII 기준이다. label 하나는 63자, 전체 도메인은 253자까지다. 한글은 한 글자가 여러 문자로 늘어나므로, 화면에서는 짧아 보여도 제한에 걸릴 수 있다.

{% raw %}
```text
한국인터넷정보센터.한국  ->  xn--3e0bx5euxnjje69i70af08bea817g.xn--3e0b707e
```
{% endraw %}

### 변환 전에 정규화가 먼저 있다

Punycode는 문자열을 그대로 바꿀 뿐이다. 그 전에 IDNA 규칙이 문자열을 정규화(mapping)한다. 대문자는 소문자로, 전각 문자는 반각으로 바뀐다.

{% raw %}
```js
new URL("https://EXAMPLE.com").hostname;    // example.com
new URL("https://ｅｘａｍｐｌｅ.com").hostname; // example.com
```
{% endraw %}

이 정규화 규칙은 표준 버전에 따라 조금씩 다르다.

| 표준 | 내용 |
|---|---|
| IDNA2003 | 첫 표준. Unicode 3.2 기준 |
| IDNA2008 | 허용 문자를 다시 정했다. 일부 문자 처리가 IDNA2003과 다르다 |
| UTS #46 | 두 표준 사이의 호환 처리 규칙. 브라우저(WHATWG URL)가 이것을 쓴다 |

차이가 드러나는 대표 문자가 독일어 `ß`다.

{% raw %}
```text
faß.de
  Node.js URL (UTS #46)   ->  xn--fa-hia.de
  Java IDN.toASCII        ->  fass.de
```
{% endraw %}

같은 입력이 서로 다른 도메인이 된다. 한글은 두 방식의 결과가 같다. 하지만 브라우저와 서버가 같은 문자열을 다르게 바꿀 수 있다는 점은 알아 둘 만하다.

### 화면에 한글로 보여 줄지는 브라우저가 판단한다

Punycode를 다시 유니코드로 바꾸는 것은 쉽다. 하지만 브라우저는 모든 IDN을 유니코드로 보여 주지 않는다. homograph 공격 때문이다.

homograph 공격은 모양이 같은 다른 문자로 가짜 도메인을 만드는 공격이다. 예를 들어 라틴 문자 `a`와 키릴 문자 `а`는 화면에서 구분되지 않는다. 그래서 브라우저는 문자 체계가 섞여 있거나 헷갈리기 쉬운 도메인을 Punycode 그대로 보여 준다.

관리 화면이나 로그 뷰어에서 Punycode를 한글로 바꿔 보여 줄 때도 같은 위험이 있다. 의심스러운 도메인은 Punycode로 남기는 쪽이 안전하다.

---

## path와 query: percent-encoding

host가 아닌 부분은 Punycode를 쓰지 않는다. 문자를 UTF-8 바이트로 바꾸고, 바이트마다 `%XX`로 쓴다.

{% raw %}
```text
값  ->  UTF-8 바이트 EA B0 92  ->  %EA%B0%92
```
{% endraw %}

JavaScript에는 함수가 두 개 있다. 용도가 다르다.

{% raw %}
```js
encodeURI("https://a.kr/경로?q=값&x=1");
// https://a.kr/%EA%B2%BD%EB%A1%9C?q=%EA%B0%92&x=1   (: / ? & = 는 그대로)

encodeURIComponent("값 1+2");
// %EA%B0%92%201%2B2                                  (구분자까지 모두 인코딩)
```
{% endraw %}

- `encodeURI`는 URL 전체용이다. URL 구조를 만드는 문자는 남긴다.
- `encodeURIComponent`는 query 값 하나처럼 **조각** 하나용이다. 값 안의 `&`, `=`, `/`도 인코딩한다.
- 두 함수 모두 host를 Punycode로 바꾸지 **않는다.** host는 `new URL()`에 맡긴다.

### 공백은 `%20`인가 `+`인가

HTML form 전송(`application/x-www-form-urlencoded`)은 공백을 `+`로 쓴다. URI의 percent-encoding은 `%20`이다. Java `URLEncoder`는 이름과 달리 form 방식이다.

{% raw %}
```java
URLEncoder.encode("값 1+2", StandardCharsets.UTF_8);   // %EA%B0%92+1%2B2
URLDecoder.decode("%EA%B0%92+1", StandardCharsets.UTF_8); // 값 1
```
{% endraw %}

query 값에는 맞지만 path에 쓰면 공백이 `+`가 되어 다른 경로가 된다.

---

## Java에서 다룰 때 주의할 점

아래 결과는 JDK 25(Corretto 25.0.5)로 직접 실행해 확인했다.

### `java.net.URI`는 한글 host를 host로 보지 않는다

{% raw %}
```java
URI u = new URI("https://한국.kr/경로?q=값");
u.getHost();          // null
u.getAuthority();     // 한국.kr
u.getRawPath();       // /경로
u.toASCIIString();    // https://%ED%95%9C%EA%B5%AD.kr/%EA%B2%BD%EB%A1%9C?q=%EA%B0%92
```
{% endraw %}

- `getHost()`가 `null`이다. 한글 host는 일반 host 문법에 맞지 않아 다른 형태(registry-based authority)로 해석된다.
- `toASCIIString()`은 host까지 percent-encoding한다. `%ED%95%9C%EA%B5%AD.kr`은 DNS에서 쓸 수 없는 값이다. 브라우저 결과(`xn--3e0b707e.kr`)와 다르다.
- 공백 같은 문자가 그대로 있으면 생성자가 `URISyntaxException`을 던진다.

{% raw %}
```text
new URI("https://한국.kr/경로?q=값 1")
java.net.URISyntaxException: Illegal character in query at index 20
```
{% endraw %}

그래서 host는 따로 꺼내 `java.net.IDN`으로 바꾼다.

### `java.net.IDN`의 동작

{% raw %}
```java
IDN.toASCII("한국.kr");                // xn--3e0b707e.kr
IDN.toASCII("*.한국.kr");              // *.xn--3e0b707e.kr
IDN.toASCII("ｅｘａｍｐｌｅ.com");       // example.com
IDN.toASCII("EXAMPLE.com");           // EXAMPLE.com     (소문자로 바꾸지 않는다)
IDN.toASCII("faß.de");                // fass.de         (브라우저와 다르다)
IDN.toASCII("a..com");                // IllegalArgumentException: Empty label is not a legal name
IDN.toASCII("a".repeat(64) + ".com"); // IllegalArgumentException: The label in the input is too long
IDN.toASCII("😀.com");                // IllegalArgumentException: ... unassigned code point ...
IDN.toUnicode("xn--bcher-kva.de");    // bücher.de
```
{% endraw %}

브라우저 규칙과 다른 점을 모으면 이렇다.

| 입력 | Node.js `URL` (브라우저 규칙) | Java `IDN.toASCII` |
|---|---|---|
| `EXAMPLE.com` | `example.com` | `EXAMPLE.com` |
| `faß.de` | `xn--fa-hia.de` | `fass.de` |
| `a..com` | `a..com` (그대로 통과) | 예외 |
| 이모지 label | 변환된다 | 예외 (Unicode 3.2 이후 문자) |

Java `IDN`은 IDNA2003, Unicode 3.2 기준이라 생기는 차이다. 그리고 ASCII뿐인 값에서도 예외가 날 수 있다. 입력을 받는 곳에서는 예외를 잡아 입력 오류로 돌려준다.

---

## 저장하고 비교할 때의 원칙

한글 주소를 받는 서비스는 같은 주소가 여러 형태로 들어온다. 관리자는 한글로 입력하고, 브라우저는 Punycode와 percent-encoding으로 보낸다. 문자열 그대로 비교하면 같은 주소가 다르게 판정된다.

1. **표준형을 하나로 정한다.** host는 소문자 Punycode, path와 query는 percent-encoding 형태가 일반적이다. 브라우저가 보내는 형태와 같기 때문이다.
2. **저장, 비교, 캐시 키, 로그 키는 표준형만 쓴다.** 한글은 화면에 보여 줄 때만 되돌린다.
3. **host와 나머지를 따로 다룬다.** URL 전체를 한 함수로 인코딩하면, host는 Punycode가 아니라 percent-encoding이 되거나 path의 ASCII 특수문자가 바뀔 수 있다.
4. **이미 ASCII인 값은 건드리지 않는 것도 방법이다.** 기존 데이터가 많으면 비ASCII label이 있을 때만 변환한다. 그러면 기존 ASCII 주소는 입력과 출력이 같다.
5. **와일드카드 패턴(`*.한국.kr`)과 스킴 없는 값(`한국.kr/path`)을 따로 시험한다.** URL 파서는 이런 값을 host로 인식하지 못할 수 있다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 원칙 | URI는 ASCII만. 한글은 위치에 따라 다르게 바뀐다 |
| host | IDNA 정규화 뒤 Punycode. `xn--` 접두어. label 63자, 전체 253자 |
| path, query | UTF-8 바이트를 `%XX`로 |
| 브라우저 | 주소창은 한글로 보여도 실제 요청과 `location.hostname`은 변환된 값 |
| 표시 | homograph 위험 때문에 브라우저는 일부 IDN을 Punycode로 보여 준다 |
| JS | `encodeURI`는 전체, `encodeURIComponent`는 조각. host 변환은 `new URL()` |
| Java | `URI.getHost()`는 한글 host에서 `null`. host는 `IDN.toASCII`로 따로 |
| Java 차이 | 소문자 변환 없음, `ß` 처리 다름, 빈 label과 63자 초과는 예외 |
| 공백 | form 방식(`URLEncoder`)은 `+`, URI 방식은 `%20` |
