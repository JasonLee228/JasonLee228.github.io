---
title: "02. Cluster, Index, Shard, Replica"
date: 2026-05-20 02:58:06 +0000
categories: ["Elasticsearch", "기초"]
tags: ["기초", "elasticsearch"]
---

> 🧭 
>
> **문서 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [01. RDB 관점에서 Elasticsearch 이해하기](/posts/01-rdb-관점에서-elasticsearch-이해하기/)
>
> - 다음: [03. Document, Mapping, Data Types](/posts/03-document-mapping-data-types/)

Elasticsearch는 처음부터 분산 검색 엔진으로 설계되었다. RDB의 단일 DB 인스턴스 관점으로 접근하면 `shard`, `replica`, `allocation` 같은 개념이 낯설 수 있다.

## 기본 구조

{% raw %}
```text
Cluster
  Node A
    primary shard 0
    replica shard 1
  Node B
    primary shard 1
    replica shard 0
```
{% endraw %}

| 개념 | 설명 |
| --- | --- |
| Cluster | 여러 Elasticsearch node가 하나의 시스템처럼 동작하는 단위 |
| Node | Elasticsearch 프로세스 하나 |
| Index | document를 저장하고 검색하는 논리적 단위 |
| Primary shard | index 데이터를 나누어 저장하는 원본 shard |
| Replica shard | primary shard의 복제본 |
| Allocation | shard를 어떤 node에 배치할지 결정하는 과정 |

## Index는 왜 shard로 나뉘는가

- 데이터를 여러 node에 분산 저장한다.

- 검색 요청을 shard별로 병렬 처리한다.

- 한 node 장애 시 replica를 이용해 서비스를 계속할 수 있다.

- 데이터 증가에 따라 저장 공간과 처리량을 분산한다.

## Primary shard

Primary shard는 document의 원본이 저장되는 shard다. document를 index할 때 Elasticsearch는 `_id` routing 값을 기준으로 어떤 primary shard에 저장할지 결정한다.

{% raw %}
```text
document _id
  -> routing hash
    -> primary shard 선택
      -> replica shard로 복제
```
{% endraw %}

Elasticsearch 7.x에서 index 생성 시 `number_of_shards`를 지정하면 생성 후 일반적인 설정 변경처럼 바꿀 수 없다. 운영에서는 처음 index 설계 시 primary shard 수를 신중히 정해야 한다.

## Replica shard

Replica shard는 primary shard의 복제본이다. 주 목적은 장애 대응과 검색 부하 분산이다.

## MVP에서 shard와 replica를 직접 지정하지 않는 이유

`es-rhlc-mvp`의 mapping JSON은 `refresh_interval`만 지정한다. 신규 index는 운영 Elasticsearch의 기본값 또는 index template 정책을 따른다. MVP에서는 단순하지만, 운영에서는 index template 또는 bootstrap 정책으로 shard/replica 기준을 명시하는 편이 좋다.

## 확인 API

{% raw %}
```bash
curl -X GET "http://localhost:9200/_cat/indices?v"
curl -X GET "http://localhost:9200/_cat/shards?v"
curl -X GET "http://localhost:9200/_cluster/health?pretty"
```
{% endraw %}

## Green, Yellow, Red

| 상태 | 의미 |
| --- | --- |
| green | primary와 replica가 모두 정상 배치됨 |
| yellow | primary는 정상이나 replica 일부가 미배치 |
| red | primary shard 일부가 미배치되어 데이터 접근에 문제가 있음 |

## Tenant index 전략과 shard 수

MVP는 회사별로 docs/comment index를 나눈다.

{% raw %}
```text
acme_docs_v1
acme_comment_v1
softcamp_docs_v1
softcamp_comment_v1
```
{% endraw %}

Tenant index 전략은 격리와 삭제가 단순해지는 장점이 있다. 하지만 tenant 수가 많아지면 index와 shard 수도 함께 늘어나 cluster state와 shard 관리 비용이 커질 수 있다.

## 권장 판단 기준

| 상황 | 권장 방향 |
| --- | --- |
| tenant 수가 적고 tenant별 격리가 중요함 | tenant별 index |
| tenant 수가 많고 tenant별 데이터량이 작음 | shared index + `companyId` filter 검토 |
| tenant별 retention/delete가 중요함 | tenant별 index 또는 rollover 정책 검토 |
| 대량 검색과 집계가 많음 | shard 수와 routing 전략 검토 |

---

> 🧭 
>
> **다음으로 이동**
>
> - 상위: [Elasticsearch](/categories/기초/)
>
> - 이전: [01. RDB 관점에서 Elasticsearch 이해하기](/posts/01-rdb-관점에서-elasticsearch-이해하기/)
>
> - 다음: [03. Document, Mapping, Data Types](/posts/03-document-mapping-data-types/)

---

## 공식 문서 출처

- [Shard allocation, relocation, and recovery](https://www.elastic.co/docs/deploy-manage/distributed-architecture/shard-allocation-relocation-recovery)

- [Red or yellow cluster health status](https://www.elastic.co/docs/troubleshoot/elasticsearch/red-yellow-cluster-status)

- [Explain the shard allocations API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-allocation-explain)
