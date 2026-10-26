---
title: "Windows와 Docker에서 Testcontainers 연결이 실패할 때"
date: 2026-10-26 11:40:00 +0900
categories: ["Spring", "테스트"]
tags: ["testcontainers", "windows", "docker", "테스트"]
permalink: /posts/windows와-docker에서-testcontainers-연결이-실패할-때/
---

Redis나 Elasticsearch 같은 외부 의존성을 Testcontainers로 띄워서 통합 테스트를 돌리고 있었다. 리눅스 CI에서는 잘 되는데 Windows 개발 PC에서는 컨테이너가 정상으로 뜬 뒤에도 테스트가 실패했다.

이 글에서는 두 가지 서로 다른 실패를 정리한다.

1. Windows 호스트의 JVM에서 `Unable to establish loopback connection`으로 실패한다.
2. 이를 피하려고 Maven을 컨테이너 안에서 돌렸더니 `Connection refused`로 실패한다.

두 실패는 증상이 비슷하지만 원인이 완전히 다르다. 구분하지 못하면 우회만 길어진다.

## 1. Windows 호스트: `Unable to establish loopback connection`

### 증상

Redis 통합 테스트 8건이 모두 실패했다. 컨테이너는 정상 기동했고, 실패는 클라이언트가 연결하기 전에 일어났다.

{% raw %}
```text
java.io.IOException: Unable to establish loopback connection
Caused by: java.net.SocketException: Invalid argument: connect
```
{% endraw %}

스택 트레이스에 Lettuce(Netty)가 보였지만, 같은 오류가 MockWebServer, Apache HttpClient 5의 I/O reactor 같은 다른 라이브러리에서도 났다. 공통점은 **NIO `Selector`를 여는 순간** 실패한다는 것이다. 즉 애플리케이션 코드나 컨테이너 문제가 아니다.

### 먼저 환경 문제인지 가려낸다

코드를 고치기 전에, 아래 최소 코드로 JVM 자체가 selector를 열 수 있는지 확인한다.

{% raw %}
```java
public class LoopbackProbe {
    public static void main(String[] args) throws Exception {
        try (var selector = java.nio.channels.Selector.open()) {
            System.out.println("Selector.open OK");
        }
        var pipe = java.nio.channels.Pipe.open();
        pipe.sink().close();
        pipe.source().close();
        System.out.println("Pipe.open OK");
    }
}
```
{% endraw %}

{% raw %}
```bash
java LoopbackProbe.java
```
{% endraw %}

여기서 실패하면 **코드 회귀가 아니라 실행 환경 문제**다. 이 경우 테스트를 고치지 말고 환경을 먼저 바꿔야 한다. 실제로 이번에는 JDK 배포판과 패치 버전을 바꿔도(Zulu 17, Corretto 17.0.x 여러 버전) 같은 방식으로 재현되었다. `-Djava.net.preferIPv4Stack=true`도 효과가 없었다.

### 우회: Unix domain socket 임시 디렉터리를 바꾼다

JDK 16 이후 Windows에서는 selector 내부 연결에 Unix domain socket 파일을 임시 디렉터리에 만드는 경로가 있는 것으로 알려져 있다 (JDK 버전에 따라 다를 수 있다). 그 위치를 `jdk.net.unixdomain.tmpdir` 시스템 프로퍼티로 바꿀 수 있다. 짧고 단순한 경로로 지정했더니 실패하던 8건이 모두 통과했다.

{% raw %}
```bash
JAVA_TOOL_OPTIONS="-Djdk.net.unixdomain.tmpdir=D:/work/project/target" \
  mvn "-Dtest=SessionStoreIntegrationTest" test
```
{% endraw %}

PowerShell에서는 이렇게 쓴다.

{% raw %}
```powershell
$env:JAVA_TOOL_OPTIONS = "-Djdk.net.unixdomain.tmpdir=D:/work/project/target"
mvn "-Dtest=SessionStoreIntegrationTest" test
```
{% endraw %}

### 원인은 확정하지 못했다

이 우회가 먹힌 이유를 정확히 확인하지는 못했다. 관찰한 사실은 다음과 같다.

- 기본 TEMP 경로에 `USERNA~1`처럼 **8.3 단축 이름**이 들어 있는 환경이었다.
- 경로를 바꾸면 해결되었다.

그래서 단축 이름이 든 TEMP 경로가 원인이라고 **추정**하지만, 단축 이름을 없앤 TEMP로 재현하는 대조 실험은 하지 않았다. JDK 버전과 구현에 따라 동작이 다를 수 있으니, 원인을 단정하지 않고 "이 환경에서 이 우회로 해결되었다"까지만 기록했다.

주의할 점은 이 우회가 **환경 문제를 피하는 것일 뿐 production 코드 호환성을 증명하지 않는다**는 것이다. 우회로 통과한 결과를 "클라이언트가 문제없다"는 근거로 쓰면 안 된다.

## 2. 컨테이너 안의 Maven: `Connection refused`

호스트 JVM 문제를 피하려고 Maven도 Docker 컨테이너 안에서 실행했다. 리눅스 JVM에서는 selector probe가 성공했고 Spring context도 떴다. 그런데 첫 외부 호출에서 실패했다.

{% raw %}
```text
Connection refused
```
{% endraw %}

### 원인

Testcontainers는 컨테이너 포트를 호스트의 임의 포트에 매핑하고, 접속 주소를 이렇게 돌려준다.

{% raw %}
```text
http://127.0.0.1:55012
```
{% endraw %}

