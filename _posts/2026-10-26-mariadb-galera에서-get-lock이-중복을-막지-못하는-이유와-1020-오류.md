---
title: "MariaDB Galera에서 GET_LOCK이 중복을 막지 못하는 이유와 1020 오류"
date: 2026-10-26 10:20:00 +0900
categories: ["Database", "MariaDB"]
tags: ["mariadb", "galera", "동시성", "트랜잭션"]
permalink: /posts/mariadb-galera에서-get-lock이-중복을-막지-못하는-이유와-1020-오류/
---

사용자가 접속할 때마다 세션 row를 INSERT하는 서비스가 있었다. 같은 사용자의 `ACTIVE` row가 두 건씩 생기는 문제가 있어서 `GET_LOCK`으로 직렬화했다. 배포 후에도 중복은 계속 생겼다.

원인을 찾아 보니 DB가 **Galera 3노드 클러스터**였다. 같은 시기에 `Record has changed since last read in table` 오류(1020)와 데드락(1213)도 로그에 쌓이고 있었다. 세 현상의 뿌리는 같았다. **하나의 DB처럼 보이는 주소 뒤에 여러 노드가 있다**는 점이다.

이 글은 다음 내용을 정리한다.

- `GET_LOCK`이 클러스터 전체 락이 아닌 이유
- 락 해제 시점을 잘못 잡았을 때의 문제
- 여러 인스턴스가 같은 이벤트를 처리할 때 1020이 나는 이유와 해결

---

## 1. 증상

접속 세션 목록 API에서 같은 사용자의 `ACTIVE` row가 두 건 나왔다. 두 row는 `createdAt`이 초 단위로 같고 접속 시각만 수백 ms 차이였다.

원인을 처음에는 이렇게 봤다.

- 같은 사용자의 로그인이 거의 동시에 두 번 들어온다 (탭 두 개, 재연결).
- 사용자별 unique 제약이 없다 (이력 보관을 위해 제거했다).
- "조회 후 없으면 INSERT" 흐름이라 둘 다 빈 조회를 본다.

전형적인 check-then-insert 경합이다. 그래서 같은 사용자 키로 `GET_LOCK`을 잡은 뒤 조회와 저장을 하도록 바꿨다.

{% raw %}
```sql
SELECT GET_LOCK(?, 5);      -- 사용자 키의 hash로 이름을 만든다
-- 활성 row 조회 → 있으면 UPDATE, 없으면 INSERT
SELECT RELEASE_LOCK(?);
```
{% endraw %}

단일 DB에서는 이 방식이 맞다. 그런데 운영에서는 중복이 다시 생겼다.

---

## 2. GET_LOCK은 노드 로컬이다

운영 로그를 분류하면서 확인한 구조는 다음과 같다.

- DB는 Galera 3노드이고, 앱은 **단일 Service 주소**로 접속한다.
- 앱은 커넥션 풀(크기 10)을 쓴다.
- Kubernetes의 Service는 **TCP 커넥션 단위**로 백엔드를 고른다.

그래서 인스턴스가 하나여도 풀의 커넥션 10개가 서로 다른 노드에 흩어진다.

{% raw %}
```text
요청 A ─ 커넥션 #3 ─ 노드 0 ─ GET_LOCK('member-1') 성공
요청 B ─ 커넥션 #7 ─ 노드 2 ─ GET_LOCK('member-1') 성공   ← 같은 이름인데도 성공
         ↓
둘 다 활성 row 없음으로 보고 INSERT
         ↓
unique가 없으므로 Galera가 두 row를 모두 commit
```
{% endraw %}

`GET_LOCK`은 **해당 노드의 서버 안에서만** 유효한 이름 있는 락이다. Galera는 row 변경은 복제하지만 이 락은 복제하지 않는다. 노드가 다르면 같은 이름의 락을 둘 다 얻는다.

