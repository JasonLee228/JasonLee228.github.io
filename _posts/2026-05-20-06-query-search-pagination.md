---
title: "06. Query, Search, Pagination"
date: 2026-05-20 02:59:25 +0000
categories: ["Elasticsearch", "기초"]
tags: ["기초", "elasticsearch"]
permalink: /posts/06-query-search-pagination/
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [05. Refresh, Near Real-Time, 검색 일관성](/posts/05-refresh-near-real-time-검색-일관성/)
>
> - 다음: [07. Write, Update, Delete, Bulk](/posts/07-write-update-delete-bulk/)

Elasticsearch의 강점은 검색이다. RDB의 `WHERE`, `ORDER BY`, `LIMIT/OFFSET`에 대응되는 기능이 있지만, 내부 동작과 비용 모델이 다르다.

## Search API 기본 구조

{% raw %}
```javascript
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "match_all": {}
  },
  "size": 10
}
```
{% endraw %}

MVP에서는 read alias를 통해 검색한다.

{% raw %}
```java
var response = clientGateway.search(
        new SearchRequest(names.readAlias()).source(sourceBuilder));
```
{% endraw %}

## Term query와 Match query

`term` query는 정확히 같은 값을 찾는다. `keyword` field에 적합하다.

{% raw %}
```javascript
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "term": {
      "companyId": "acme"
    }
  }
}
```
{% endraw %}

`match` query는 analyzer가 적용된 full-text 검색에 적합하다.

| Query | 주로 쓰는 field | 용도 |
| --- | --- | --- |
| `term` | `keyword`, numeric, date, boolean | 정확히 같은 값 하나 |
| `terms` | `keyword`, numeric, date, boolean | 여러 값 중 하나 |
| `match` | `text` | 분석기를 거친 본문 검색 |
| `match_phrase` | `text` | 단어 순서가 중요한 구문 검색 |

## Bool query와 filter

여러 조건을 조합하려면 `bool` query를 사용한다. `filter`는 score 계산이 필요 없는 조건에 적합하다.

{% raw %}
```java
QueryBuilders.boolQuery()
        .filter(QueryBuilders.termQuery("companyId", companyId))
        .filter(QueryBuilders.termQuery("docsId", docsId));
```
{% endraw %}

| Clause | 의미 | RDB식 비유 | Score 영향 |
| --- | --- | --- | --- |
| `must` | 반드시 만족해야 함 | `AND` | 있음 |
| `filter` | 반드시 만족하되 score 계산 불필요 | `AND` 조건 필터 | 없음 |
| `should` | 만족하면 더 좋은 조건 | 선택 조건, OR 성격 | 있음 |
| `must_not` | 만족하면 제외 | `NOT` | 없음 |

## Range, Exists, Wildcard, Prefix

- `range`: 숫자나 날짜 범위 조건에 사용한다.

- `exists`: 특정 field 존재 여부를 확인한다.

- `wildcard`: `*`, `?` 패턴 검색에 사용하지만 비용이 클 수 있다.

- `prefix`: 지정한 접두사로 시작하는 값을 찾는다.

Wildcard는 편리하지만 운영 index에서 느릴 수 있다. 본문 검색은 `text` + `match`, 접두어 자동완성은 `prefix`, `match_phrase_prefix`, `completion` suggester, 복잡한 부분 문자열 검색은 ngram analyzer를 먼저 검토한다.

## Query string 계열

`query_string`은 Lucene query syntax를 문자열로 받아 검색한다. 강력하지만 사용자 입력을 그대로 넣으면 syntax error나 의도하지 않은 검색이 발생할 수 있다. 검색창 입력을 직접 받을 때는 더 안전한 `simple_query_string`을 검토한다.

## Sort

검색 결과 순서를 안정적으로 만들려면 sort를 명시해야 한다.

