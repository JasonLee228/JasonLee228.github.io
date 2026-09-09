---
title: "Test에 Security 적용 시 오류 해결(MYSQL사용 시)"
parent: "Spring-Boot"
nav_order: 2
permalink: "/notes/test에-security-적용-시-오류-해결mysql사용-시/"
---

> 💡 springboot.config.auth.CustomOAuth2UserService를 찾을 수 없다고 문제가 뜰 것이다.
> 책에서 나온 대로 [application.properties](http://application.properties) 파일을 수정하면 
> posts Test와 HelloControllerTest말고는 실행이 되는 게 원래는 맞지만,

> 💡 우리는 H2 DB가 아닌 MYSQL DB를 사용한다.
> → 관련 설정을 해 줘야 하는데, 설정코드는 다음을 참고

---

#기존 코드

{% raw %}
```java
spring.jpa.properties.hibernate.dialect-org.hibernate.dialect.MYSQL5InnoDBDialect=
spring.jpa.show-sql=true
spring.session.store-type=jdbc

#TEST OAuth

spring.security.oauth2.client.registration.google.client-id=test
spring.security.oauth2.client.registration.google.client-secret=test
spring.security.oauth2.client.registration.google.scope=profile,email
```
{% endraw %}

#수정한 코드

{% raw %}
```java
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver
spring.datasource.url=jdbc:mysql://localhost:3306/test1?useSSL=false&useUnicode=true&serverTimezone=Asia/Seoul
spring.datasource.username=root
spring.datasource.password=root
spring.jpa.hibernate.ddl-auto=update
spring.jpa.properties.hibernate.format_sql=true

spring.profiles.include=oauth

spring.jpa.properties.hibernate.dialect-org.hibernate.dialect.MYSQL5InnoDBDialect=
spring.jpa.show-sql=true
spring.session.store-type=jdbc
spring.session.jdbc.initialize-schema=always

#TEST OAuth

spring.security.oauth2.client.registration.google.client-id=test
spring.security.oauth2.client.registration.google.client-secret=test
spring.security.oauth2.client.registration.google.scope=profile,email
```
{% endraw %}

> 💡 기존 코드에 mySql관련 설정을 추가해준 모습이고, SQL관련 설정값은 자신의 설정값을 집어넣으면 된다.

#### 그렇다면 기존 테스트에서는 왜 관련 설정을 해주지 않아도 됐는가?

> 💡 이유는 당연하다.
> Spring_test에서는 test에 application.properties가 없을 때 src.main의 properties파일을 그대로 가져와서 사용한다. 우리의 main.application.properties에 Sql관련 설정을 해 두었으니 당연하게 가져와서 사용해서 됐던 것.

> 💡 하지만 test.application.properties파일을 src.test에 추가해 주면서, 
> main의 properties를 가져와서 사용할 수 없게 되었기 때문에 새로 추가해 주어야 한다.
> 해당 해결법이 수정한 코드의 내용인 것.

> 💡 사실 근데 
> spring.jpa.hibernate.ddl-auto=update
> spring.jpa.properties.hibernate.format_sql=true
>
> spring.profiles.include=oauth
> 부분은 없어도 잘 돌아가는데, 혹여나 하는 생각에 같이 집어넣었다.
