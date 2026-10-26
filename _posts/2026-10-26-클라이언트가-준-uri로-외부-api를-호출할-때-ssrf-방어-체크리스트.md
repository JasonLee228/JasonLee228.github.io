---
title: "클라이언트가 준 URI로 외부 API를 호출할 때 SSRF 방어 체크리스트"
date: 2026-10-26 11:20:00 +0900
categories: ["보안", "웹"]
tags: ["ssrf", "보안", "spring", "webclient"]
permalink: /posts/클라이언트가-준-uri로-외부-api를-호출할-때-ssrf-방어-체크리스트/
---

백엔드가 외부 시스템의 결과를 조회해서 파일을 내려받고, 그 파일을 다른 저장소에 올리는 API를 만들었다. 요청 body에는 "결과를 조회할 주소"가 들어 있었다.

```json
{
  "reportUri": "https://external.example.com/api/reports/1234/result"
}
```

서버는 이 주소로 **서버가 가진 인증 토큰을 붙여서** GET 요청을 보낸다. 구현은 간단했지만, 코드 리뷰에서 Critical 1건과 Major 여러 건이 나왔다. 모두 한 가지 문제에서 나왔다. **클라이언트가 준 문자열을 서버 권한으로 호출하고 있었다.**

이 글에서는 그 리뷰 과정에서 정리한 방어 순서를 체크리스트로 남긴다.

## 무엇이 위험한가

클라이언트가 URL을 주면 서버는 두 가지를 잃을 수 있다.

| 위험 | 설명 |
|---|---|
| SSRF | 서버가 내부망, 메타데이터 주소, 다른 서비스로 요청을 보낸다. 클라이언트는 직접 접근하지 못하는 곳이다. |
| 토큰 유출 | 서버가 붙인 인증 헤더가 공격자가 지정한 호스트로 전달된다. |

특히 두 번째가 놓치기 쉽다. 외부 시스템 응답 안에 "파일 다운로드 URL"이 들어 있고, 서버가 그 URL에도 인증을 붙여 내려받는 구조라면, 응답 내용이 조작되었을 때 토큰이 그대로 나간다.

그래서 검증할 대상은 두 곳이다.

1. 클라이언트가 보낸 조회 주소
2. 외부 시스템 응답 안에 들어 있는 파일 주소

## 1단계: 절대 URL은 받지 않고 path만 받는다

가장 단순하고 강한 방법은 **호스트를 클라이언트가 정하지 못하게** 하는 것이다. 호스트는 서버 설정에서 가져오고, 요청에서는 path만 받는다.

{% raw %}
```java
URI uri = URI.create(raw);

// scheme, host가 있으면 절대 URL이다. "//host/path" 형태도 authority가 생긴다.
if (uri.isAbsolute() || uri.getRawAuthority() != null) {
    throw new InvalidTargetException("path만 허용한다");
}

String path = uri.getRawPath();
if (path == null || !path.startsWith("/")) {
    throw new InvalidTargetException("path는 /로 시작해야 한다");
}
```
{% endraw %}

문자열에 `http://`가 있는지 `contains`로 검사하는 방식은 약하다. `//evil.example.com/x` 같은 scheme 없는 형태가 빠져나간다. `URI`로 파싱한 뒤 `isAbsolute()`와 `getRawAuthority()`를 보는 편이 안전하다.

## 2단계: 계정(조직) prefix를 강제한다

path만 받아도 아직 부족하다. 같은 외부 시스템 안에는 다른 고객의 데이터 경로도 있다. 요청한 사용자의 계정 prefix 아래인지 확인해야 한다.

{% raw %}
```java
String prefix = "/api/external/" + accountKey + "/";
if (!path.startsWith(prefix)) {
    throw new InvalidTargetException("허용되지 않은 경로");
}
```
{% endraw %}

prefix 검사를 빠뜨리면 인증된 사용자가 다른 계정의 결과를 조회할 수 있다. SSRF는 아니지만 같은 계열의 권한 우회다.

## 3단계: dot-segment와 인코딩 우회를 막는다

prefix를 `startsWith`로만 확인하면 아래 경로가 통과한다.