{% raw %}
```java
List.of(
    SortBuilders.fieldSort("createdAt").order(SortOrder.ASC),
    SortBuilders.fieldSort("id").order(SortOrder.ASC)
)
```
{% endraw %}

MVP는 `createdAt` 뒤에 `id`를 tie-breaker로 둔다.

## `track_total_hits`

정확한 total count가 필요하면 `track_total_hits`를 켠다. MVP의 공통 search는 `trackTotalHits(true)`를 사용한다.

## `from/size` pagination의 한계

ES에서 깊은 페이지를 `from/size`로 조회하면 앞 페이지 결과까지 shard별로 모아 정렬해야 해서 비용이 커진다. 기본적으로 `index.max_result_window` 제한도 있다.

## `search_after`

깊은 pagination에는 `search_after`가 더 적합하다. 이전 페이지의 마지막 hit가 가진 sort 값을 다음 요청에 전달한다.

{% raw %}
```json
{
  "search_after": ["2026-05-20T01:00:00.000Z", "docs-20"]
}
```
{% endraw %}

## MVP의 `SearchPage`

{% raw %}
```java
if (hits.length > 0) {
    nextSearchAfter = new ArrayList<>(
            Arrays.asList(hits[hits.length - 1].getSortValues()));
}
return new SearchPage<>(content, total, nextSearchAfter);
```
{% endraw %}

현재 MVP API는 다음 페이지 cursor를 request parameter로 다시 받지는 않는다. Repository 계층은 준비되어 있지만 공개 REST API는 첫 페이지 중심이다.

## 쿼리 타입별 상세 실전 예시

아래 예시는 `company`, `docs`, `comment` 도메인과 stable alias(`company_read`, `acme_docs_read`, `acme_comment_read`)를 기준으로 한다. 핵심은 문법보다 **어떤 조건을 어떤 query로 표현하는가**다.

### 1. `term` query: 정확히 하나의 값과 일치

`term`은 분석기를 거치지 않은 정확 일치 조건이다. `companyId`, `id`, `docsId`, `authorUserId`, `status`처럼 `keyword`로 매핑된 field에 적합하다.

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "term": {
      "companyId": "acme"
    }
  }
}
```
{% endraw %}

이 query는 `companyId`가 정확히 `acme`인 게시글만 찾는다. `text` field에 `term`을 쓰면 사용자가 기대한 본문 검색이 되지 않을 수 있다.

{% raw %}
```java
QueryBuilder query = QueryBuilders.termQuery("companyId", companyId);
```
{% endraw %}

### 2. `terms` query: 여러 후보 중 하나와 일치

`terms`는 RDB의 `IN (...)` 조건과 비슷하다.

{% raw %}
```text
GET /company_read/_search
Content-Type: application/json

{
  "query": {
    "terms": {
      "status": ["ACTIVE", "PENDING"]
    }
  }
}
```
{% endraw %}

이 query는 회사 상태가 `ACTIVE` 또는 `PENDING`인 document를 찾는다.

{% raw %}
```java
QueryBuilder query = QueryBuilders.termsQuery("status", List.of("ACTIVE", "PENDING"));
```
{% endraw %}

### 3. `match` query: 분석기를 거친 본문 검색

`match`는 `text` field에서 사용자가 입력한 문장을 analyzer로 분석해 검색한다.

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "match": {
      "content": "Elasticsearch database migration"
    }
  }
}
```
{% endraw %}

이 query는 `content`에서 `Elasticsearch`, `database`, `migration`과 관련된 게시글을 찾는다. 단어가 반드시 붙어 있거나 순서가 같을 필요는 없다.

{% raw %}
```java
QueryBuilder query = QueryBuilders.matchQuery("content", keyword);
```
{% endraw %}

