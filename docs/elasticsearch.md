---
title: "Elasticsearch"
nav_order: 9
has_children: true
permalink: "/notes/elasticsearch/"
---

> 🔎 
>
> **RDB 개발자를 위한 Elasticsearch 학습 노트**
>
> 관계형 데이터베이스에 익숙한 개발자가 Elasticsearch를 검색 엔진이자 document store로 이해하고, 실제 Spring 기반 MVP 코드 구조까지 연결해 볼 수 있도록 정리한 교육형 블로그입니다.

## Elasticsearch를 왜 따로 배워야 할까

Elasticsearch는 단순히 "검색이 빠른 데이터베이스"가 아닙니다. 데이터를 JSON document로 저장하고, field mapping을 통해 검색 방식을 설계하며, shard와 replica로 분산 저장하고, refresh 주기에 따라 검색 반영 시점이 달라지는 시스템입니다.

RDB 관점으로만 접근하면 `JOIN`, `Transaction`, `Foreign Key`, `ALTER TABLE` 같은 익숙한 보장을 기대하기 쉽습니다. 하지만 Elasticsearch를 안정적으로 사용하려면 **무엇을 Elasticsearch가 잘하고, 무엇을 애플리케이션과 운영 절차가 책임져야 하는지**를 분리해서 이해해야 합니다.

## 한눈에 보는 학습 흐름

| 단계 | 학습 주제 | 핵심 질문 |
| --- | --- | --- |
| 1 | RDB 관점에서 ES 이해하기 | Table, Row, Column은 ES에서 무엇에 대응될까? |
| 2 | Cluster, Index, Shard, Replica | Index는 왜 shard로 나뉘고 replica는 왜 필요할까? |
| 3 | Document, Mapping, Data Types | `keyword`와 `text`는 왜 구분해야 할까? |
| 4 | Alias와 Lifecycle | 운영에서 physical index를 직접 쓰지 않는 이유는 무엇일까? |
| 5 | Refresh와 검색 일관성 | 저장 직후 검색 결과에 바로 보이지 않을 수 있는 이유는? |
| 6 | Query, Search, Pagination | `term`, `match`, `bool`, `search_after`는 언제 써야 할까? |
| 7 | Write, Update, Delete, Bulk | Bulk 실패와 delete-by-query 부하는 어떻게 다뤄야 할까? |
| 8 | Database처럼 쓸 때의 제약 | ES가 제공하지 않는 RDB식 보장은 무엇일까? |
| 9 | MVP Architecture Walkthrough | 개념이 실제 코드 계층에서 어떻게 구현될까? |
| 10 | 운영 체크리스트와 용어집 | 운영 전 반드시 확인해야 할 항목은 무엇일까? |

## 핵심 요약

### Elasticsearch의 강점

- Full-text search와 filter/search 조합에 강하다.

- JSON document 단위 저장과 조회가 자연스럽다.

- Shard와 replica를 통해 분산 저장과 검색 부하 분산이 가능하다.

- Physical index에는 version을 두고 stable read/write alias로 reindex와 alias switch migration 전략을 세울 수 있다.

### 반드시 조심할 점

- Foreign key와 multi-document transaction을 제공하지 않는다.

- 검색 결과는 refresh 이후에 반영되는 near real-time 모델이다.

- Mapping type 변경은 대개 새 index와 reindex가 필요하다.

- Bulk와 delete-by-query는 item별 실패와 운영 부하를 따로 관리해야 한다.

## 이 시리즈에서 다루는 예제 구조

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

예제 애플리케이션은 Controller나 Service가 Elasticsearch client를 직접 호출하지 않도록 공통 repository와 gateway 계층을 둡니다. 이를 통해 검색 엔진의 세부 API와 도메인 로직을 분리하고, 나중에 client 교체나 운영 정책 변경이 필요할 때 수정 범위를 줄일 수 있습니다.

## 학습 전에 잡고 갈 관점

> Elasticsearch를 데이터베이스처럼 사용할 수는 있지만, RDB처럼 생각하면 위험합니다. 핵심은 검색 중심의 document 설계, 명시적인 mapping 관리, refresh 정책, stable read/write alias 기반 lifecycle, alias switch migration, 그리고 실패 복구 절차입니다.

## 추천 읽기 순서

## 빠른 실습 흐름

1. 회사를 생성해 전역 `company_v1` physical index와 `company_read`/`company_write` stable alias 동작을 확인합니다.

1. 게시글을 생성해 tenant별 docs index lazy creation을 확인합니다.

1. `_cat/indices`와 `_cat/aliases`로 physical index와 read/write alias를 관찰합니다.

1. 단건 저장과 bulk 저장의 refresh policy 차이를 비교합니다.

1. 삭제 API 호출 후 cascade cleanup과 delete-by-query의 특성을 확인합니다.

## 운영으로 확장할 때의 체크포인트

- Shard/replica 수를 기본값에 맡길지, index template으로 명시할지 결정해야 합니다.

- Version은 physical index에만 두고, stable read/write alias를 `_aliases` 또는 admin alias switch API로 전환하는 절차를 설계해야 합니다.

- Bulk item별 실패, delete-by-query task monitoring, retry queue, orphan cleanup을 준비해야 합니다.

- `search_after` 기반 pagination을 REST API 계약으로 노출할지 결정해야 합니다.

- RHLC 7.9.3 사용 환경에서는 장기적으로 Java API Client 전환 가능성도 염두에 둬야 합니다.
