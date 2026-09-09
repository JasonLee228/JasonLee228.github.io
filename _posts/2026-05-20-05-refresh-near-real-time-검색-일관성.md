---
title: "05. Refresh, Near Real-Time, 검색 일관성"
date: 2026-05-20 02:58:44 +0000
categories: ["Elasticsearch"]
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/posts/elasticsearch/)
>
> - 이전: [04. Index Alias와 생명주기](/posts/04-index-alias와-생명주기/)
>
> - 다음: [06. Query, Search, Pagination](/posts/06-query-search-pagination/)

Elasticsearch는 near real-time 검색 엔진이다. document를 저장했다고 해서 검색 결과에 즉시 보인다고 가정하면 안 된다.

## Refresh란 무엇인가

Elasticsearch는 document를 index한 뒤 내부 segment를 refresh해야 검색에서 볼 수 있다. refresh는 transaction commit과 다르다.

{% raw %}
```text
Index document
  -> write buffer
    -> refresh
      -> searchable segment
        -> search result
```
{% endraw %}

MVP에서는 mapping template에 `refresh_interval` 설정을 넣는다.

{% raw %}
```yaml
app:
  elasticsearch:
    refresh-interval: 1000
    default-refresh-policy: wait_for
```
{% endraw %}

## Refresh API

{% raw %}
```javascript
POST /acme_docs_read/_refresh
```
{% endraw %}

Refresh는 비용이 있는 작업이므로 쓰기 요청마다 강제 refresh를 남발하면 indexing throughput이 떨어질 수 있다.

## Write API의 refresh parameter

| 값 | 의미 | 특징 |
| --- | --- | --- |
| `false` | refresh를 기다리지 않음 | 쓰기 성능 우선, 검색 반영은 나중 |
| `wait_for` | 다음 refresh가 일어날 때까지 대기 | read-after-write 경험 개선, 강제 refresh보다 부담이 작음 |
| `true` | 요청 후 즉시 refresh | 검색 즉시 반영, 비용 큼 |

## MVP의 refresh 정책

| 작업 | 정책 | 이유 |
| --- | --- | --- |
| 단건 save | 기본 `wait_for` | 저장 직후 조회/검색 경험 보장 |
| partial update | 기본 `wait_for` | 수정 후 다시 읽어 응답 생성 |
| delete by id | 기본 `wait_for` | 삭제 직후 목록에서 사라지는 경험 |
| 댓글 bulk insert | `false` 고정 | 대량 입력 성능 우선 |
| delete by query | `refresh=true` | cascade cleanup 이후 검색 반영성 확보 |

## 단건 저장 코드

{% raw %}
```java
IndexRequest request = new IndexRequest(names.writeAlias())
        .id(document.getId())
        .source(json, XContentType.JSON)
        .setRefreshPolicy(properties.defaultRefreshPolicy());
```
{% endraw %}

## 댓글 bulk 저장

{% raw %}
```java
private static final String BULK_INSERT_REFRESH_POLICY = "false";

return commentRepository.saveAll(companyId, comments, BULK_INSERT_REFRESH_POLICY);
```
{% endraw %}

## RDB와의 차이

| 조회 방식 | 반영성 |
| --- | --- |
| `_id` 기반 get | 저장 성공 직후 상대적으로 즉시 확인 가능 |
| search query | refresh 이후 검색 가능 |

## 주의할 운영 포인트

- `refresh_interval`을 너무 짧게 잡지 않는다.

- Bulk 작업은 별도 정책을 둔다.

- 검색 일관성을 API 계약으로 명확히 한다.

## 실습 API

{% raw %}
```bash
curl -X POST "http://localhost:9200/acme_docs_write/_doc/docs-2?refresh=false" \
  -H "Content-Type: application/json" \
  -d '{"id":"docs-2","companyId":"acme","title":"NRT","content":"refresh false","authorUserId":"u1","createdAt":"2026-05-20T01:00:00Z","updatedAt":"2026-05-20T01:00:00Z"}'

curl -X POST "http://localhost:9200/acme_docs_read/_refresh"
curl -X GET "http://localhost:9200/acme_docs_read/_search?pretty"
```
{% endraw %}

Refresh는 ES를 데이터베이스처럼 사용할 때 반드시 이해해야 하는 핵심 개념이다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/posts/elasticsearch/)
>
> - 이전: [04. Index Alias와 생명주기](/posts/04-index-alias와-생명주기/)
>
> - 다음: [06. Query, Search, Pagination](/posts/06-query-search-pagination/)

---

## 공식 문서 출처

- [Refresh an index API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-refresh)

- [Update index settings API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-put-settings)

- [Tune for indexing speed](https://www.elastic.co/docs/deploy-manage/production-guidance/optimize-performance/indexing-speed)
