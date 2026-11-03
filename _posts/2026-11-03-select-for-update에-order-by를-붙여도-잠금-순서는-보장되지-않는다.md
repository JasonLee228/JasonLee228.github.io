---
title: "SELECT FOR UPDATE에 ORDER BY를 붙여도 잠금 순서는 보장되지 않는다"
date: 2026-11-03 09:10:00 +0900
categories: ["Database", "MariaDB"]
tags: ["mariadb", "innodb", "jpa", "querydsl", "동시성", "데드락"]
permalink: /posts/select-for-update에-order-by를-붙여도-잠금-순서는-보장되지-않는다/
---

## 여러 행을 함께 잠그면 순서가 문제다

한 트랜잭션이 여러 행을 함께 잠그는 일은 흔하다. 재고 여러 개를 한 번에 차감하거나, 상태 여러 개를 한 번에 바꾸는 경우다.

두 트랜잭션이 같은 행들을 **다른 순서로** 잠그면 데드락(deadlock, 서로 상대의 잠금을 기다리는 교착)이 난다.

{% raw %}
```text
트랜잭션 X:  행 3 잠금 -> 행 1 잠금 시도 (Y가 쥐고 있어 대기)
트랜잭션 Y:  행 1 잠금 -> 행 3 잠금 시도 (X가 쥐고 있어 대기)
```
{% endraw %}

잘 알려진 해법은 **모든 경로가 같은 순서로 잠그는 것**이다. 그래서 이런 쿼리를 쓰기 쉽다.

{% raw %}
```sql
SELECT * FROM item
 WHERE id IN (1, 2, 3)
 ORDER BY sort_key
 FOR UPDATE;
```
{% endraw %}

`sort_key` 순으로 잠글 것 같다. 하지만 그렇지 않다. 이 글은 그 이유와 확인 방법, 대안을 정리한다.

실험은 MariaDB 10.11.15 컨테이너에서 했다. 테이블은 이렇게 만들었다. `id`가 커질수록 `sort_key`는 작아진다. 두 순서가 정반대다.

{% raw %}
```sql
CREATE TABLE item (
  id INT PRIMARY KEY,
  sort_key VARCHAR(10) NOT NULL,
  qty INT,
  KEY ix_sort (sort_key)
) ENGINE=InnoDB;

-- id 1..1000, sort_key 는 k0999 .. k0000
INSERT INTO item SELECT seq, CONCAT('k', LPAD(1000 - seq, 4, '0')), 0 FROM seq_1_to_1000;
```
{% endraw %}

---

## ORDER BY는 결과 순서이지 잠금 순서가 아니다

InnoDB의 `FOR UPDATE`는 행을 **읽는 순간** 잠근다. 행을 읽는 순서는 옵티마이저가 고른 인덱스가 정한다. `ORDER BY` 정렬은 그다음 단계다.

실행 계획부터 보자.

{% raw %}
```text
EXPLAIN SELECT * FROM item WHERE id IN (1,2,3) ORDER BY sort_key FOR UPDATE;

type   key      rows  Extra
range  PRIMARY  3     Using where; Using filesort
```
{% endraw %}

- `key`가 `PRIMARY`다. 행은 기본 키 순서(1, 2, 3)로 읽힌다.
- `Using filesort`는 다 읽은 뒤 따로 정렬했다는 뜻이다.

결과는 `sort_key` 순(3, 2, 1)으로 온다. 하지만 잠금은 이미 id 순(1, 2, 3)으로 걸렸다.

### 직접 확인: 기다리는 동안 무엇을 잠갔나

세 세션으로 확인했다.

1. 세션 A가 `id = 1`만 잠그고 쥐고 있는다.
2. 세션 B가 위의 `ORDER BY sort_key FOR UPDATE` 쿼리를 실행한다. 세션 B는 대기한다.
3. 세션 C가 세션 B가 기다리는 동안 `id = 3`과 `id = 2`를 `NOWAIT`로 잠가 본다.

{% raw %}
```sql
-- 세션 C
BEGIN;
SELECT id FROM item WHERE id = 3 FOR UPDATE NOWAIT;   -- 성공
SELECT id FROM item WHERE id = 2 FOR UPDATE NOWAIT;   -- 성공
ROLLBACK;
```
{% endraw %}

둘 다 성공했다. `information_schema.INNODB_TRX`에서도 세션 B는 `LOCK WAIT`, `trx_rows_locked = 1`이었다.

`sort_key` 순서였다면 세션 B는 3과 2를 먼저 잠그고 1에서 기다렸어야 한다. 실제로는 기본 키 순서의 첫 행인 1에서 바로 멈췄다. 3과 2는 잠그지 않았다.

### 데드락 재현

이제 다른 경로 하나가 `sort_key` 순서대로 한 행씩 잠근다고 하자. 위 쿼리와 섞으면 데드락이 난다.

{% raw %}
```sql
-- 세션 X: sort_key 순으로 한 행씩 (3 -> 1)
BEGIN;
SELECT id FROM item WHERE id = 3 FOR UPDATE;
SELECT SLEEP(3);
SELECT id FROM item WHERE id = 1 FOR UPDATE;

-- 세션 Y: X 가 3 을 잠근 직후 실행
BEGIN;
SELECT id FROM item WHERE id IN (1,2,3) ORDER BY sort_key FOR UPDATE;
```
{% endraw %}

세션 Y는 1과 2를 잠그고 3에서 기다린다. 세션 X는 1에서 기다린다. 이번 실행에서는 세션 X가 롤백됐다.

