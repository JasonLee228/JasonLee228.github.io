---
title: "03. Document, Mapping, Data Types"
parent: "Elasticsearch"
nav_order: 4
permalink: "/notes/03-document-mapping-data-types/"
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/notes/elasticsearch/)
>
> - 이전: [02. Cluster, Index, Shard, Replica](/notes/02-cluster-index-shard-replica/)
>
> - 다음: [04. Index Alias와 생명주기](/notes/04-index-alias와-생명주기/)

Elasticsearch의 기본 저장 단위는 JSON document다. RDB의 row와 비슷하지만, document는 중첩 구조를 가질 수 있고 field마다 검색 방식이 달라진다.

## Document

{% raw %}
```json
{
  "id": "docs-1",
  "companyId": "acme",
  "title": "Elasticsearch MVP",
  "content": "Elasticsearch를 DB처럼 사용하는 예시",
  "authorUserId": "u1",
  "createdAt": "2026-05-20T01:00:00Z",
  "updatedAt": "2026-05-20T01:00:00Z"
}
```
{% endraw %}

Elasticsearch는 document마다 `_id`를 가진다. MVP에서는 도메인 field `id`와 ES `_id`를 같은 값으로 맞춘다.

{% raw %}
```java
IndexRequest request = new IndexRequest(names.writeAlias())
        .id(document.getId())
        .source(json, XContentType.JSON);
```
{% endraw %}

## Mapping

Mapping은 field 이름과 type을 정의한다. RDB schema와 비슷하지만, 검색 엔진 특성 때문에 "어떻게 분석하고 색인할지"까지 포함한다. MVP의 `docs_v1.json`은 `dynamic: strict`를 사용한다.

{% raw %}
```json
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "id": { "type": "keyword" },
      "companyId": { "type": "keyword" },
      "title": {
        "type": "text",
        "fields": {
          "keyword": { "type": "keyword" }
        }
      },
      "content": { "type": "text" },
      "createdAt": { "type": "date" }
    }
  }
}
```
{% endraw %}

`dynamic: strict`는 mapping에 없는 field가 들어오면 indexing을 실패시켜 schema drift를 줄인다.

## 주요 데이터 타입

| 타입 | 용도 | 예시 |
| --- | --- | --- |
| `keyword` | 정확 일치, 필터, 정렬, 집계 | ID, status, code, enum |
| `text` | full-text search | 제목, 본문, 설명 |
| `date` | 날짜/시간 | 생성일, 수정일 |
| `boolean` | true/false | 활성 여부 |
| `integer`, `long` | 정수 | 카운트, 번호 |
| `object` | 일반 JSON 객체 | 주소, 설정 |
| `nested` | 객체 배열을 독립 document처럼 검색 | 주문 상품 목록 |

## `keyword`와 `text`

`keyword`는 값을 쪼개지 않고 그대로 색인한다. 정확 일치, 필터, 정렬, 집계에 적합하다. `text`는 analyzer를 통해 단어 단위로 분석되며 본문 검색에 적합하다.

## Multi-field

하나의 field를 검색용 `text`와 정렬/집계용 `keyword`로 동시에 쓰고 싶을 때 multi-field를 사용한다.

{% raw %}
```json
{
  "title": {
    "type": "text",
    "fields": {
      "keyword": {
        "type": "keyword"
      }
    }
  }
}
```
{% endraw %}

## `object`와 `nested`

JSON 객체는 기본적으로 `object`로 저장된다. 객체 배열에서 각 객체의 field 관계를 보존해야 한다면 `nested`가 필요하다. MVP는 댓글을 docs document 안에 nested로 넣지 않고 별도 comment index에 저장한다.

## Mapping 변경의 제약

기존 field의 type 변경은 제한적이다. 운영에서는 새 index 생성, reindex, alias 전환, old index 제거 순서로 처리한다.

## MVP의 placeholder mapping

{% raw %}
```json
{
  "settings": {
    "refresh_interval": "@REFRESH_INTERVAL@"
  },
  "aliases": {
    "@ALIAS_READ@": {},
    "@ALIAS_WRITE@": {
      "is_write_index": true
    }
  }
}
```
{% endraw %}

`IndexMappingLoader`가 `@REFRESH_INTERVAL@`, `@ALIAS_READ@`, `@ALIAS_WRITE@`를 실제 값으로 치환한다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/notes/elasticsearch/)
>
> - 이전: [02. Cluster, Index, Shard, Replica](/notes/02-cluster-index-shard-replica/)
>
> - 다음: [04. Index Alias와 생명주기](/notes/04-index-alias와-생명주기/)

---

## 공식 문서 출처

- [Index mapping and text analysis](https://www.elastic.co/docs/manage-data/ingest/transform-enrich/index-mapping-text-analysis)

- [Dynamic field mapping](https://www.elastic.co/docs/manage-data/data-store/mapping/dynamic-field-mapping)

- [Text field type](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/text)

- [Keyword field type](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/keyword)

- [Nested field type](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/nested)
