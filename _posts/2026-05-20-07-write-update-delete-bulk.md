---
title: "07. Write, Update, Delete, Bulk"
date: 2026-05-20 02:59:25 +0000
categories: ["Elasticsearch", "기초"]
tags: ["기초", "elasticsearch"]
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [06. Query, Search, Pagination](/posts/06-query-search-pagination/)
>
> - 다음: [08. Elasticsearch를 Database처럼 쓸 때의 제약](/posts/08-elasticsearch를-database처럼-쓸-때의-제약/)

Elasticsearch write API는 RDB의 `INSERT`, `UPDATE`, `DELETE`와 비슷해 보이지만, refresh, version conflict, bulk 실패 처리, delete-by-query 부하 같은 ES 고유의 고려사항이 있다.

## Index API

Document 저장은 Index API로 수행한다.

{% raw %}
```javascript
PUT /acme_docs_write/_doc/docs-1?refresh=wait_for
Content-Type: application/json

{
  "id": "docs-1",
  "companyId": "acme",
  "title": "Hello ES",
  "content": "Index API example",
  "authorUserId": "u1"
}
```
{% endraw %}

MVP의 RHLC 코드는 write alias로 저장한다.

{% raw %}
```java
String json = objectMapper.writeValueAsString(document);
IndexRequest request = new IndexRequest(names.writeAlias())
        .id(document.getId())
        .source(json, XContentType.JSON)
        .setRefreshPolicy(properties.defaultRefreshPolicy());
clientGateway.index(request);
```
{% endraw %}

## Update API

일부 field만 수정하려면 Update API를 사용한다. MVP는 partial update에 `retryOnConflict(5)`를 적용한다.

{% raw %}
```java
UpdateRequest request = new UpdateRequest(names.writeAlias(), id)
        .doc(fields, XContentType.JSON)
        .retryOnConflict(5)
        .setRefreshPolicy(properties.defaultRefreshPolicy());
clientGateway.update(request);
return findById(companyId, id);
```
{% endraw %}

## Delete API

단건 삭제는 Delete API로 수행한다. MVP에서는 tenant index가 없으면 no-op으로 처리한다.

{% raw %}
```java
if (!clientGateway.indexExists(names.writeAlias())) {
    return;
}
DeleteRequest request = new DeleteRequest(names.writeAlias(), id)
        .setRefreshPolicy(properties.defaultRefreshPolicy());
clientGateway.delete(request);
```
{% endraw %}

## Bulk API

여러 document를 한 번에 저장하거나 삭제하려면 Bulk API를 사용한다.

{% raw %}
```javascript
POST /_bulk?refresh=false
Content-Type: application/x-ndjson

{ "index": { "_index": "acme_comment_write", "_id": "c1" } }
{ "id": "c1", "companyId": "acme", "docsId": "docs-1", "content": "first" }
{ "index": { "_index": "acme_comment_write", "_id": "c2" } }
{ "id": "c2", "companyId": "acme", "docsId": "docs-1", "content": "second" }
```
{% endraw %}

MVP의 bulk 저장은 `BulkRequest`를 사용한다. Bulk response가 전체 HTTP 성공이어도 item별 실패를 포함할 수 있으므로 운영에서는 실패 item 재시도와 실패 이력 저장이 필요하다.

## Delete By Query API

조건에 맞는 여러 document를 삭제하려면 Delete By Query API를 사용한다.

{% raw %}
```javascript
POST /acme_comment_write/_delete_by_query?refresh=true&conflicts=proceed
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "term": { "docsId": "docs-1" } }
      ]
    }
  }
}
```
{% endraw %}

`conflicts=proceed`는 version conflict가 있어도 전체 작업을 계속 진행한다.

## 회사 삭제와 게시글 삭제 흐름

회사 삭제:

{% raw %}
```text
lock company:{companyId}
  -> company 존재 확인
  -> company 삭제
  -> 비동기 child cleanup 요청
unlock

async cleanup
  -> comment delete-by-query
  -> docs delete-by-query
```
{% endraw %}

게시글 삭제:

{% raw %}
```text
lock docs:{companyId}:{docsId}
  -> docs 존재 확인
  -> docs 삭제
  -> 비동기 comment cleanup 요청
unlock
```
{% endraw %}

## REST API 예시

{% raw %}
```bash
curl -X POST "http://localhost:8080/api/companies/{companyId}/docs" \
  -H "Content-Type: application/json" \
  -d '{"title":"Write API","content":"index request","authorUserId":"u1"}'

curl -X POST "http://localhost:8080/api/companies/{companyId}/docs/{docsId}/comments/bulk" \
  -H "Content-Type: application/json" \
  -d '{"comments":[{"content":"c1","authorUserId":"u1"},{"content":"c2","authorUserId":"u2"}]}'
```
{% endraw %}

