---
title: "Maven 전이 의존성 취약점 대응: 버전 오버라이드, exclusion, 그리고 포크로 갈아타기"
date: 2026-11-06 18:50:00 +0900
categories: ["Java", "빌드"]
tags: ["maven", "dependency-track", "sca", "전이의존성", "보안취약점"]
permalink: /posts/maven-전이-의존성-취약점-대응-버전-오버라이드-exclusion-그리고-포크로-갈아타기/
---

## 결과표에 세 종류가 섞여 있다

SCA(소프트웨어 구성 분석) 도구가 새 빌드의 SBOM을 읽고 취약점 목록을 냈다. 이번에는 Dependency-Track이었다. high와 medium을 고치기로 했는데, 목록을 보니 성격이 셋이었다.

| 라이브러리 | 어떻게 들어왔나 | 패치 상태 |
|---|---|---|
| `mariadb-java-client` 3.5.10 | 우리 `pom.xml`이 직접 선언 | 3.5.11에 수정 |
| `guava` 33.6.0-android | 사내 gRPC SDK 라이브러리의 전이 의존성 | 33.7.2-android에 수정 |
| `org.lz4:lz4-java` 1.8.0 | Elasticsearch 7.17 High Level REST Client의 전이 의존성 | **원본 저장소 archived. 패치 없음** |

세 가지 모두 Maven에서 처리 방법이 다르다. 이전 글 [SBOM 취약점 결과를 VEX로 정리하는 방법](/posts/sbom-취약점-결과를-vex로-정리하는-방법/)은 "고칠 수 없는 것을 판정하는 쪽"이었다. 이 글은 **고치는 쪽**의 세 패턴이다.

---

## 1. 직접 의존성: 버전 속성만 올린다

가장 쉽다. 우리가 선언한 의존성이면 버전을 올린다. Spring Boot parent를 쓰면 BOM이 관리하는 라이브러리는 **속성 이름**으로 덮는다.

{% raw %}
```xml
<properties>
    <mariadb.version>3.5.11</mariadb.version>
</properties>
```
{% endraw %}

Boot BOM의 `mariadb.version` 속성을 덮으면 `spring-boot-dependencies`가 관리하는 모든 자리에 적용된다. `<dependency>`에 `<version>`을 직접 쓰는 것보다 이쪽이 BOM과 어긋나지 않는다.

어느 속성인지는 BOM pom에서 찾는다.

{% raw %}
```bash
mvn help:effective-pom | grep -i mariadb
```
{% endraw %}

---

## 2. 전이 의존성: dependencyManagement로 덮는다

`guava`는 우리가 선언하지 않았다. 사내 라이브러리가 끌고 온다. 그 라이브러리를 고치는 것이 정답이지만 릴리스 주기가 따로 있다. 우리 쪽에서 먼저 막아야 한다.

전이 의존성 버전은 `<dependencyManagement>`가 **가장 센 규칙**이다. 어디서 끌려오든 여기 적힌 버전으로 맞춰진다.

{% raw %}
```xml
<dependencyManagement>
    <dependencies>
        <!-- gRPC SDK 전이 guava 33.6.0 보안 패치 오버라이드. SDK가 올라오면 제거 -->
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>33.7.2-android</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```
{% endraw %}

두 가지를 챙긴다.

**classifier 성격을 유지한다.** `-android`가 붙은 guava는 Android/JDK 8 호환 빌드다. 원래 끌려오던 것이 `-android`였으니 `-jre`로 바꾸지 않고 같은 계열의 패치 버전으로 올린다. 라이브러리가 그 계열을 선택한 이유가 있을 수 있다.

**제거 조건을 주석에 남긴다.** 이 오버라이드는 임시다. 원인 라이브러리가 올라오면 지워야 한다. 안 지우면 나중에 그 라이브러리가 더 높은 guava를 요구할 때 우리가 낮은 버전으로 고정해 버리는 역효과가 난다.

적용됐는지는 트리로 본다.

{% raw %}
```bash
mvn dependency:tree -Dincludes=com.google.guava
# [INFO] +- com.example:grpc-sdk:jar:1.2.3:compile
# [INFO]    \- com.google.guava:guava:jar:33.7.2-android:compile (version managed from 33.6.0-android)
```
{% endraw %}

`(version managed from ...)`가 붙으면 `dependencyManagement`가 적용된 것이다.

---

## 3. 패치가 없는 라이브러리: exclusion 후 포크로 교체

`lz4-java`가 문제였다. 보고된 취약점은 신뢰할 수 없는 압축 데이터를 풀 때 생기는 것들이다(디코더 범위 밖 메모리 접근, 출력 버퍼 미초기화 등). 그런데 `org.lz4:lz4-java`는 원본 저장소가 archived 상태다. 마지막 1.8.1에도 패치가 없다. **버전을 올려서 해결할 수 없다.**

