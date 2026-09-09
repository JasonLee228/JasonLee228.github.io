---
title: "08. Elasticsearch를 Database처럼 쓸 때의 제약"
date: 2026-05-20 02:59:25 +0000
categories: ["Elasticsearch", "클러스터운영"]
tags: ["클러스터운영", "elasticsearch"]
permalink: /posts/08-elasticsearch를-database처럼-쓸-때의-제약/
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [07. Write, Update, Delete, Bulk](/posts/07-write-update-delete-bulk/)
>
> - 다음: [09. MVP Architecture Walkthrough](/posts/09-mvp-architecture-walkthrough/)

Elasticsearch를 주 저장소처럼 사용할 수는 있지만, RDB와 같은 보장을 제공한다고 생각하면 위험하다. ES는 검색과 분산 색인에 강한 시스템이며, 관계 무결성과 transaction 중심 시스템이 아니다.

## 핵심 차이

| 주제 | RDB | Elasticsearch |
| --- | --- | --- |
| 관계 무결성 | foreign key, constraint | 애플리케이션에서 검증 |
| Transaction | multi-row, multi-table ACID | 단일 document 중심 원자성 |
| Join | 일반적 | 제한적이며 권장 설계가 다름 |
| Schema 변경 | `ALTER TABLE` | field type 변경 제한, reindex 필요 |
| 조회 일관성 | commit 후 즉시 조회 기대 | 검색은 refresh 이후 반영 |
| 삭제 전파 | cascade constraint 가능 | 애플리케이션 delete-by-query/bulk 처리 |

## ES가 적합한 경우와 조심해야 하는 경우

| 판단 | 예시 |
| --- | --- |
| 적합 | 검색, 필터링, 정렬, 집계가 핵심인 데이터 |
| 적합 | document 단위로 조회/수정되는 데이터 |
| 적합 | 약간의 검색 반영 지연을 허용할 수 있는 업무 |
| 조심 | 계좌 이체처럼 강한 transaction이 핵심인 업무 |
| 조심 | 복잡한 join과 FK 제약이 핵심인 정규화 모델 |
| 조심 | 쓰기 직후 모든 조회 경로에서 즉시 일관성이 필요한 업무 |

## Foreign key가 없다

MVP의 관계는 다음과 같다.

{% raw %}
```text
company 1 -- N docs 1 -- N comment
```
{% endraw %}

게시글 생성 전 회사가 존재하는지, 댓글 생성 전 게시글이 존재하는지 Service 계층에서 확인한다.

{% raw %}
```java
public Docs create(String companyId, CreateDocsRequest request) {
    companyService.get(companyId);
    return docsRepository.save(companyId, docs);
}

public Comment create(String companyId, String docsId, CreateCommentRequest request) {
    docsService.get(companyId, docsId);
    return commentRepository.save(companyId, comment);
}
```
{% endraw %}

## Multi-document transaction이 없다

회사 삭제는 company document 삭제, comment 삭제, docs 삭제가 여러 요청으로 나뉜다. 이 중 하나가 실패할 수 있다.

{% raw %}
```text
company delete 성공
comment cleanup 실패
docs cleanup 성공
```
{% endraw %}

운영에서는 outbox 또는 retry queue, 삭제 이력 index, idempotent cleanup, task monitoring, orphan data cleanup scheduler, 알림과 수동 복구 절차가 필요할 수 있다.

## Cascade delete는 애플리케이션 책임

{% raw %}
```text
lock docs:{companyId}:{docsId}
  -> docs 존재 확인
  -> docs 삭제
  -> comment cleanup 비동기 요청
unlock
```
{% endraw %}

댓글 cleanup은 `deleteByQuery`로 처리한다. 이 방식은 이해하기 쉽지만 best-effort다.

## Lock이 필요한 이유

ES에는 RDB row lock이나 FK cascade lock이 없다. 같은 회사나 게시글에 대해 삭제 작업이 동시에 실행되면 중복 cleanup이나 순서 꼬임이 발생할 수 있다. MVP는 `DistributedLockService`를 사용한다.

## Refresh와 eventual consistency

MVP는 일반 단건 write에 `wait_for`를 사용해 read-after-write 경험을 개선한다. 하지만 대량 bulk insert는 `false`를 사용하므로 댓글 bulk 직후 검색 반영이 즉시 보장되지 않을 수 있다.

## Mapping 변경은 migration 문제다

{% raw %}
```text
1. 새 physical index 생성: sc_docs_v2
2. 기존 데이터 reindex: sc_docs_v1 -> sc_docs_v2
3. _tasks로 reindex 진행 상태 확인
4. count, mapping, 샘플 검색 결과 검증
5. _aliases 또는 /api/admin/elasticsearch/aliases/switch로 sc_docs_read/sc_docs_write stable alias 전환
6. 검증 후 old physical index 보존 또는 삭제
```
{% endraw %}

## 설계 원칙

- 데이터 모델을 검색 중심으로 설계한다.

- 관계는 줄이고 중복을 허용한다.

- 실패 복구를 설계에 포함한다.

- Index lifecycle을 운영 기능으로 본다.

- API 계약에 일관성 수준을 명시한다.

## MVP의 현재 한계

| 한계 | 설명 |
| --- | --- |
| 테스트 코드 없음 | 실제 ES 7.9.3 E2E 검증은 후속 과제 |
| outbox/retry 없음 | 비동기 cleanup 실패 복구가 자동화되지 않음 |
| alias switch 운영화 필요 | admin alias switch API는 예시 수준이며, 운영에서는 reindex job, 검증, 쓰기 정책, rollback 절차가 필요 |
| lazy index creation | 운영 동시 생성 race 가능 |
| Redis 기본 비활성 | 다중 instance lock은 운영 설정 필요 |
| cursor request 미노출 | `search_after` 응답은 있지만 다음 페이지 요청 API는 미완 |

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [07. Write, Update, Delete, Bulk](/posts/07-write-update-delete-bulk/)
>
> - 다음: [09. MVP Architecture Walkthrough](/posts/09-mvp-architecture-walkthrough/)

---

## 공식 문서 출처

- [The Elasticsearch data store](https://www.elastic.co/docs/manage-data/data-store)

- [Joining queries](https://www.elastic.co/docs/reference/query-languages/query-dsl/joining-queries)

- [Join field type](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/parent-join)

- [Nested field type](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/nested)

- [SQL limitations](https://www.elastic.co/docs/reference/query-languages/sql/sql-limitations)