## API와 Java 코드 매칭 상세 예시

이 절은 Elasticsearch REST API가 어떤 의미를 가지며, MVP의 RHLC 코드와 어떻게 대응되는지 보여준다. 예시는 stable write alias(`company_write`, `acme_docs_write`, `acme_comment_write`)를 기준으로 한다.

### 1. Index API: 문서 생성 또는 전체 교체

{% raw %}
```text
PUT /acme_docs_write/_doc/docs-1?refresh=wait_for
Content-Type: application/json

{
  "id": "docs-1",
  "companyId": "acme",
  "title": "Alias switch migration",
  "content": "Stable alias를 신규 physical index로 전환하는 절차",
  "authorUserId": "u1",
  "createdAt": "2026-05-20T01:00:00Z",
  "updatedAt": "2026-05-20T01:00:00Z"
}
```
{% endraw %}

이 API는 `acme_docs_write` alias가 가리키는 physical index에 `_id = docs-1` 문서를 저장한다. 같은 `_id` 문서가 이미 있으면 기존 문서를 새 source로 교체한다. `refresh=wait_for`는 다음 refresh까지 기다려 저장 직후 검색 반영 경험을 개선한다.

{% raw %}
```java
String json = objectMapper.writeValueAsString(docs);

IndexRequest request = new IndexRequest(names.writeAlias())
        .id(docs.getId())
        .source(json, XContentType.JSON)
        .setRefreshPolicy(properties.defaultRefreshPolicy());

IndexResponse response = clientGateway.index(request);
```
{% endraw %}

### 2. Create only: `op_type=create`

{% raw %}
```text
PUT /acme_docs_write/_doc/docs-1?op_type=create&refresh=wait_for
Content-Type: application/json

{
  "id": "docs-1",
  "companyId": "acme",
  "title": "Create only",
  "content": "이미 같은 ID가 있으면 409 conflict",
  "authorUserId": "u1",
  "createdAt": "2026-05-20T01:00:00Z",
  "updatedAt": "2026-05-20T01:00:00Z"
}
```
{% endraw %}

이 API는 `docs-1`이 이미 있으면 version conflict로 실패한다. 중복 생성을 실패로 처리하고 싶을 때 사용한다.

{% raw %}
```java
IndexRequest request = new IndexRequest(names.writeAlias())
        .id(docs.getId())
        .opType(DocWriteRequest.OpType.CREATE)
        .source(json, XContentType.JSON)
        .setRefreshPolicy(WriteRequest.RefreshPolicy.WAIT_UNTIL);
```
{% endraw %}

### 3. Update API: 일부 field만 수정

{% raw %}
```text
POST /acme_docs_write/_update/docs-1?refresh=wait_for&retry_on_conflict=5
Content-Type: application/json

{
  "doc": {
    "title": "Updated alias switch migration",
    "updatedAt": "2026-05-20T02:00:00Z"
  }
}
```
{% endraw %}

이 API는 `_id = docs-1` 문서의 `title`, `updatedAt`만 부분 수정한다. `_source` 전체를 다시 보내는 Index API와 달리 변경 field만 전달한다.

{% raw %}
```java
Map<String, Object> fields = new HashMap<>();
fields.put("title", "Updated alias switch migration");
fields.put("updatedAt", Instant.parse("2026-05-20T02:00:00Z"));

UpdateRequest request = new UpdateRequest(names.writeAlias(), "docs-1")
        .doc(fields, XContentType.JSON)
        .retryOnConflict(5)
        .setRefreshPolicy(properties.defaultRefreshPolicy());

clientGateway.update(request);
Docs updated = findById(companyId, "docs-1");
```
{% endraw %}

### 4. Scripted update: 기존 값을 기반으로 수정

{% raw %}
```text
POST /acme_docs_write/_update/docs-1?refresh=wait_for
Content-Type: application/json

{
  "script": {
    "source": "ctx._source.viewCount = (ctx._source.viewCount == null ? 0 : ctx._source.viewCount) + params.count; ctx._source.updatedAt = params.updatedAt",
    "params": {
      "count": 1,
      "updatedAt": "2026-05-20T02:00:00Z"
    }
  }
}
```
{% endraw %}

이 API는 기존 `viewCount`를 1 증가시킨다. MVP 기본 mapping에 없는 field라면 `dynamic: strict` 때문에 실패할 수 있으므로 mapping 정의가 선행되어야 한다.

