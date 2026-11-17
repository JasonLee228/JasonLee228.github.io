---
title: "read-only 트랜잭션이 방금 지운 row를 다시 센다: MariaDB Connector/J와 read/write split 프록시의 복제 지연"
date: 2026-11-16 18:00:00 +0900
categories: ["Database", "MariaDB"]
tags: ["mariadb", "spring", "transaction", "replication"]
permalink: /posts/read-only-트랜잭션이-방금-지운-row를-다시-센다-mariadb-connector-j와-read-write-split-복제-지연/
---

## 다 지웠는데 남았다고 한다

테넌트 하나를 지우는 기능이 실패했다. 응답은 "remaining child rows exist"였다. 삭제가 끝난 뒤 남은 row를 세는 검증 단계가 실패한 것이다.

로그를 보면 이상했다.

- 지울 row는 1,435개였다. chunk 크기는 1,000이었다.
- 검증 단계는 남은 row가 435개라고 했다.
- 435는 정확히 **마지막 chunk** 크기다.

마지막 chunk의 삭제는 commit까지 끝났다. 그런데 바로 뒤의 count는 그 삭제를 보지 못했다. 15초 앞서 다른 테넌트(1,632 row)를 지운 요청은 성공했다. 그 요청은 마지막 삭제와 검증 사이 간격이 더 길었다.

시간이 지나면 보이는 데이터, 즉 **복제 지연**의 모양이다.

---

## 구조

코드는 대략 이렇다.

{% raw %}
```java
@Repository
@Transactional(readOnly = true)          // 클래스 기본값: 읽기 전용
public class TenantDeletionRepository {

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public int deleteChunk(String tenantId, int size) { ... }   // chunk마다 새 트랜잭션으로 commit

    public long countRemainingChildRows(String tenantId) { ... } // 클래스 기본값을 그대로 씀
}
```
{% endraw %}

- 서비스 메서드에는 바깥 트랜잭션이 없다.
- chunk 삭제는 `REQUIRES_NEW`라 chunk마다 primary에 commit된다.
- 검증 count는 메서드에 `@Transactional`이 없다. 그래서 클래스 기본값 `readOnly = true`로 실행된다.

DB 앞에는 read/write split 프록시가 있다. 쓰기는 primary로, 읽기 전용 트랜잭션은 replica로 보낼 수 있는 구성이다.

---

## readOnly가 서버까지 가는 경로

`readOnly = true`는 Spring 안에서만 쓰이는 힌트가 아니다. 경로는 세 단계다.

1. Spring 트랜잭션 매니저가 트랜잭션을 시작할 때 JDBC `Connection.setReadOnly(true)`를 부른다.
2. MariaDB Connector/J는 이 호출을 받아 서버에 SQL을 보낸다.
3. 프록시는 이 세션이 읽기 전용이라는 것을 보고 replica로 보낼 수 있다.

2번은 드라이버 코드에서 확인했다. MariaDB Connector/J 3.5.11 `StandardClient.setReadOnly`다.

{% raw %}
```java
public void setReadOnly(boolean readOnly) throws SQLException {
  ...
  if (conf.readOnlyPropagatesToServer()
      && context.getVersion().versionGreaterOrEqual(5, 6, 5)
      && context.isServerReadOnly() != readOnly) {
    execute(
        new QueryPacket(
            readOnly
                ? "SET SESSION TRANSACTION READ ONLY"
                : "SET SESSION TRANSACTION READ WRITE"),
        true);
    context.setServerReadOnly(readOnly);
  }
}
```
{% endraw %}

옵션 기본값은 `Configuration`에 있다.

{% raw %}
```java
this.readOnlyPropagatesToServer =
    builder.readOnlyPropagatesToServer == null || builder.readOnlyPropagatesToServer;
```
{% endraw %}