운영 로그에서도 같은 패턴이 보였다. 같은 인스턴스의 다른 스레드가 같은 사용자, 같은 채널로 `Creating new session`을 남기는 쌍이 세 번 있었고, 간격은 32ms, 236ms, 757ms였다. 반면 `lock acquire timeout` 로그는 한 건도 없었다. 락 대기 자체가 일어나지 않았다는 뜻이다.

처음 설계에서는 "`GET_LOCK`은 DB만으로 클러스터 직렬화가 된다"고 가정했다. 이 가정이 단일 노드 기준이었다.

---

## 3. 해결: 앱 레벨 락을 앞에 둔다

DB 스키마를 바꿀 수 없는 상황이었다. 활성 row에 대한 partial unique(generated column + UNIQUE)가 가장 확실한 방법이지만, 이미 쌓인 중복 row 때문에 인덱스를 만들 수 없고 마이그레이션도 범위 밖이었다. 단일 writer 엔드포인트도 인프라 변경이라 제외했다.

그래서 **Redis 락을 `GET_LOCK` 앞에 추가**했다. 순서는 다음과 같다.

{% raw %}
```text
Redis 락 획득 → GET_LOCK → 활성 row 조회 → UPDATE 또는 INSERT
→ (트랜잭션 종료 후) GET_LOCK 해제 → Redis 락 해제
```
{% endraw %}

핵심 계약은 다음과 같다.

| 항목 | 값 |
|---|---|
| key | `{prefix}:{shop}:{memberId}:loginLock` |
| value | 호출마다 만드는 UUID token |
| TTL | 10초 |
| 획득 | `setIfAbsent`를 50ms 간격으로 재시도, 최대 5초 |
| 실패 | 예외를 던지고 INSERT하지 않는다 |
| 해제 | token이 일치할 때만 삭제 (compare-and-delete) |

토큰 비교 삭제는 Lua 스크립트로 구현한다. TTL이 먼저 지나 다른 요청이 같은 키를 얻은 뒤에 이전 요청이 `DEL`을 호출하면 남의 락을 지우게 되기 때문이다.

{% raw %}
```lua
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
```
{% endraw %}

`GET_LOCK`은 남겨 뒀다. Redis를 쓰지 않는 환경이나 Redis 장애 시에도 **같은 노드 안에서는** 보호하기 위해서다. Redis 호출이 예외를 던지면 경고를 남기고 `GET_LOCK`만으로 진행한다. 가용성을 정합성보다 우선한 선택이고, 반대로 로그인을 거부하는 방안도 있었다.

---

## 4. 락 해제는 트랜잭션이 끝난 뒤에

락을 어디서 해제하느냐도 중요했다. INSERT 직후, commit 전에 풀면 안 된다.

{% raw %}
```text
요청 A: 락 획득 → INSERT → 락 해제 → (아직 commit 전)
요청 B:                      락 획득 → 조회 → A의 row가 보이지 않음 → INSERT
```
{% endraw %}

락이 풀린 시점에 A의 row는 아직 커밋되지 않았다. B는 그 row를 볼 수 없다. 그래서 락은 **commit이나 rollback 이후**에 풀어야 한다. Spring에서는 `TransactionSynchronization.afterCompletion`을 쓴다.

{% raw %}
```java
TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
    @Override
    public void afterCompletion(int status) {
        repository.releaseDbLock(lockName);   // DB 락 먼저
        cache.deleteIfTokenMatches(redisKey, token);   // 그다음 Redis 락
    }
});
```
{% endraw %}

주의할 점이 하나 더 있다. `GET_LOCK`은 **커넥션 단위**다. 락을 건 커넥션과 해제하는 커넥션이 같아야 한다. 락 획득과 해제 메서드에 자체 `@Transactional`을 붙이면 afterCompletion 시점에 새 트랜잭션이 다른 커넥션을 잡을 수 있고, 원래 커넥션에는 락이 풀에 남는다. 그래서 이 메서드들에는 `@Transactional`을 붙이지 않았다.

---

## 5. 같은 뿌리의 두 번째 문제: 1020

