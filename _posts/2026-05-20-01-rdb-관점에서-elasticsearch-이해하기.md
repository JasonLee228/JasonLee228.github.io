---
title: "01. RDB 관점에서 Elasticsearch 이해하기"
date: 2026-05-20 02:58:06 +0000
categories: ["Elasticsearch", "기초"]
tags: ["기초", "elasticsearch"]
permalink: /posts/01-rdb-관점에서-elasticsearch-이해하기/
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [00. Elasticsearch 교육 문서 목차](/posts/00-elasticsearch-교육-문서-목차/)
>
> - 다음: [02. Cluster, Index, Shard, Replica](/posts/02-cluster-index-shard-replica/)

RDB를 먼저 배운 개발자는 Elasticsearch를 "테이블이 다른 데이터베이스"처럼 이해하기 쉽다. 하지만 Elasticsearch는 관계형 데이터베이스가 아니라 검색 엔진 기반의 분산 document store다.

## RDB와 Elasticsearch 비교

| RDB 개념 | Elasticsearch 개념 | 중요한 차이 |
| --- | --- | --- |
| Database | Cluster 또는 논리적 index 집합 | ES cluster는 여러 node와 shard를 포함하는 분산 시스템이다. |
| Table | Index | ES index는 물리적으로 shard로 나뉘고 검색을 위해 역색인을 만든다. |
| Row | Document | document는 JSON이며 nested/object 구조를 가질 수 있다. |
| Column | Field | field마다 mapping type이 있고 검색/정렬/집계 가능 여부가 달라진다. |
| Schema | Mapping | 타입 변경은 보통 새 index와 reindex가 필요하다. |
| Primary Key | `_id` | `_id`는 unique하지만 관계 제약을 만들지는 않는다. |
| Foreign Key | 없음 | 관계 검증은 애플리케이션에서 처리해야 한다. |
| Transaction | 단일 document 중심 원자성 | 여러 document/index에 걸친 ACID transaction은 제공하지 않는다. |

Elasticsearch 7.9.3에서는 예전 버전의 `mapping type`을 RDB table처럼 사용하는 모델을 더 이상 설계 기준으로 삼지 않는다. 실무에서는 "하나의 index가 하나의 document 종류를 담는다"는 방향으로 이해하는 편이 안전하다.

## Elasticsearch를 DB처럼 쓴다는 말의 의미

`es-rhlc-mvp`에서 "ES를 데이터베이스처럼 사용한다"는 말은 RDB의 모든 기능을 ES로 대체한다는 뜻이 아니다. 다음을 애플리케이션 설계로 보완하면서 ES를 주 저장소처럼 사용한다는 뜻이다.

- mapping을 schema처럼 엄격하게 관리한다.

- document ID를 애플리케이션에서 생성해 저장한다.

- read/write alias를 통해 index 교체 가능성을 확보한다.

- relation과 cascade delete는 Service 계층에서 처리한다.

- refresh policy를 명시해 쓰기 직후 검색 반영성을 제어한다.

## MVP 도메인을 RDB로 보면

{% raw %}
```sql
CREATE TABLE company (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE docs (
  id VARCHAR(64) PRIMARY KEY,
  company_id VARCHAR(64) NOT NULL REFERENCES company(id),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  author_user_id VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE comment (
  id VARCHAR(64) PRIMARY KEY,
  company_id VARCHAR(64) NOT NULL REFERENCES company(id),
  docs_id VARCHAR(64) NOT NULL REFERENCES docs(id),
  content TEXT NOT NULL,
  author_user_id VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```
{% endraw %}

## Elasticsearch 저장 위치

| 도메인 | ES 저장 위치 | 관계 처리 |
| --- | --- | --- |
| company | 전역 `company_v1` index | root tenant document |
| docs | 회사별 `{companyId}_docs_v1` index | `companyId` field 저장, 회사 존재 검증은 Service |
| comment | 회사별 `{companyId}_comment_v1` index | `companyId`, `docsId` field 저장, 게시글 존재 검증은 Service |

## RDB 사고방식에서 조심할 점

- JOIN보다 document 설계를 먼저 생각한다.

- Transaction을 기대하지 않는다.

- 검색 반영은 refresh에 묶인다.

- Mapping 변경은 신중해야 한다.

## MVP 코드에서 관계를 처리하는 위치

{% raw %}
```java
public Docs create(String companyId, CreateDocsRequest request) {
    companyService.get(companyId);
    Docs docs = Docs.builder()
            .companyId(companyId)
            .title(request.title())
            .content(request.content())
            .authorUserId(request.authorUserId())
            .build();
    return docsRepository.save(companyId, docs);
}
```
{% endraw %}

이 코드는 RDB의 foreign key를 ES가 대신 검사하지 않기 때문에 필요하다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [00. Elasticsearch 교육 문서 목차](/posts/00-elasticsearch-교육-문서-목차/)
>
> - 다음: [02. Cluster, Index, Shard, Replica](/posts/02-cluster-index-shard-replica/)

---

## 공식 문서 출처

- [The Elasticsearch data store](https://www.elastic.co/docs/manage-data/data-store)

- [Index mapping and text analysis](https://www.elastic.co/docs/manage-data/ingest/transform-enrich/index-mapping-text-analysis)

- [Joining queries](https://www.elastic.co/docs/reference/query-languages/query-dsl/joining-queries)

- [SQL limitations](https://www.elastic.co/docs/reference/query-languages/sql/sql-limitations)
