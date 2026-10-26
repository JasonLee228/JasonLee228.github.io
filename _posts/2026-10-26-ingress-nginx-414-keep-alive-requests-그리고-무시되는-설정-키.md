---
title: "ingress-nginx 414, keep-alive-requests, 그리고 무시되는 설정 키"
date: 2026-10-26 09:10:00 +0900
categories: ["Kubernetes", "Ingress"]
tags: ["ingress-nginx", "nginx", "kubernetes", "http2"]
permalink: /posts/ingress-nginx-414-keep-alive-requests-그리고-무시되는-설정-키/
---

## ingress-nginx 설정에서 같은 날 만난 문제 세 가지

ingress-nginx 운영 환경에서 서로 관련 없어 보이는 장애를 같은 시기에 두 번 겪었다.

1. 긴 URL의 WebSocket 요청이 `414`로 거절된다.
2. 페이지 로드 중 JavaScript 모듈 몇 개가 가끔 실패하고, 새로고침하면 된다.
3. ConfigMap에 값을 넣었는데 동작이 바뀌지 않는다.

원인을 따라가 보니 모두 **nginx 설정 값 한두 개와, 그 값이 어떻게 적용되는가**의 문제였다. 이 글은 세 가지를 순서대로 정리한다.

> 명령과 기본값은 ingress-nginx 1.12 계열(chart 4.12)에서 확인한 내용이다. 버전과 chart에 따라 기본값이 다를 수 있으므로 반드시 사용 중인 환경에서 다시 확인한다.

---

## 1. 414 Request-URI Too Large

### 증상

WebSocket 연결 URL에 긴 쿼리 파라미터가 붙는 기능이 일부 사용자에게만 동작하지 않았다. ingress 로그를 보니 상태 코드가 `414`였다.

확인한 사실은 다음과 같다.

- 414 로그의 request line 길이가 전부 8194자였다. 8192(8k)에서 잘린 값이다.
- upstream 응답 시간이 `0.000`이었다. 요청은 백엔드까지 가지 못하고 nginx가 바로 거절했다.
- 정상 요청의 최대 길이는 약 5.7k였다.
- 길어진 원인은 쿼리의 `ticket` 파라미터였다. 그 안에 JWT가 들어 있고, JWT 하나만 5k를 넘었다.

### 원인: `large-client-header-buffers`

nginx는 request line 하나가 **버퍼 한 개에 전부 들어가야** 한다. 실제 적용된 `nginx.conf`는 아래와 같았다.

{% raw %}
```nginx
client_header_buffer_size 1k;
large_client_header_buffers 4 8k;
```
{% endraw %}

처리 순서는 이렇다.

1. 요청 헤더를 먼저 `client_header_buffer_size`(1k) 버퍼에 읽는다.
2. 1k에 안 들어가면 `large_client_header_buffers`의 버퍼(여기서는 8k)를 할당한다.
3. request line이 8k 버퍼 하나를 넘으면 `414`를 반환한다.
4. 개별 헤더 한 줄이 넘으면 `400`을 반환한다.

즉 8k를 넘는 URL이나 쿠키 한 줄은 개수와 상관없이 거절된다.

### 해결

ConfigMap(또는 Helm values의 `controller.config`)에 아래를 넣는다.

{% raw %}
```yaml
data:
  large-client-header-buffers: "4 32k"
  client-header-buffer-size: "8k"
```
{% endraw %}

- 16k도 당시 요청은 통과했다. JWT 같은 토큰은 클레임이 늘면 계속 커질 수 있어서 여유를 두고 32k를 권장했다.
- 버퍼는 연결마다 필요할 때 할당된다. 값을 크게 잡으면 메모리 사용이 늘 수 있으니 무작정 키우지 않는다.
- 근본적으로는 URL에 토큰을 싣지 않는 설계가 더 안전하다. 토큰은 access log에도 남기 쉽다.

---

## 2. 설정 키 형식 함정: 언더스코어는 조용히 무시된다

414를 조사하다가 ConfigMap에 이미 아래 값이 들어 있는 것을 발견했다.

{% raw %}
```yaml
data:
  client_header_buffer_size: "8k"
```
{% endraw %}

그런데 실제 `nginx.conf`에는 `client_header_buffer_size 1k;`가 그대로였다. **값이 적용되지 않았다.**

ingress-nginx ConfigMap은 nginx 지시어 이름이 아니라 **하이픈으로 연결한 고유 키**를 읽는다. 언더스코어로 쓴 키는 에러 없이 무시된다.

| 쓴 키 | 결과 |
|---|---|
| `client_header_buffer_size` | 무시됨 (nginx 지시어 이름 그대로 쓴 경우) |
| `client-header-buffer-size` | 적용됨 |
| `large_client_header_buffers` | 무시됨 |
| `large-client-header-buffers` | 적용됨 |

변경 후에는 항상 **실제 생성된 설정 파일**에서 확인한다.

{% raw %}
```bash
kubectl -n <namespace> exec deploy/<controller> -- \
  grep -nE "client_header_buffer_size|large_client_header_buffers" /etc/nginx/nginx.conf
```
{% endraw %}

ConfigMap에 값이 있다는 사실과 nginx에 반영됐다는 사실은 다르다. 이 확인 한 줄이 추측을 줄여 준다.

---

## 3. keep-alive-requests: 동시 접속 수가 아니다

### 증상

브라우저 앱이 로드될 때 정적 JavaScript 모듈을 약 140개 요청한다. 일부 사용자에게서 이런 현상이 나타났다.