{% raw %}
```text
/api/external/account-a/../account-b/secret
/api/external/account-a/%2e%2e/account-b/secret
/api/external/account-a/..%2faccount-b/secret
```
{% endraw %}

문자열은 prefix로 시작하지만 서버가 요청을 처리할 때 정규화되면 다른 경로가 된다. 아래 순서로 막았다.

{% raw %}
```java
String lower = path.toLowerCase(Locale.ROOT);

// 인코딩된 점, 슬래시, 역슬래시는 아예 거부한다.
if (lower.contains("%2e") || lower.contains("%2f") || lower.contains("%5c")
        || path.contains("\\")) {
    throw new InvalidTargetException("허용되지 않은 문자");
}

// raw segment에 . 또는 .. 이 있으면 거부한다.
for (String segment : path.split("/")) {
    if (segment.equals(".") || segment.equals("..")) {
        throw new InvalidTargetException("상위 경로 이동은 허용하지 않는다");
    }
}
```
{% endraw %}

핵심은 **정규화해서 통과시키지 않고 거부**하는 것이다. 정규화 결과를 믿고 쓰면 정규화 구현 차이(프록시, 서블릿 컨테이너, HTTP 클라이언트)가 다시 우회 지점이 된다. 정상 요청에는 `..`이 필요 없으니 거부해도 잃는 것이 없다.

## 4단계: 응답 안의 파일 URL은 same-origin일 때만 인증 다운로드한다

외부 시스템 응답에 파일 URL이 들어 있는 경우가 가장 위험했다. 리뷰에서 Critical로 지적된 부분이 여기다. 검증 없이 그 URL로 인증 다운로드를 하면, 응답 내용에 따라 토큰이 다른 호스트로 나간다.

기준은 두 가지였다.

- 설정에 등록된 파일 서버 origin(scheme, host, port)과 같아야 한다.
- 허용된 path 하위여야 한다.

{% raw %}
```java
boolean isTrustedFileUrl(URI file, URI configuredBase, String allowedPrefix) {
    if (file.getRawUserInfo() != null) return false;               // user@host 형태 차단
    if (!configuredBase.getScheme().equalsIgnoreCase(file.getScheme())) return false;
    if (!configuredBase.getHost().equalsIgnoreCase(file.getHost())) return false;
    if (port(configuredBase) != port(file)) return false;

    String rawPath = file.getRawPath();
    if (rawPath == null || !rawPath.startsWith(allowedPrefix)) return false;
    return !containsUnsafeSegment(rawPath);                         // 3단계와 같은 검사
}

private int port(URI u) {
    if (u.getPort() != -1) return u.getPort();
    return "https".equalsIgnoreCase(u.getScheme()) ? 443 : 80;
}
```
{% endraw %}

`file.getHost()`는 `http://trusted.example.com@evil.example.com/` 같은 주소에서 `evil.example.com`을 돌려준다. 호스트 비교가 이런 userinfo 속임수도 걸러준다. 그래도 userinfo가 있는 URL은 정상 요청에서 쓸 일이 없으니 먼저 거부했다.

추가로 권장하는 것은 인증 헤더를 붙이는 클라이언트가 **redirect를 자동으로 따라가지 않게** 하는 것이다. same-origin 검사를 통과한 URL이 다른 호스트로 redirect하면 헤더가 따라갈 수 있다. 이 부분은 사용하는 HTTP 클라이언트의 기본 동작에 따라 다르므로 버전과 설정을 확인해야 한다.

## 5단계: 응답 id를 요청과 대조한다

리뷰에서 같이 나온 Major가 있었다. 요청한 작업 id와 응답의 작업 id가 일치하는지 확인하지 않았다. 외부 시스템이 다른 작업의 결과를 돌려주거나 조작된 응답이 오면, 다른 사용자의 파일을 업로드할 수 있다.

- 요청에서 기대하는 id와 응답 안의 id가 같은지 확인한다.
- 응답에 id가 없으면 "일치 확인 불가"이므로 통과시키지 않고 실패로 처리한다.

## 6단계: 조회 실패와 값 없음을 구분한다

