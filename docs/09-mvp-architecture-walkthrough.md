---
title: "09. MVP Architecture Walkthrough"
parent: "Elasticsearch"
nav_order: 10
permalink: "/notes/09-mvp-architecture-walkthrough/"
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/notes/elasticsearch/)
>
> - 이전: [08. Elasticsearch를 Database처럼 쓸 때의 제약](/notes/08-elasticsearch를-database처럼-쓸-때의-제약/)
>
> - 다음: [10. 운영 체크리스트와 용어집](/notes/10-운영-체크리스트와-용어집/)

이 문서는 Elasticsearch 개념이 `es-rhlc-mvp` 코드에서 어떻게 연결되는지 따라간다. 상세 API별 lifecycle은 `docs/elasticsearch-operations-and-lifecycle.md`에 더 길게 정리되어 있다.

## 전체 계층

{% raw %}
```text
Controller
  -> Service
    -> Domain Repository
      -> AbstractEsCrudRepository
        -> ElasticsearchClientGateway
          -> RestHighLevelClient
            -> Elasticsearch
```
{% endraw %}

| 계층 | 책임 |
| --- | --- |
| Controller | HTTP path/body/query를 받고 Service 호출 |
| Service | 회사/게시글 존재 검증, 관계 무결성, lock, cascade orchestration |
| Domain Repository | 도메인별 query 메서드 제공 |
| AbstractEsCrudRepository | 공통 ES CRUD/search/bulk/delete-by-query |
| ElasticsearchClientGateway | RHLC 호출 경계 |
| RestHighLevelClient | Elasticsearch 7.9.3 HTTP API 호출 |

## 왜 Gateway를 두는가

`RestHighLevelClient`는 ES 7.x 시대의 client이며 deprecated 상태다. 운영 ES가 7.9.3이면 현실적인 선택이지만 장기적으로 Java API Client 전환 가능성을 생각해야 한다. MVP는 RHLC 호출을 `ElasticsearchClientGateway`에 모은다.

{% raw %}
```java
public IndexResponse index(IndexRequest request) throws IOException {
    return client.index(request, RequestOptions.DEFAULT);
}

public SearchResponse search(SearchRequest request) throws IOException {
    return client.search(request, RequestOptions.DEFAULT);
}

public BulkByScrollResponse deleteByQuery(DeleteByQueryRequest request) throws IOException {
    return client.deleteByQuery(request, RequestOptions.DEFAULT);
}
```
{% endraw %}

## 회사 생성 흐름

{% raw %}
```text
CompanyController.create
  -> CompanyService.create
    -> CompanyRepository.save(null, company)
      -> AbstractEsCrudRepository.createIndexIfAbsent(null)
      -> IndexRequest(company_write)
```
{% endraw %}

전역 company index는 `CompanyIndexBootstrap`이 애플리케이션 기동 시 미리 만든다. 그래도 `save()`는 공통 로직상 `createIndexIfAbsent()`를 호출한다.

## 게시글 생성 흐름

{% raw %}
```text
DocsController.create
  -> DocsService.create
    -> CompanyService.get(companyId)
      -> CompanyRepository.findById(null, companyId)
    -> DocsRepository.save(companyId, docs)
      -> createIndexIfAbsent(companyId)
        -> HEAD /{companyId}_docs_read
        -> PUT /{companyId}_docs_v1
      -> IndexRequest({companyId}_docs_write)
```
{% endraw %}

게시글 저장은 tenant docs physical index lazy creation을 트리거할 수 있다. `IndexNameResolver`는 physical base name과 alias base name을 분리해 `sc_docs_v1` physical index에는 `sc_docs_read`, `sc_docs_write` stable alias를 붙인다.

## 댓글 생성과 bulk 생성

단건 댓글 생성:

{% raw %}
```text
CommentController.create
  -> CommentService.create
    -> DocsService.get(companyId, docsId)
    -> CommentRepository.save(companyId, comment)
```
{% endraw %}

Bulk 댓글 생성:

{% raw %}
```text
CommentController.createBulk
  -> CommentService.createBulk
    -> DocsService.get(companyId, docsId)
    -> CommentRepository.saveAll(companyId, comments, "false")
```
{% endraw %}

단건 저장은 기본 `wait_for` refresh policy를 사용하고, bulk 저장은 `false`를 사용한다.

## 목록 조회 흐름

Repository query:

{% raw %}
```java
return search(
        companyId,
        QueryBuilders.termQuery("companyId", companyId),
        List.of(
            SortBuilders.fieldSort("createdAt").order(SortOrder.ASC),
            SortBuilders.fieldSort("id").order(SortOrder.ASC)),
        size,
        searchAfter);
```
{% endraw %}

ES API 관점:

{% raw %}
```javascript
GET /acme_docs_read/_search
Content-Type: application/json

{
  "track_total_hits": true,
  "query": {
    "term": {
      "companyId": "acme"
    }
  },
  "sort": [
    { "createdAt": "asc" },
    { "id": "asc" }
  ],
  "size": 20
}
```
{% endraw %}

## 게시글 삭제 흐름

{% raw %}
```text
DocsService.delete
  -> lock docs:{companyId}:{docsId}
    -> DocsService.get(companyId, docsId)
    -> DocsRepository.deleteById(companyId, docsId)
    -> DocsChildCleanupService.deleteDocsChildren(companyId, docsId) @Async
      -> CommentRepository.deleteByDocsId(companyId, docsId)
```
{% endraw %}

## 회사 삭제 흐름

{% raw %}
```text
CompanyService.delete
  -> lock company:{companyId}
    -> CompanyService.get(companyId)
    -> CompanyRepository.deleteById(null, companyId)
    -> CompanyChildCleanupService.deleteCompanyChildren(companyId) @Async
      -> CommentRepository.deleteByCompanyId(companyId)
      -> DocsRepository.deleteByCompanyId(companyId)
```
{% endraw %}

회사 root document 삭제가 성공하면 child cleanup은 비동기로 진행된다. cleanup 실패는 HTTP 응답을 rollback하지 않는다.

## Health check

`ElasticsearchHealthChecker`는 `restHighLevelClient.ping()`, `cluster().health()`, cluster status가 `RED`인지 여부를 확인한다. ES 연결 실패가 애플리케이션 기동 자체를 막지는 않고 health endpoint에서 상태를 드러낸다.

## 코드 읽기 순서

1. `README.md`

1. `src/main/resources/index/*.json`

1. `IndexNameResolver`

1. `IndexMappingLoader`

1. `AbstractEsCrudRepository`

1. `CompanyRepository`, `DocsRepository`, `CommentRepository`

1. `CompanyService`, `DocsService`, `CommentService`

1. `docs/elasticsearch-operations-and-lifecycle.md`

1. alias switch 흐름을 볼 때는 admin API `/api/admin/elasticsearch/aliases/switch`, `_reindex`, `_tasks`, `_aliases` 순서를 함께 확인한다.

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/notes/elasticsearch/)
>
> - 이전: [08. Elasticsearch를 Database처럼 쓸 때의 제약](/notes/08-elasticsearch를-database처럼-쓸-때의-제약/)
>
> - 다음: [10. 운영 체크리스트와 용어집](/notes/10-운영-체크리스트와-용어집/)

---

## 공식 문서 출처

- [Getting started with the Elasticsearch Java client](https://www.elastic.co/docs/reference/elasticsearch/clients/java/getting-started)

- [Javadoc for the Elasticsearch Java REST client](https://www.elastic.co/docs/reference/elasticsearch/clients/java/transport/rest-client/usage/javadoc)

- [Run a search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search)

- [Bulk index or delete documents API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk)