같은 시기에 다른 오류가 보였다. 이벤트 스트림으로 "연결 삭제" 이벤트를 받아 세션을 종료 처리하는 코드에서 나온 오류다.

{% raw %}
```text
ERROR: Record has changed since last read in table 'member_sessions'
```
{% endraw %}

서비스는 3개 인스턴스로 떠 있고, 같은 이벤트를 **모든 인스턴스가** 받아 처리한다 (인스턴스마다 구독하는 구조다). 종료 처리 흐름은 다음과 같았다.

{% raw %}
```text
@Transactional (기본 REPEATABLE READ)
  1. SELECT: 해당 사용자·채널의 활성 row 조회  ← snapshot 고정
  2. UPDATE ... WHERE id IN (...) AND status = 'ACTIVE'
```
{% endraw %}

먼저 commit한 인스턴스는 성공한다. 늦은 인스턴스는 이미 고정된 snapshot 기준으로 읽은 row를 UPDATE하려는데, 그 row가 snapshot 이후에 다른 트랜잭션에 의해 바뀌어 있다. MariaDB의 snapshot isolation 검사가 이를 막고 1020을 반환한다. 부하 테스트 50회 중 27회에서 138건이 발생했다.

이 검사는 MariaDB 버전과 `innodb_snapshot_isolation` 설정에 따라 동작이 다를 수 있다. 이 환경에서는 켜져 있었다.

### 해결 1. READ COMMITTED 조건부 UPDATE

종료 처리 트랜잭션의 격리 수준을 `READ_COMMITTED`로 낮췄다.

{% raw %}
```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public int closeActive(String memberId, int channel, LocalDateTime eventTime) { ... }
```
{% endraw %}

RC에서는 UPDATE가 최신 commit 상태를 기준으로 `status = 'ACTIVE'` 조건을 다시 평가한다. 다른 인스턴스가 먼저 종료했다면 조건에 맞는 row가 없어서 **0 row를 갱신하고 정상 종료**한다. 오류가 아니라 no-op이 된다. 인스턴스가 여러 개 같은 이벤트를 처리하는 구조(fan-out)는 그대로 둬도 된다. 한 인스턴스가 실패해도 다른 인스턴스가 처리하는 안전망이 되기 때문이다.

### 해결 2. 세대 조건

격리 수준만 바꾸면 새 문제가 생긴다. 이벤트를 늦게 처리하는 동안 같은 사용자가 같은 채널로 **재접속**하면, 새 세션 row까지 종료할 수 있다.

그래서 UPDATE 조건에 이벤트 시각을 넣었다.

{% raw %}
```sql
UPDATE member_sessions
   SET status = CASE status
                  WHEN 'ACTIVE' THEN 'CLOSED'
                  WHEN 'PENDING_FORCE_CLOSE' THEN 'FORCE_CLOSED'
                END,
       closed_at = COALESCE(closed_at, :eventTime)
 WHERE id IN (:ids)
   AND status IN ('ACTIVE', 'PENDING_FORCE_CLOSE')
   AND (last_seen_at IS NULL OR last_seen_at <= :eventTime);
```
{% endraw %}

이벤트보다 늦게 접속하거나 갱신된 row는 **이벤트 이후의 세션**이다. 그 세션은 자기 삭제 이벤트가 처리한다.

이 조건에는 한계가 있다. 이벤트 발생 시각과 `last_seen_at`는 서로 다른 서버의 시계에서 나온다. 같은 클러스터의 NTP 오차는 ms 단위이고, 접속부터 종료 이벤트까지는 보통 초 단위 이상이어서 실제 영향은 작다고 판단했다. 허용 오차는 두지 않았다.

---

## 6. UPDATE의 잠금 범위도 함께 줄였다

데드락(1213) 로그도 같이 분석했다. 125건의 분류는 다음과 같았다.