테스트가 호스트에서 돌 때는 맞는 주소다. 하지만 **테스트(Maven)가 컨테이너 안에서 돌면 `127.0.0.1`은 Maven 컨테이너 자신**이다. 매핑된 포트는 호스트에만 열려 있으니 연결이 거부된다.

`--network host`로 해결해 보려 했지만 Docker Desktop(Windows)의 리눅스 컨테이너는 VM 안에서 도는 것이어서 Windows 호스트의 loopback을 공유하지 않는다. 결국 ES 대기 timeout으로 끝났다. 이 옵션은 리눅스 호스트에서만 기대한 대로 동작한다.

### 해결: 같은 Docker network와 alias를 쓴다

핵심은 **테스트 JVM과 대상 컨테이너를 같은 Docker network에 두고, 컨테이너 이름(alias)과 컨테이너 내부 포트로 접속하는 것**이다.

{% raw %}
```bash
# 1. 전용 network
docker network create it-net

# 2. 대상 컨테이너를 alias와 함께 기동 (호스트 포트 매핑은 필요 없다)
docker run -d --name it-redis --network it-net --network-alias redis redis:7-alpine

# 3. 테스트 실행 컨테이너를 같은 network에서 실행
docker run --rm --network it-net \
  -v "$PWD":/work -w /work \
  maven:3.9-eclipse-temurin-17 \
  mvn -B "-Dtest=SessionStoreIntegrationTest" "-Dredis.host=redis" "-Dredis.port=6379" test

# 4. 정리
docker rm -f it-redis
docker network rm it-net
```
{% endraw %}

테스트 코드는 주소를 하드코딩하지 않고 외부에서 받는다.

{% raw %}
```java
String host = System.getProperty("redis.host");
if (host != null) {
    // 컨테이너 network 안에서 실행: alias와 컨테이너 내부 포트 사용
    return new RedisURI(host, Integer.getInteger("redis.port", 6379));
}
// 호스트에서 실행: Testcontainers가 매핑한 주소 사용
return new RedisURI(container.getHost(), container.getMappedPort(6379));
```
{% endraw %}

호스트에서 도는 테스트와 컨테이너 안에서 도는 테스트는 **접속 주소가 다르다**는 것만 기억하면 된다.

| 테스트 JVM 위치 | 접속 주소 |
|---|---|
| 호스트 | `127.0.0.1:<매핑 포트>` (Testcontainers가 제공) |
| 같은 network의 컨테이너 | `<alias>:<컨테이너 내부 포트>` |

Maven 컨테이너 안에서 Testcontainers로 다시 컨테이너를 띄우는 중첩 구조는 Docker 소켓 마운트 같은 추가 설정이 필요하고 주소 문제가 더 복잡해진다. 가능하면 대상 컨테이너는 바깥에서 띄우고 테스트에는 주소만 넘기는 편이 단순하다.

## 3. 실행 순서에서 얻은 교훈

이번에 가장 시간이 오래 걸린 부분은 기술 문제가 아니라 **실행 순서**였다. 처음부터 API, TLS, 장애 주입, health 검사를 모두 담은 큰 테스트를 만들었다. 환경 실패가 나자 그 실패가 "기술 호환성 문제"인지 "환경 문제"인지 구분되지 않았고, 우회를 연달아 시도하며 시간을 썼다.

- 첫 실행은 **가장 작은 smoke 테스트**로 한다. (예: 두 클라이언트 생성 + 각각 `info()` 호출)
- smoke가 통과하기 전에는 시나리오를 늘리지 않는다.
- 환경 실패는 호환성 실패로 기록하지 않는다.
- 같은 가설로 두 번 실패하면 새 우회를 얹지 말고 실행 구조를 다시 생각한다.

## 4. 실패한 뒤 컨테이너를 정리한다

시도를 여러 번 하면 컨테이너가 남는다. Testcontainers의 정리용 컨테이너(Ryuk)와 직접 띄운 컨테이너가 남지 않았는지 매번 확인했다.

{% raw %}
```bash
docker ps -a --filter "name=it-" --format "{{.ID}} {{.Names}} {{.Status}}"
docker network ls --filter "name=it-net"
```
{% endraw %}

## 정리

| 증상 | 원인 | 대응 |
|---|---|---|
| `Unable to establish loopback connection` (호스트) | Windows JVM이 selector 내부 연결을 만들지 못함. 원인은 미확정이고 TEMP의 8.3 경로가 의심됨 | `Selector.open()`/`Pipe.open()` probe로 확인 후 `-Djdk.net.unixdomain.tmpdir`로 우회 |
| `Connection refused` (컨테이너 안 Maven) | `127.0.0.1`이 호스트가 아니라 자기 자신 | 같은 Docker network, alias, 내부 포트 사용 |
| `--network host`로도 실패 | Docker Desktop은 호스트 loopback을 공유하지 않음 | host network에 의존하지 않음 |
| 우회가 길어짐 | 큰 테스트를 먼저 작성함 | smoke 우선, 환경 실패와 코드 실패 분리 |

체크리스트로 줄이면 이렇다.

- [ ] 통합 테스트가 실패하면 먼저 selector probe로 JVM 환경을 확인한다.
- [ ] 환경 우회로 통과한 결과를 코드 호환성의 근거로 쓰지 않는다.
- [ ] 컨테이너 안에서 테스트를 돌리면 `127.0.0.1`을 쓰지 않는다.
- [ ] 접속 주소를 시스템 프로퍼티로 받아 두 실행 방식을 모두 지원한다.
- [ ] 최소 smoke를 먼저 통과시킨 뒤 시나리오를 늘린다.
- [ ] 실패 후 남은 컨테이너와 network를 정리한다.