### 4. `match_phrase` query: 단어 순서가 중요한 구문 검색

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "match_phrase": {
      "content": "alias switch"
    }
  }
}
```
{% endraw %}

이 query는 `content` 안에 `alias switch`라는 구문이 순서대로 나타나는 게시글을 찾는다. 일반 `match`보다 더 엄격하다.

{% raw %}
```java
QueryBuilder query = QueryBuilders.matchPhraseQuery("content", "alias switch");
```
{% endraw %}

### 5. `bool` query: 여러 조건 조합

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "term": { "status": "ACTIVE" } }
      ],
      "must": [
        { "match": { "content": "Elasticsearch migration" } }
      ],
      "should": [
        { "match": { "title": "alias" } },
        { "match_phrase": { "content": "alias switch" } }
      ],
      "minimum_should_match": 1,
      "must_not": [
        { "term": { "authorUserId": "blocked-user" } }
      ]
    }
  }
}
```
{% endraw %}

이 query는 `companyId = acme`, `status = ACTIVE`인 게시글 중 본문에 `Elasticsearch migration` 관련 내용이 있고, 제목에 `alias`가 있거나 본문에 `alias switch` 구문이 있는 문서를 찾는다. `blocked-user` 작성자의 문서는 제외한다.

{% raw %}
```java
BoolQueryBuilder query = QueryBuilders.boolQuery()
        .filter(QueryBuilders.termQuery("companyId", companyId))
        .filter(QueryBuilders.termQuery("status", "ACTIVE"))
        .must(QueryBuilders.matchQuery("content", "Elasticsearch migration"))
        .should(QueryBuilders.matchQuery("title", "alias"))
        .should(QueryBuilders.matchPhraseQuery("content", "alias switch"))
        .minimumShouldMatch(1)
        .mustNot(QueryBuilders.termQuery("authorUserId", "blocked-user"));
```
{% endraw %}

### 6. 댓글 목록 조회용 `bool.filter`

{% raw %}
```text
GET /acme_comment_read/_search
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "term": { "docsId": "docs-1" } }
      ]
    }
  },
  "sort": [
    { "createdAt": "asc" },
    { "id": "asc" }
  ],
  "size": 50
}
```
{% endraw %}

이 query는 `acme` 회사의 `docs-1` 게시글에 달린 댓글만 생성일/ID 순서로 조회한다. 랭킹이 필요 없는 목록 조회이므로 `filter`만으로 충분하다.

### 7. `range` query: 날짜/숫자 범위

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        {
          "range": {
            "createdAt": {
              "gte": "2026-05-01T00:00:00Z",
              "lt": "2026-06-01T00:00:00Z"
            }
          }
        }
      ]
    }
  }
}
```
{% endraw %}

이 query는 `acme` 회사의 게시글 중 2026년 5월에 생성된 문서만 찾는다.

### 8. `exists` query: 필드 존재 여부

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "exists": { "field": "updatedAt" } }
      ]
    }
  }
}
```
{% endraw %}

이 query는 `updatedAt` field가 존재하는 게시글만 찾는다. 반대로 누락 데이터를 찾을 때는 `must_not`과 조합한다.

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } }
      ],
      "must_not": [
        { "exists": { "field": "updatedAt" } }
      ]
    }
  }
}
```
{% endraw %}

### 9. `wildcard`와 `prefix`

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "wildcard": {
      "title.keyword": {
        "value": "*elastic*",
        "case_insensitive": true
      }
    }
  }
}
```
{% endraw %}

이 query는 제목 전체 문자열에 `elastic`이 포함된 문서를 찾는다. 앞쪽 wildcard가 있는 `*elastic*`는 비용이 클 수 있으므로 기본 검색 전략으로 남발하지 않는다.

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "prefix": {
      "title.keyword": {
        "value": "Elastic"
      }
    }
  }
}
```
{% endraw %}

이 query는 제목이 `Elastic`으로 시작하는 문서를 찾는다.

### 10. `query_string`과 `simple_query_string`

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "query_string": {
      "query": "title:(Elasticsearch OR Search) AND authorUserId:u1"
    }
  }
}
```
{% endraw %}