- 모듈 몇 개가 `Failed to fetch dynamically imported module`로 실패한다.
- 실패는 0.2~2초 안에 빨리 발생한다. 30초 timeout이 아니다.
- 새로고침을 몇 번 하면 결국 로드된다.
- 서버 access log에는 해당 요청이 전부 `200`/`304`였다. 서버는 정상 응답했는데 브라우저는 실패했다.

HTTP/1.1과 HTTP/2로 나눠 보니 HTTP/2에서 실패율이 크게 높았다. 재현 PC에서 Chrome net-export 로그를 받아 보니 결정적인 단서가 나왔다.

| HTTP/2 세션 | 보낸 스트림 | 응답 헤더 받음 | 종료 |
|---|---|---|---|
| 1차 로드 | 146 | 46 | TCP RST |
| 재시도 연결 | 100 | 100 | `GOAWAY NO_ERROR` |

### 원인

controller의 `keep-alive-requests`가 **100**이었다. 이 값의 의미를 오해하기 쉽다.

> `keep-alive-requests`는 **연결 하나가 평생 처리할 수 있는 요청 수의 누적 상한**이다. 동시 접속 수도, 동시 스트림 수도 아니다.

HTTP/2는 연결 하나에 스트림을 여러 개 실어 보낸다. 모듈 140개가 연결 하나로 동시에 나갔다. 일어난 일은 다음과 같다.

1. 동시 스트림 상한(128) 안이라 브라우저는 한꺼번에 요청을 보낸다.
2. nginx는 100번째 요청에서 `GOAWAY`를 보내고, 처리가 끝나면 연결을 닫는다.
3. 소켓에는 아직 읽지 않은 요청(넘친 40여 개)이 남아 있다. 이 상태로 닫으면 `FIN`이 아니라 **TCP RST**가 나간다.
4. RST를 받은 클라이언트 OS는 아직 읽지 않은 수신 데이터를 버린다. nginx는 `200`을 보내고 기록했지만 브라우저는 받지 못한다.
5. 응답 헤더를 받기 전 스트림은 Chrome이 새 연결로 자동 재시도한다. 본문을 받던 스트림은 재시도되지 않고 실패한다.
6. 모듈 하나가 실패하면 `import()` 전체가 실패한다. 브라우저는 실패한 URL을 문서 수명 동안 기억하므로 새로고침해야 복구된다.

HTTP/1.1은 연결 6개에 요청이 나뉘어 연결당 100개를 잘 넘지 않기 때문에 거의 실패하지 않았다. 새로고침이 통하는 이유도 설명된다. 정적 파일에 긴 `Cache-Control`이 있어서 받은 만큼 디스크 캐시에서 읽히고, 연결당 요청 수가 100 아래로 내려가기 때문이다.

### 왜 환경마다 달랐는가

개발 환경에서는 같은 증상이 없었다. ConfigMap에 키가 없는 controller는 chart 기본값(1000)으로 동작했고, 운영 controller에만 100이 설정되어 있었다. 참고로 nginx 자체 지시어 `keepalive_requests`의 기본값은 1.19.10 이전에는 100, 이후에는 1000이다. 어떤 값이 적용되는지는 버전과 설정을 직접 확인해야 한다.

### 해결

{% raw %}
```yaml
data:
  keep-alive-requests: "1000"
```
{% endraw %}

- ConfigMap 변경은 nginx reload만 일으킨다. Pod 재시작은 필요 없다.
- 기존 연결은 닫힐 때까지 옛 worker가 옛 값으로 처리한다. `worker-shutdown-timeout`이 길면 오래 남는다. 테스트는 새 연결(브라우저 재시작 또는 소켓 flush)로 한다.
- Helm으로 관리하는 controller라면 `controller.config`에 넣어야 다음 `helm upgrade`에서 값이 되돌아가지 않는다.
- Ingress 리소스의 annotation으로는 이 값을 바꿀 수 없다.

적용 확인은 `http` 블록의 값을 본다. `upstream` 블록 안의 `keepalive_requests`는 백엔드 연결용이므로 무관하다.

{% raw %}
```bash
kubectl -n <namespace> exec deploy/<controller> -- grep -n keepalive_requests /etc/nginx/nginx.conf
```
{% endraw %}

모듈 수 자체를 줄이는 것도 근본 대응이다. 번들링으로 요청 수가 줄면 연결당 요청 수 상한에 닿을 확률이 같이 낮아진다.

---

## 정리

| 증상 | 설정 키 | 의미 | 확인 방법 |
|---|---|---|---|
| 긴 URL에서 `414` | `large-client-header-buffers` | request line 하나가 들어갈 버퍼 크기 (기본 `4 8k`) | access log의 request line 길이 |
| 일부 헤더에서 `400` | 같은 키 | 헤더 한 줄이 버퍼를 넘음 | 헤더 크기 |
| 모듈이 일부 실패, 새로고침하면 됨 | `keep-alive-requests` | 연결 하나가 처리할 누적 요청 수 상한 | net-export의 GOAWAY, RST |
| 값을 넣었는데 변화 없음 | 키 이름 | 하이픈 형식만 인식됨 | `nginx.conf`를 직접 grep |

체크리스트로 줄이면 다음과 같다.

- ConfigMap 키는 `kebab-case`로 쓴다. 언더스코어 키는 에러 없이 무시된다.
- 변경 후에는 `/etc/nginx/nginx.conf`에서 실제 반영을 확인한다.
- `keep-alive-requests`는 동시 접속 상한이 아니다. 연결 하나의 누적 요청 상한이다.
- 서버가 모두 `200`을 기록했는데 클라이언트만 실패한다면, 연결을 닫는 쪽(GOAWAY/RST)을 의심한다.
