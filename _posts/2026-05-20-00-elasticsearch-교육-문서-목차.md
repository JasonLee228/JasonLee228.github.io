---
title: "00. Elasticsearch 교육 문서 목차"
date: 2026-05-20 02:58:06 +0000
categories: ["Elasticsearch"]
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/posts/elasticsearch/)
>
> - 다음: [01. RDB 관점에서 Elasticsearch 이해하기](/posts/01-rdb-관점에서-elasticsearch-이해하기/)

> 📚 
>
> **Elasticsearch 교육 시리즈 목차**
>
> RDB 중심으로 개발해 온 사람이 Elasticsearch를 검색 엔진이자 document store로 이해하고, 실제 애플리케이션 구조까지 자연스럽게 따라갈 수 있도록 구성한 학습 로드맵입니다.

## 이 시리즈의 목표

Elasticsearch는 RDB와 비슷해 보이는 용어가 많지만, 실제 동작 방식과 보장 범위는 꽤 다릅니다. 이 시리즈는 단순 사용법 나열보다 **왜 그렇게 설계해야 하는지**를 먼저 설명합니다.

읽고 나면 다음 질문에 답할 수 있어야 합니다.

- RDB의 table, row, column, index는 Elasticsearch에서 무엇에 대응되는가?

- `keyword`와 `text`는 왜 구분해야 하는가?

- 저장 직후 검색 결과에 바로 보이지 않을 수 있는 이유는 무엇인가?

- Physical index version과 stable read/write alias는 왜 분리하는가?

- Elasticsearch를 데이터베이스처럼 쓸 때 애플리케이션이 책임져야 할 것은 무엇인가?

- Bulk, delete-by-query, reindex, shard/replica 같은 운영 포인트는 어디에서 문제가 되는가?

## 읽는 순서

| 순서 | 글 | 핵심 내용 |
| --- | --- | --- |
| 1 | [01. RDB 관점에서 Elasticsearch 이해하기](/posts/01-rdb-관점에서-elasticsearch-이해하기/) | RDB 개념을 기준으로 Elasticsearch의 document, index, mapping, relation 차이를 이해합니다. |
| 2 | [02. Cluster, Index, Shard, Replica](/posts/02-cluster-index-shard-replica/) | 분산 검색 엔진의 기본 단위와 shard/replica가 필요한 이유를 정리합니다. |
| 3 | [03. Document, Mapping, Data Types](/posts/03-document-mapping-data-types/) | JSON document, mapping, `keyword`, `text`, multi-field, nested 구조를 살펴봅니다. |
| 4 | [04. Index Alias와 생명주기](/posts/04-index-alias와-생명주기/) | Physical index에는 version을 두고 stable read/write alias를 유지하는 이유, reindex와 alias switch의 기초를 다룹니다. |
| 5 | [05. Refresh, Near Real-Time, 검색 일관성](/posts/05-refresh-near-real-time-검색-일관성/) | 저장과 검색 반영 사이의 지연, `refresh=false`, `wait_for`, `true`의 차이를 이해합니다. |
| 6 | [06. Query, Search, Pagination](/posts/06-query-search-pagination/) | `term`, `match`, `bool`, `range`, `search_after` 등 검색 API의 선택 기준을 정리합니다. |
| 7 | [07. Write, Update, Delete, Bulk](/posts/07-write-update-delete-bulk/) | 저장, 수정, 삭제, bulk 처리와 item별 실패, delete-by-query 부하를 다룹니다. |
| 8 | [08. Elasticsearch를 Database처럼 쓸 때의 제약](/posts/08-elasticsearch를-database처럼-쓸-때의-제약/) | FK, transaction, cascade, mapping 변경처럼 RDB가 제공하던 보장을 어떻게 보완할지 봅니다. |
| 9 | [09. MVP Architecture Walkthrough](/posts/09-mvp-architecture-walkthrough/) | Controller, Service, Repository, Gateway 계층이 Elasticsearch 개념과 어떻게 연결되는지 따라갑니다. |
| 10 | [10. 운영 체크리스트와 용어집](/posts/10-운영-체크리스트와-용어집/) | 운영 전 확인할 설정, lifecycle, 동시성, client, 용어를 체크리스트로 정리합니다. |

## 빠르게 훑는 핵심 구조

{% raw %}
```text
Controller
  -> Service
    -> Domain Repository
      -> AbstractEsCrudRepository
        -> ElasticsearchClientGateway
          -> RestHighLevelClient 7.9.3
            -> Elasticsearch 7.9.3
```
{% endraw %}

이 구조의 핵심은 Controller나 Service가 Elasticsearch API를 직접 다루지 않도록 하는 것입니다. 검색 엔진 접근은 공통 Repository와 Gateway에 모으고, Service는 관계 검증, 삭제 흐름, 동시성 제어 같은 도메인 책임에 집중합니다.

## 먼저 기억할 세 가지

### 1. ES는 검색 중심 시스템

RDB처럼 정규화된 관계를 조회 시점에 조합하기보다, 검색에 맞는 document와 mapping을 먼저 설계합니다.

### 2. 일관성은 refresh에 묶인다

Write 성공과 search 반영은 같은 의미가 아닙니다. API별로 refresh policy를 명시해야 합니다.

### 3. 운영 절차가 설계의 일부

Mapping 변경, reindex, stable alias switch, bulk 실패 복구, delete-by-query 모니터링은 구현 이후의 부가 작업이 아니라 설계 단계에서 함께 봐야 합니다.

## 추천 학습 방식

1. 먼저 `01`부터 `05`까지 읽어 Elasticsearch의 기본 모델과 일관성 차이를 잡습니다.

1. 그 다음 `06`, `07`에서 실제 검색/쓰기 API의 선택 기준을 익힙니다.

1. `08`에서 RDB처럼 쓸 때의 한계를 정리하고, 어떤 책임을 애플리케이션이 가져가야 하는지 확인합니다.

1. 마지막으로 `09`, `10`을 통해 코드 구조와 운영 체크리스트로 연결합니다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/posts/elasticsearch/)
>
> - 다음: [01. RDB 관점에서 Elasticsearch 이해하기](/posts/01-rdb-관점에서-elasticsearch-이해하기/)

---

## 공식 문서 출처

- [The Elasticsearch data store](https://www.elastic.co/docs/manage-data/data-store)

- [Index mapping and text analysis](https://www.elastic.co/docs/manage-data/ingest/transform-enrich/index-mapping-text-analysis)

- [Run Elasticsearch in production](https://www.elastic.co/docs/deploy-manage/production-guidance/elasticsearch-in-production-environments)