{% raw %}
```text
ERROR 1213 (40001): Deadlock found when trying to get lock; try restarting transaction
```
{% endraw %}

`SHOW ENGINE INNODB STATUS`의 `LATEST DETECTED DEADLOCK` 절에 두 쿼리와 기다린 잠금이 남는다.

`sort_key` 인덱스를 타게 만들면 순서가 맞을 수도 있다. 하지만 실행 계획은 데이터 분포와 통계에 따라 바뀐다. 정확성이 걸린 잠금 순서를 옵티마이저 선택에 맡기면 안 된다.

---

## 대안: 순서는 먼저 정하고, 잠금은 한 행씩

두 단계로 나눈다.

1. 잠글 id 목록을 **잠금 없이** 원하는 순서로 조회한다. 엔티티가 아니라 id만 읽는다.
2. 그 순서대로 한 행씩 `PESSIMISTIC_WRITE`(`FOR UPDATE`)로 잠그며 읽는다.

JPA와 QueryDSL로 쓰면 이렇다.

{% raw %}
```java
// 1단계: 순서만 정한다. 잠금 없음, 엔티티 로딩 없음
List<Long> idsInLockOrder = queryFactory.select(item.id)
        .from(item)
        .where(item.id.in(ids))
        .orderBy(item.sortKey.asc())
        .fetch();

// 2단계: 그 순서대로 한 행씩 잠근다
List<Item> locked = new ArrayList<>();
for (Long id : idsInLockOrder) {
    Item row = queryFactory.selectFrom(item)
            .where(item.id.eq(id))
            .setLockMode(LockModeType.PESSIMISTIC_WRITE)
            .fetchOne();
    if (row != null) {
        locked.add(row);
    }
}
```
{% endraw %}

한 쿼리가 한 행만 잠그므로 잠금 순서가 곧 반복문 순서다. 실행 계획이 바뀌어도 순서가 흔들리지 않는다.

### 1단계에서 엔티티를 읽으면 안 되는 이유

1단계에서 `selectFrom(item)`으로 엔티티를 읽으면 함정이 생긴다. JPA 영속성 컨텍스트(persistence context, 트랜잭션 동안 읽은 엔티티를 보관하는 1차 캐시)에 **잠그기 전 상태**가 올라간다. 2단계에서 같은 행을 잠금 조회해도, 이미 관리 중인 엔티티 인스턴스가 그대로 반환될 수 있다. 그러면 잠근 뒤의 최신 값을 못 본다.

그래서 1단계는 id만 읽고, 엔티티는 잠금 조회로만 처음 읽는다.

### 메서드는 호출자 트랜잭션 안에서만

잠금은 트랜잭션이 끝날 때 풀린다. 이 조회 메서드가 자기 트랜잭션을 열고 닫으면, 잠그자마자 풀린다. 그래서 `@Transactional(propagation = Propagation.MANDATORY)`를 붙인다. 호출자 트랜잭션이 없으면 예외가 나므로, 트랜잭션 밖에서 부르는 실수를 테스트에서 바로 잡는다.

---

## 잠근 뒤에 다시 비교한다

같은 행을 바꾸려는 요청 두 개가 동시에 오면, 하나는 잠금을 기다린다. 첫 요청이 커밋하면 두 번째 요청이 잠금을 얻고 최신 값을 읽는다.

이때 변경 여부를 **잠그기 전 값**으로 판단하면 두 요청이 모두 "변경했다"고 응답한다. 실제 변경은 한 번뿐이다. 그래서 비교는 잠근 행으로 한다.

{% raw %}
```java
List<Item> rows = repository.findByIdsForUpdate(ids);
List<Item> changed = rows.stream()
        .filter(row -> row.getStatus() != target)   // 잠근 뒤의 값으로 비교
        .toList();
```
{% endraw %}

UPDATE 문에도 `status <> :target` 같은 조건을 걸면 한 번 더 막을 수 있다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 문제 | 두 경로가 같은 행 여러 개를 다른 순서로 잠그면 데드락 |
| 함정 | `ORDER BY ... FOR UPDATE`는 결과 순서만 정한다. 잠금은 읽는 인덱스 순서 |
| 확인 | `EXPLAIN`에서 `key`와 `Using filesort`. 대기 중에 다른 행을 `NOWAIT`로 잠가 본다 |
| 대안 | 잠글 id를 잠금 없이 순서대로 조회하고, 한 행씩 `PESSIMISTIC_WRITE` |
| 주의 1 | 1단계에서 엔티티를 읽지 않는다. 영속성 컨텍스트가 잠그기 전 상태를 돌려줄 수 있다 |
| 주의 2 | 잠금 메서드는 `Propagation.MANDATORY`로 호출자 트랜잭션 안에서만 |
| 주의 3 | 변경 여부는 잠근 뒤의 값으로 비교한다 |
| 비용 | 행마다 쿼리 한 번. id가 많으면 왕복이 늘어난다 |

행마다 쿼리를 보내는 비용은 측정하지 않았다. 한 번에 잠그는 행이 적으면 문제가 되지 않는다. 대량 처리라면 반대로 모든 경로를 기본 키 순서로 통일하는 쪽이 싸다. `WHERE id IN (...) FOR UPDATE`가 기본 키 순서로 읽는다는 점을 이용하는 방법이다. 다만 이것도 실행 계획에 기대는 방법이니 `EXPLAIN`으로 확인해 둔다.
