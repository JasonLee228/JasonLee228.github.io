---
title: "Spring AOP 를 이용한 캐시 적용"
date: 2024-03-11 05:16:23 +0000
categories: ["Spring", "운영"]
tags: ["운영", "spring"]
---

#### 📌 주의 사항

> AOP 를 이용하여 캐시를 적용하면 @Around 가 적용된 메소드에 대해서 프록시 형태로 적용되기 때문에, 원래 메소드 내의 inner method call 에 대해서는 캐시 적용이 안 된다는 것..

{% raw %}
```java
public class SimplePojo implements Pojo {

	public void foo() {
		// this next method invocation is a direct call on the 'this' reference
		this.bar();
	}

	public void bar() {
		// some logic...
	}
}
```
{% endraw %}

→ 위와 같은 코드에서 bar() 에 캐시가 적용되어 있어도 캐시 foo() 호출 시 캐시가 적용되지 않는다는 것..

- 참고

[redis cache 를 @annotation 으로 하기 (with @Aspect)](https://nevercaution.github.io/redis-cache-annotation-with-aspect/)

[Spring AOP not working for method call inside another method](https://stackoverflow.com/questions/13564627/spring-aop-not-working-for-method-call-inside-another-method)

[Proxying Mechanisms :: Spring Framework](https://docs.spring.io/spring-framework/reference/core/aop/proxying.html#aop-understanding-aop-proxies)

---

#### Spring AOP vs AspectJ

[자바 AOP의 모든 것(Spring AOP & AspectJ)](https://jiwondev.tistory.com/152)
