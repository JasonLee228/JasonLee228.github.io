---
title: "@ConditionalOnProperty"
date: 2023-10-12 04:36:58 +0000
categories: ["Spring", "활용"]
tags: ["활용", "spring"]
---

#### ConditionalOnProperty 어노테이션이란?

`@ConditionalOnProperty` 어노테이션은 스프링 부트(Spring Boot) 애플리케이션에서 빈(bean)을 조건부로 등록하거나 활성화하는데 사용되는 스프링 프레임워크의 조건부 어노테이션 중 하나입니다. 이 어노테이션은 프로퍼티(Property) 값을 기반으로 조건부 빈 등록을 수행합니다.

---

#### 주요 속성에 대한 설명

- `name`: 조건을 검사할 프로퍼티의 이름을 나타냅니다.

- `havingValue`: `name` 프로퍼티가 가져야 하는 값입니다. 이 값과 일치할 때 조건이 충족됩니다.

- `matchIfMissing`: `name` 프로퍼티가 존재하지 않을 경우에 대한 동작을 제어합니다. 기본값은 `true`로, 프로퍼티가 존재하지 않으면 조건이 충족됩니다. `false`로 설정하면 프로퍼티가 존재하지 않을 경우 조건이 충족되지 않습니다.

예를 들어, `@ConditionalOnProperty` 어노테이션은 특정 프로퍼티 값에 따라 빈을 등록하거나 활성화하는데 사용됩니다. 아래는 `custom.schedule-run` 프로퍼티가 "true"일 때 빈을 등록하는 예제입니다:

{% raw %}
```java
@Configuration
@ConditionalOnProperty(name = "custom.schedule-run", havingValue = "true", matchIfMissing = false)
public class CustomScheduleConfiguration {
    // 이 빈은 custom.schedule-run 프로퍼티가 "true"일 때만 활성화됨
}

```
{% endraw %}

이 경우, `custom.schedule-run` 프로퍼티가 "true"로 설정된 경우에만 `CustomScheduleConfiguration` 빈이 등록됩니다. 만약 `custom.schedule-run` 프로퍼티가 존재하지 않거나 "true"가 아닌 다른 값으로 설정된 경우에는 이 빈이 활성화되지 않습니다.

이 어노테이션은 스프링 부트 애플리케이션의 설정을 유연하게 구성하고 필요한 빈을 동적으로 활성화 또는 비활성화하는 데 유용합니다.