{% raw %}
```java
Script script = new Script(
        ScriptType.INLINE,
        "painless",
        "ctx._source.viewCount = (ctx._source.viewCount == null ? 0 : ctx._source.viewCount) + params.count; ctx._source.updatedAt = params.updatedAt",
        Map.of("count", 1, "updatedAt", "2026-05-20T02:00:00Z"));

UpdateRequest request = new UpdateRequest(names.writeAlias(), "docs-1")
        .script(script)
        .retryOnConflict(5)
        .setRefreshPolicy(WriteRequest.RefreshPolicy.WAIT_UNTIL);
```
{% endraw %}

### 5. Delete API: ID 기반 단건 삭제

{% raw %}
```text
DELETE /acme_docs_write/_doc/docs-1?refresh=wait_for
```
{% endraw %}

이 API는 `acme_docs_write` alias가 가리키는 physical index에서 `_id = docs-1` 문서를 삭제한다. 게시글 삭제처럼 특정 문서를 정확히 알고 있을 때 사용한다.

{% raw %}
```java
DeleteRequest request = new DeleteRequest(names.writeAlias(), "docs-1")
        .setRefreshPolicy(properties.defaultRefreshPolicy());

clientGateway.delete(request);
```
{% endraw %}

### 6. Bulk API: 여러 문서 저장

{% raw %}
```text
POST /_bulk?refresh=false
Content-Type: application/x-ndjson

{ "index": { "_index": "acme_comment_write", "_id": "c1" } }
{ "id": "c1", "companyId": "acme", "docsId": "docs-1", "content": "first", "authorUserId": "u1", "createdAt": "2026-05-20T01:00:00Z", "updatedAt": "2026-05-20T01:00:00Z" }
{ "index": { "_index": "acme_comment_write", "_id": "c2" } }
{ "id": "c2", "companyId": "acme", "docsId": "docs-1", "content": "second", "authorUserId": "u2", "createdAt": "2026-05-20T01:00:00Z", "updatedAt": "2026-05-20T01:00:00Z" }
```
{% endraw %}

이 API는 `docs-1` 게시글에 댓글 `c1`, `c2`를 한 요청으로 저장한다. `refresh=false`는 대량 입력 성능을 우선한다는 뜻이므로 요청 직후 검색 결과에 바로 보이지 않을 수 있다.

{% raw %}
```java
BulkRequest bulkRequest = new BulkRequest();
bulkRequest.setRefreshPolicy(WriteRequest.RefreshPolicy.NONE);

for (Comment comment : comments) {
    String json = objectMapper.writeValueAsString(comment);
    bulkRequest.add(new IndexRequest(names.writeAlias())
            .id(comment.getId())
            .source(json, XContentType.JSON));
}

BulkResponse response = clientGateway.bulk(bulkRequest);
if (response.hasFailures()) {
    log.warn("Bulk comment save had failures: {}", response.buildFailureMessage());
}
```
{% endraw %}

### 7. Bulk API: 저장과 삭제를 섞는 예시

{% raw %}
```text
POST /_bulk?refresh=wait_for
Content-Type: application/x-ndjson

{ "index": { "_index": "acme_comment_write", "_id": "c3" } }
{ "id": "c3", "companyId": "acme", "docsId": "docs-1", "content": "new comment", "authorUserId": "u3", "createdAt": "2026-05-20T03:00:00Z", "updatedAt": "2026-05-20T03:00:00Z" }
{ "delete": { "_index": "acme_comment_write", "_id": "c1" } }
```
{% endraw %}

이 API는 새 댓글 `c3`를 저장하면서 기존 댓글 `c1`을 삭제한다. Bulk는 여러 action을 묶을 뿐 transaction은 아니므로 일부 item만 실패할 수 있다.

{% raw %}
```java
BulkRequest bulkRequest = new BulkRequest()
        .setRefreshPolicy(WriteRequest.RefreshPolicy.WAIT_UNTIL);

bulkRequest.add(new IndexRequest(names.writeAlias())
        .id(newComment.getId())
        .source(objectMapper.writeValueAsString(newComment), XContentType.JSON));

bulkRequest.add(new DeleteRequest(names.writeAlias(), "c1"));

BulkResponse response = clientGateway.bulk(bulkRequest);
for (BulkItemResponse item : response.getItems()) {
    if (item.isFailed()) {
        log.warn("Bulk item failed. id={}, message={}", item.getId(), item.getFailureMessage());
    }
}
```
{% endraw %}

### 8. Delete By Query API: 조건에 맞는 문서 삭제

{% raw %}
```text
POST /acme_comment_write/_delete_by_query?refresh=true&conflicts=proceed
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        { "term": { "docsId": "docs-1" } }
      ]
    }
  }
}
```
{% endraw %}