마지막 리뷰에서는 설정 조회 결과가 `null`이면 "조회 실패"인지 "값이 비어 있음"인지 구분되지 않는다는 지적이 나왔다. 둘을 같은 `null`로 두면 **조회 실패가 허용으로 처리**될 수 있다.

{% raw %}
```java
public record LookupResult(boolean looked, Optional<String> value) {
    static LookupResult notFound()      { return new LookupResult(false, Optional.empty()); }
    static LookupResult emptyValue()       { return new LookupResult(true,  Optional.empty()); }
    static LookupResult of(String v)    { return new LookupResult(true,  Optional.of(v)); }
}

// 조회 자체가 안 됐으면 fail-closed
if (!result.looked()) {
    throw new AccessDeniedException("설정을 확인할 수 없다");
}
```
{% endraw %}

보안 검증은 **불확실하면 거부(fail-closed)** 가 기본이다. 결과 타입에 "조회했는가"를 따로 담으면 이 실수를 타입 수준에서 막을 수 있다.

## 로그에 남기지 않을 것

검증을 통과해도 로그가 새는 경우가 있다.

- 외부 시스템 응답 원문
- 인증 토큰
- 파일 URL 전체 (쿼리에 서명이나 토큰이 들어 있을 수 있다)

로그에는 작업 id, 결과 코드, 검증 실패 사유 정도만 남기는 것이 안전하다.

## 테스트에서 겪은 일

path traversal 테스트를 먼저 작성하고 기존 코드에 돌렸더니 **실패하지 않고 멈췄다.** 기존 코드는 검증 없이 `..`이 들어간 주소로 요청을 보냈고, 테스트용 서버가 응답하지 않아 대기 상태가 되었다.

보안 테스트는 "예외가 난다"만 기대하면 안 된다. 검증이 없을 때 **외부 호출이 실제로 일어나는지**도 같이 확인해야 한다. 거부 케이스에서는 mock 서버에 요청이 한 건도 도착하지 않았다는 것을 단언하면 좋다.

{% raw %}
```java
@Test
void rejectsDotSegment() {
    assertThatThrownBy(() -> service.fetch(account, "/api/external/a1/../a2/x"))
            .isInstanceOf(InvalidTargetException.class);
    assertThat(mockServer.getRequestCount()).isZero();
}
```
{% endraw %}

## 정리

| 순서 | 검증 | 막는 것 |
|---|---|---|
| 1 | 절대 URL 거부, path만 수신 | 임의 호스트 호출, SSRF |
| 2 | 계정 prefix 강제 | 다른 계정 경로 접근 |
| 3 | dot-segment, 인코딩된 `.` `/` 거부 | prefix 우회 |
| 4 | 응답 파일 URL은 same-origin + 허용 path | 토큰 유출 |
| 5 | 요청 id와 응답 id 대조 | 다른 작업 결과 혼입 |
| 6 | 조회 실패와 값 없음 구분, fail-closed | 실패가 허용으로 처리되는 문제 |
| - | 토큰, 원문, URL 전체를 로그에 남기지 않음 | 로그 경유 유출 |

체크리스트로 줄이면 이렇다.

- [ ] 외부 호출 주소의 host는 서버 설정에서만 온다.
- [ ] 클라이언트 입력은 `URI`로 파싱해서 절대 URL을 거부한다.
- [ ] 계정 prefix를 확인한다.
- [ ] 정규화하지 않고 `.`, `..`, `%2e`, `%2f`, `\`를 거부한다.
- [ ] 외부 응답 안의 URL에 인증을 붙일 때는 origin과 path를 다시 검증한다.
- [ ] 인증 헤더가 붙는 클라이언트의 redirect 동작을 확인한다.
- [ ] 검증이 불확실하면 거부한다.
- [ ] 거부 테스트는 외부 호출이 발생하지 않았음까지 확인한다.

리뷰는 세 번 돌았고, Critical에서 Major, Minor 순서로 줄어들었다. 처음부터 위 순서로 설계했다면 한 번에 끝났을 일이다. 사용자 입력이 "호출 대상"이 되는 순간부터는 입력 검증이 곧 인가(authorization)의 일부라고 생각하고 설계하는 것이 좋다.
