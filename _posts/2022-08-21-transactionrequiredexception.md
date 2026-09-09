---
title: "TransactionRequiredException"
date: 2022-08-21 13:51:34 +0000
categories: ["프로젝트", "SPOTY"]
tags: ["spoty", "프로젝트"]
permalink: /posts/transactionrequiredexception/
---

# Team 테이블 구조

![image](/assets/images/7a4c4c4383804b22917e484206b3bc1d.png)

팀 저장 시 로고 명은 따로 업데이트 하기에 Repository 클래스에서 따로 업데이트를 해 준다.

해당 로고 업데이트는 @Query 어노테이션을 이용해 구현했고, 코드는 다음과 같다.

{% raw %}
```java
@Modifying(clearAutomatically = true)
@Query("UPDATE FROM Team p SET p.logo = :logo WHERE p.id = :teamId")
	void updateLogo(@Param("teamId")Long teamId, @Param("logo")String logo);
```
{% endraw %}

그런데 해당 쿼리 적용 시 다음과 같은 오류가 발생.

> 💡 javax.persistence.TransactionRequiredException: Executing an update/delete query

찾아보니, jpa에서 update, delete 쿼리를 이용할 때는 `@Transactional` 어노테이션을 달아줘야 한다고 한다. 

원래는 domain 클래스 내에서 update를 했지만, 이번엔 리포지토리에서 구현했기 때문에 필요 없다고 생각했는데 아니였나 보다.

{% raw %}
```java
@Transactional
@Modifying(clearAutomatically = true)
@Query("UPDATE FROM Team p SET p.logo = :logo WHERE p.id = :teamId")
	void updateLogo(@Param("teamId")Long teamId, @Param("logo")String logo);
```
{% endraw %}

코드를 이렇게 바꾸고, 다시 호출

![image](/assets/images/33db951b095447f2b81da51b60a57758.png)

정상적으로 동작한다.
