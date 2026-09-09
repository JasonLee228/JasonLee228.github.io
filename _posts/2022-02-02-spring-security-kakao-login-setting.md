---
title: "Spring security - kakao login setting"
date: 2022-02-02 14:03:33 +0000
categories: ["Spring-Boot", "스프링부트와 AWS로 혼자 구현하는 웹 서비스"]
---

#application-oauth.properties

{% raw %}
```java
# KakaoRegistration
spring.security.oauth2.client.registration.kakao.client-id=REST API KEY
spring.security.oauth2.client.registration.kakao.client-secret=SECRET KEY
spring.security.oauth2.client.registration.kakao.redirect-uri={baseUrl}/{action}/oauth2/code/{registrationId}
spring.security.oauth2.client.registration.kakao.authorization-grant-type=authorization_code
spring.security.oauth2.client.registration.kakao.scope=profile_nickname,profile_image,account_email
spring.security.oauth2.client.registration.kakao.client-name=kakao
spring.security.oauth2.client.registration.kakao.client-authentication-method=POST

# KakaoProvider
spring.security.oauth2.client.provider.kakao.authorization-uri=https://kauth.kakao.com/oauth/authorize
spring.security.oauth2.client.provider.kakao.token-uri=https://kauth.kakao.com/oauth/token
spring.security.oauth2.client.provider.kakao.user-info-uri=https://kapi.kakao.com/v2/user/me
spring.security.oauth2.client.provider.kakao.user-name-attribute=id
```
{% endraw %}

#OAuthAttributs.java

{% raw %}
```java
private static OAuthAttributes ofKakao(String userNameAttributeName, Map<String, Object> attributes){
        Map<String , Object> response = (Map<String, Object>) attributes.get("kakao_account");
        Map<String , Object> properties = (Map<String, Object>) attributes.get("properties");//조회해본 결과 profile은 propseties안에 있음.
        System.out.println("####attributes_key### : "+attributes.keySet());
        System.out.println("####attributes_value### : "+attributes.values());
        System.out.println("####response_key### : "+response.keySet());
        System.out.println("####response_value### : "+response.values());

        /*
        실제로 profile이 있기는 한데
        properties안에 profile이 있어서 이중으로 받아야 가능함. 이전 자바파일에서도 profile로 받은게 아니라 properties로 받음
        */
        return OAuthAttributes.builder()
                .name((String) properties.get("nickname"))
                .email((String) response.get("email"))
                .picture((String) properties.get("profile_image"))
                .attributes(attributes)//key set으로 id를 가지고 있는게 attributes밖에 없었음. 그래서 CustomOAuth2UserService에서 id를 받아야 하기 때문에 attributes를 연결
                .nameAttributeKey(userNameAttributeName)
                .build();
    }
```
{% endraw %}

일일이 각각의 key-value값 조회해본 결과 해당하는 값을 받기 위한 코드들이다.