설정하지 않으면 `true`다. 즉 기본 설정에서 `readOnly = true` 트랜잭션은 서버에 `SET SESSION TRANSACTION READ ONLY`를 보낸다. 프록시가 이 신호로 라우팅을 바꾸면 검증 count는 replica에서 실행된다. replica가 마지막 chunk 삭제를 아직 받지 못했다면 435개가 남아 있다고 답한다.

> 이번 환경에서 프록시의 라우팅 로그로 직접 확인하지는 않았다. 증상(마지막 chunk 크기만 남음, 간격이 길면 성공)과 드라이버 동작이 맞아서 이 경로를 원인으로 판단했다. 수정 후 같은 시나리오의 재검증이 남아 있다.

---

## 수정: 방금 쓴 결과를 검증하는 조회는 read-write로 둔다

수정은 검증 메서드에 메서드 단위 `@Transactional`을 붙인 것뿐이다. 기존 Javadoc에 설명 단락 3줄(`<p>`부터 `</p>`까지)을 넣고 annotation 1줄을 붙였다.

{% raw %}
```java
/**
 * ...
 * <p>
 * read-only 트랜잭션은 프록시가 replica로 보내 복제 지연 시 삭제된 row를 잔여로 집계하므로 read-write로 primary에서 조회한다.
 * </p>
 */
@Transactional   // readOnly=false
public long countRemainingChildRows(String tenantId) { ... }
```
{% endraw %}

메서드의 `@Transactional`은 클래스의 `@Transactional(readOnly = true)`보다 우선한다. 기본값이 `readOnly = false`이므로 드라이버가 `READ ONLY`를 보내지 않고, 프록시도 primary로 보낸다.

두 가지를 같이 확인했다.

- **프록시 확인.** 같은 클래스 안 호출이면 Spring 트랜잭션 프록시를 거치지 않아 annotation이 무시된다. 이 메서드는 서비스에서 repository bean으로 호출되므로 프록시를 거친다. 테스트에서 bean이 CGLIB proxy인지, 각 메서드의 readOnly 속성이 무엇인지 확인했다.
- **다른 readOnly 메서드는 그대로 둔다.** 화면 조회처럼 약간 늦은 데이터를 읽어도 되는 메서드는 replica로 가는 편이 낫다. 문제는 "방금 쓴 것을 확인하는" 조회뿐이다.

---

## 다른 선택지

| 방법 | 효과 | 단점 |
|---|---|---|
| 검증 메서드만 read-write `@Transactional` (선택) | 그 조회만 primary로 간다 | 메서드마다 판단해야 한다 |
| 드라이버 `readOnlyPropagatesToServer=false` | 모든 readOnly 트랜잭션이 서버에 신호를 보내지 않는다 | replica로 읽기를 분산하던 효과가 전부 사라진다 |
| 삭제와 검증을 한 트랜잭션으로 묶음 | 같은 연결에서 읽으므로 지연이 없다 | chunk commit으로 잠금과 undo를 줄이려던 설계와 충돌한다 |

이번에는 영향 범위가 가장 작은 첫 번째를 골랐다. 나머지 두 방법은 시험하지 않았다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 증상 | 삭제 직후 검증 count가 마지막 chunk 크기만큼 남았다고 함. 간격이 길면 성공 |
| 원인 | 클래스 기본 `@Transactional(readOnly = true)`로 실행된 검증이 replica에서 읽음 |
| 경로 | Spring `setReadOnly(true)` → Connector/J `SET SESSION TRANSACTION READ ONLY`(기본 `readOnlyPropagatesToServer=true`) → 프록시가 replica로 라우팅 |
| 수정 | 방금 쓴 결과를 검증하는 메서드에 read-write `@Transactional` |
| 점검 대상 | 클래스에 `readOnly = true`를 깔아 둔 repository에서 "쓰기 직후 읽기" 메서드 |

드라이버 동작은 MariaDB Connector/J 3.5.11 소스에서 확인했다. 클래스 단위 `readOnly = true`는 편하지만, read/write split 환경에서는 "이 조회가 최신 데이터를 봐야 하는가"를 메서드마다 다시 묻게 만든다.
