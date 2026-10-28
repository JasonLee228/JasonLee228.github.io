---
# the default layout is 'page'
icon: fas fa-info-circle
order: 5
---

## 안녕하세요, 찬근입니다

백엔드 개발자입니다. Spring으로 서비스를 만들고 Kubernetes 환경에서 운영하고 있어요.
공부한 내용과 일하면서 부딪힌 문제를 잊지 않으려고 이곳에 정리합니다.

## 이 블로그에서 다루는 것

{% assign topics = site.posts | group_by_exp: "post", "post.categories[0]" | sort: "size" | reverse %}
{% for topic in topics %}{% if topic.name != "" %}
{%- capture topic_url %}/categories/{{ topic.name | slugify | url_encode }}/{% endcapture %}
- [{{ topic.name }}]({{ topic_url | relative_url }}) · {{ topic.size }}편
{%- endif %}{% endfor %}

주제별로 묶어 보려면 사이드바의 [목차]({{ '/toc/' | relative_url }})를, 날짜순으로 보려면 [아카이브]({{ '/archives/' | relative_url }})를 이용해 주세요.

## 연락

- GitHub: [JasonLee228](https://github.com/JasonLee228)