| 발생 시점 | 건수 | 추정 원인 |
|---|---:|---|
| COMMIT 시점 | 22 | Galera certification 충돌 |
| STATEMENT 시점·불명 | 103 | 넓은 잠금 범위의 UPDATE |

COMMIT 시점 충돌은 InnoDB가 commit 단계에서 row lock을 새로 잡지 않기 때문에 Galera의 certification 충돌로 볼 수 있다. 나머지 103건은 앱 로그만으로는 InnoDB 로컬 데드락인지 Galera의 brute-force abort인지 구분하지 못했다. 다만 둘 다 **잠금 범위가 넓을수록 늘어난다**는 점은 같다.

잠금 범위가 넓은 곳이 두 군데 있었다.

1. 종료 UPDATE가 `WHERE member_id = ? AND channel = ? AND status IN (...)`이었다. 이력 보관을 위해 unique 제약을 제거하면서 `member_id`를 쓸 수 있는 유일한 인덱스도 함께 사라져 풀스캔이 됐다. REPEATABLE READ에서 인덱스 없는 UPDATE는 스캔한 모든 row에 next-key lock을 건다.
2. 마지막 접속 시각을 일괄 갱신하는 bulk UPDATE가 상점의 이력 row 전체를 스캔하며 잠갔다.

대응은 다음과 같다.

- 종료 UPDATE는 먼저 조회한 PK 목록(`id IN (...)`)으로만 갱신한다. 조회 결과가 비어 있으면 UPDATE를 건너뛴다. PK row lock만 잡는다.
- bulk UPDATE는 `READ_COMMITTED`로 실행한다. RC에서는 조건에 맞지 않는 row의 잠금을 즉시 풀고 gap lock도 걸지 않는다.

---

## 7. 남는 한계

- **Galera 적용 지연**: 요청 B가 락을 잡았는데 B의 노드가 A의 row를 아직 적용하지 못했다면 중복이 생길 수 있다. 창이 ms 단위이고 50ms 재시도가 대부분 흡수하지만 이론상 남는다. 근본 해결은 DB의 unique 제약이다.
- **COMMIT 시점 certification 충돌**: 앱 코드로 없앨 수 없다. 단일 writer 구성이 필요하다. 락 범위를 줄여서 빈도를 낮추는 데 그쳤다.
- **효과 검증**: 로컬이나 단위 테스트로는 Galera 다중 노드 경합을 재현할 수 없다. 단위·H2 테스트로 계약만 확인했다. 배포 후 1213과 1020이 실제로 줄었는지는 운영 로그로 확인해야 하고, 이 글을 쓰는 시점에는 확인하지 못했다.

---

## 8. 정리

| 문제 | 원인 | 대응 |
|---|---|---|
| 중복 row | `GET_LOCK`이 노드 로컬 | 앱 레벨(Redis) 락을 앞에 두고 `GET_LOCK`은 보조로 유지 |
| 락이 다른 요청에 무효 | commit 전에 락 해제 | `afterCompletion`에서 해제 |
| 락이 풀에 남음 | 락 메서드의 자체 트랜잭션 | 락 메서드에 `@Transactional` 금지 |
| 1020 | 여러 인스턴스의 fan-out + RR snapshot | READ COMMITTED 조건부 UPDATE |
| 재접속 세션 오종료 | 늦게 처리된 종료 이벤트 | 이벤트 시각 기반 세대 조건 |
| 데드락 | 인덱스 없는 UPDATE의 넓은 잠금 | PK 범위 UPDATE, bulk는 RC |

Galera 같은 다중 writer 환경에서 기억할 점은 두 가지다.

1. DB 커넥션이 어느 노드로 가는지 앱은 모른다. **노드 로컬 기능(`GET_LOCK`, 로컬 락)에 클러스터 전체의 보장을 기대하면 안 된다.**
2. 여러 인스턴스가 같은 이벤트를 처리하는 구조에서는 **늦은 쪽이 실패하지 않고 no-op이 되도록** 쓰기를 조건부 UPDATE로 설계한다.