이 API는 `companyId = acme`이고 `docsId = docs-1`인 댓글을 모두 삭제한다. 즉 `acme` 회사의 `docs-1` 게시글에 달린 댓글 전체를 정리하는 cascade cleanup API다.

{% raw %}
```java
QueryBuilder query = QueryBuilders.boolQuery()
        .filter(QueryBuilders.termQuery("companyId", companyId))
        .filter(QueryBuilders.termQuery("docsId", docsId));

DeleteByQueryRequest request = new DeleteByQueryRequest(names.writeAlias());
request.setQuery(query);
request.setConflicts("proceed");
request.setRefresh(true);

BulkByScrollResponse response = clientGateway.deleteByQuery(request);
long deleted = response.getDeleted();
```
{% endraw %}

### 9. Delete By Query를 비동기 task로 실행

{% raw %}
```text
POST /acme_comment_write/_delete_by_query?wait_for_completion=false&conflicts=proceed&requests_per_second=500
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

이 API는 `companyId = acme`인 댓글을 비동기로 삭제한다. `requests_per_second=500`은 delete-by-query가 내부 bulk delete를 너무 빠르게 밀어 넣지 않도록 throttling한다.

{% raw %}
```text
GET /_tasks/{taskId}
```
{% endraw %}

진행 상태는 `_tasks` API로 확인한다. 취소가 필요하면 다음처럼 호출한다.

{% raw %}
```text
POST /_tasks/{taskId}/_cancel
```
{% endraw %}

### 10. Update By Query: 조건에 맞는 문서 일괄 수정

{% raw %}
```text
POST /acme_docs_write/_update_by_query?refresh=true&conflicts=proceed
Content-Type: application/json

{
  "script": {
    "source": "ctx._source.status = params.status; ctx._source.updatedAt = params.updatedAt",
    "params": {
      "status": "ARCHIVED",
      "updatedAt": "2026-05-20T04:00:00Z"
    }
  },
  "query": {
    "bool": {
      "filter": [
        { "term": { "companyId": "acme" } },
        {
          "range": {
            "createdAt": {
              "lt": "2026-01-01T00:00:00Z"
            }
          }
        }
      ]
    }
  }
}
```
{% endraw %}

이 API는 `acme` 회사의 오래된 게시글을 `ARCHIVED` 상태로 일괄 변경한다. MVP 기본 API에는 없지만 운영 배치나 데이터 보정 작업에서 등장할 수 있다.

{% raw %}
```java
UpdateByQueryRequest request = new UpdateByQueryRequest(names.writeAlias());
request.setQuery(QueryBuilders.boolQuery()
        .filter(QueryBuilders.termQuery("companyId", companyId))
        .filter(QueryBuilders.rangeQuery("createdAt").lt("2026-01-01T00:00:00Z")));
request.setScript(new Script(
        ScriptType.INLINE,
        "painless",
        "ctx._source.status = params.status; ctx._source.updatedAt = params.updatedAt",
        Map.of("status", "ARCHIVED", "updatedAt", "2026-05-20T04:00:00Z")));
request.setConflicts("proceed");
request.setRefresh(true);
```
{% endraw %}

현재 `ElasticsearchClientGateway`에 update-by-query wrapper가 없다면, gateway 메서드를 추가한 뒤 사용할 수 있다.

### 11. Refresh 정책을 API별로 다르게 보는 이유

| 작업 | 추천 refresh | 이유 |
| --- | --- | --- |
| 단건 생성/수정/삭제 | `wait_for` | API 응답 직후 조회/목록 경험을 안정화 |
| 댓글 bulk 생성 | `false` | 대량 입력 처리량 우선 |
| cascade delete-by-query | `true` | 삭제 후 검색 결과에서 빠지는 경험을 우선 |
| 운영 batch update/delete | 상황별 | 데이터량에 따라 task, throttling, refresh timing을 별도 설계 |

## 운영 주의사항

- Bulk API는 item별 실패를 반드시 확인한다.

- Delete By Query는 대량 segment scan과 delete marker를 만들 수 있어 부하가 크다.

- 대량 삭제는 task monitoring, throttling, retry 전략이 필요하다.

- `refresh=true`를 대량 작업에 남발하지 않는다.

- write alias가 올바른 index를 가리키는지 배포 전 확인한다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [06. Query, Search, Pagination](/posts/06-query-search-pagination/)
>
> - 다음: [08. Elasticsearch를 Database처럼 쓸 때의 제약](/posts/08-elasticsearch를-database처럼-쓸-때의-제약/)

---

## 공식 문서 출처

- [Create or update a document in an index API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-index)

- [Update a document API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-update)

- [Delete a document API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-delete)

- [Bulk index or delete documents API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk)

- [Update documents by query API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-update-by-query)

- [Delete documents by query API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-delete-by-query)