이 query는 제목에 `Elasticsearch` 또는 `Search`가 있고 작성자가 `u1`인 문서를 찾는다. 사용자 입력을 그대로 넣으면 syntax error가 날 수 있으므로 주의한다.

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "query": {
    "simple_query_string": {
      "query": "Elasticsearch \"alias switch\" -deprecated",
      "fields": ["title^2", "content"],
      "default_operator": "and"
    }
  }
}
```
{% endraw %}

이 query는 `title`과 `content`를 검색하되 제목 매칭에 더 높은 가중치를 준다.

### 11. 여러 query를 섞은 운영형 검색 예시

{% raw %}
```text
GET /acme_docs_read/_search
Content-Type: application/json

{
  "track_total_hits": true,
  "size": 20,
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "term": { "status": "ACTIVE" } },
        {
          "range": {
            "createdAt": {
              "gte": "2026-05-01T00:00:00Z",
              "lt": "2026-06-01T00:00:00Z"
            }
          }
        }
      ],
      "must": [
        {
          "multi_match": {
            "query": "alias switch migration",
            "fields": ["title^2", "content"]
          }
        }
      ],
      "should": [
        { "match_phrase": { "content": "zero downtime" } },
        { "prefix": { "title.keyword": { "value": "Elastic" } } }
      ],
      "minimum_should_match": 0,
      "must_not": [
        { "term": { "authorUserId": "blocked-user" } }
      ]
    }
  },
  "sort": [
    { "createdAt": "desc" },
    { "id": "asc" }
  ]
}
```
{% endraw %}

이 query는 `acme` tenant의 활성 게시글 중 2026년 5월에 생성된 문서를 대상으로 제목/본문에서 `alias switch migration`을 검색한다. 제목 매칭을 더 중요하게 보고, `zero downtime` 구문이나 `Elastic` 접두 제목은 score에 유리하게 반영한다. 차단 작성자는 제외하고 최신순으로 정렬한다.

{% raw %}
```java
BoolQueryBuilder query = QueryBuilders.boolQuery()
        .filter(QueryBuilders.termQuery("companyId", companyId))
        .filter(QueryBuilders.termQuery("status", "ACTIVE"))
        .filter(QueryBuilders.rangeQuery("createdAt")
                .gte("2026-05-01T00:00:00Z")
                .lt("2026-06-01T00:00:00Z"))
        .must(QueryBuilders.multiMatchQuery("alias switch migration", "title", "content")
                .field("title", 2.0f)
                .field("content"))
        .should(QueryBuilders.matchPhraseQuery("content", "zero downtime"))
        .should(QueryBuilders.prefixQuery("title.keyword", "Elastic"))
        .mustNot(QueryBuilders.termQuery("authorUserId", "blocked-user"));
```
{% endraw %}

## Query 설계 체크리스트

- ID, 상태, tenantId는 `keyword` + `term/filter`로 조회한다.

- 본문 검색은 `text` + `match`를 사용한다.

- 날짜/숫자 구간은 `range`를 사용한다.

- field 존재 여부는 `exists`를 사용한다.

- wildcard는 사용자 검색의 기본 전략으로 남발하지 않는다.

- pagination 결과가 흔들리지 않도록 sort에 tie-breaker를 넣는다.

- deep pagination에는 `from/size`보다 `search_after`를 우선 검토한다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [05. Refresh, Near Real-Time, 검색 일관성](/posts/05-refresh-near-real-time-검색-일관성/)
>
> - 다음: [07. Write, Update, Delete, Bulk](/posts/07-write-update-delete-bulk/)

---

## 공식 문서 출처

- [Run a search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search)

- [Get started with Query DSL search and filters](https://www.elastic.co/docs/reference/query-languages/query-dsl/full-text-filter-tutorial)

- [Match phrase prefix query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-match-query-phrase-prefix)

- [Match boolean prefix query](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-match-bool-prefix-query)