실제 수정은 포크인 `at.yawk.lz4:lz4-java` 1.11.4에 들어갔다. groupId가 다르므로 `dependencyManagement`로 버전만 바꾸는 방법은 쓸 수 없다. 원본을 **제외하고** 포크를 **직접 추가**한다.

{% raw %}
```xml
<dependency>
    <groupId>org.elasticsearch.client</groupId>
    <artifactId>elasticsearch-rest-high-level-client</artifactId>
    <version>${elasticsearch.version}</version>
    <!-- org.lz4:lz4-java는 저장소가 archived 상태라 패치가 없어 포크(at.yawk.lz4)로 교체 -->
    <exclusions>
        <exclusion>
            <groupId>org.lz4</groupId>
            <artifactId>lz4-java</artifactId>
        </exclusion>
    </exclusions>
</dependency>

<dependency>
    <groupId>at.yawk.lz4</groupId>
    <artifactId>lz4-java</artifactId>
    <version>1.11.4</version>
</dependency>
```
{% endraw %}

### 포크 교체 전에 확인할 것

포크는 같은 패키지(`net.jpountz.lz4`)와 같은 클래스를 제공해야 원래 호출자가 깨지지 않는다. 다음을 봤다.

- 포크 jar 안의 패키지 이름이 원본과 같은가. `unzip -l`로 확인한다.
- 원본을 끌고 오던 라이브러리(여기서는 Elasticsearch 클라이언트 jar)가 실제로 어느 클래스를 참조하는가. `jdeps` 또는 소스에서 본다.
- 우리 코드가 그 라이브러리를 직접 쓰는가. 이번 경우 lz4는 Elasticsearch 노드 간 transport(9300 포트) 압축용이고, 우리는 REST(9200)만 쓴다. 코드 경로가 닿지 않는다.

마지막 항목은 중요한 갈림길이다. **코드가 닿지 않으면** 교체 대신 VEX로 `code_not_reachable` 판정을 하는 선택도 있다. 사실 처음 보고 때는 그렇게 처리했다. 이번에 교체로 돌아선 이유는 두 가지다. 포크가 안정 버전을 냈고, 같은 라이브러리에 취약점이 **일곱 건 넘게** 누적되어 매 빌드마다 판정을 반복하는 비용이 교체 비용을 넘었다.

exclusion이 하나 빠지면 두 lz4가 classpath에 공존한다. 트리에서 `org.lz4`가 완전히 사라졌는지 본다.

{% raw %}
```bash
mvn dependency:tree -Dincludes=org.lz4,at.yawk.lz4
```
{% endraw %}

---

## 고치지 않는 항목은 도구에서 끊는다

같은 결과표에 두 건이 더 있었다.

- querydsl: 보고된 CVE가 우리가 쓰지 않는 모듈에 해당. 영향 없음.
- jjwt: 권고 자체가 철회됨.

이런 항목은 `pom.xml`로 할 일이 없다. Dependency-Track에서 해당 finding을 `not_affected`로 판정하거나 suppress한다. 그래야 다음 빌드의 결과표에서 사라지고, 진짜 새 취약점이 묻히지 않는다. 판정 근거는 도구의 analysis comment에 적는다. VEX 파일로 내보내는 절차는 이전 글에 있다.

---

## 적용 후

빌드와 단위 테스트를 돌렸다. 교체한 라이브러리 경로를 실제로 타는 테스트는 없었으므로, 통과는 "컴파일과 기존 동작이 깨지지 않았다"까지다. 압축 경로를 쓰지 않는다는 판단은 코드 분석에 근거한다.

커밋 메시지에는 라이브러리별로 **어떤 권고(GHSA 번호)에 대응한 것인지** 적었다. 몇 달 뒤 "이 오버라이드 지워도 되나"를 판단할 때 그 번호가 출발점이 된다.

---

## 정리

| 상황 | 방법 | 확인 |
|---|---|---|
| 직접 선언한 의존성 | 버전 올림. Boot BOM 관리 항목은 `<properties>`의 `xxx.version` 속성 | `mvn help:effective-pom` |
| 전이 의존성, 같은 groupId에 패치 있음 | `<dependencyManagement>`로 버전 고정. 제거 조건 주석 | `dependency:tree`의 `version managed from` |
| 패치가 포크에만 있음 | 원본 `<exclusion>` + 포크 `<dependency>` 직접 추가. 패키지 호환 확인 | 트리에서 원본 groupId 소멸 |
| 코드가 닿지 않음 | 교체 또는 VEX `code_not_reachable`. 누적 건수와 포크 안정성으로 결정 | 호출 경로 분석 |
| 영향 없음 · 권고 철회 | `pom.xml` 변경 없음. 도구에서 판정·suppress | 다음 빌드 결과표 |

Maven과 Dependency-Track 기준으로 썼다. Gradle은 `constraints`와 `exclude`로 같은 일을 한다. 포크 교체 뒤 실제 압축 경로의 동작 검증은 하지 않았다. 우리 서비스가 그 경로를 쓰지 않기 때문이다.
