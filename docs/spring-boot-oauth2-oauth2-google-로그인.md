---
title: "[Spring boot Oauth2] oauth2 - google 로그인"
grand_parent: "기타"
parent: "SPOTY-PROJECT(종료)"
nav_order: 2
permalink: "/notes/spring-boot-oauth2-oauth2-google-로그인/"
---

#### 1. 구글 API 페이지 접속 

[Google Cloud Platform](https://console.cloud.google.com/apis/dashboard)

#### 2. 프로젝트 생성

- 좌 상단 프로젝트 선택 버튼 클릭

![image](/assets/images/89a5c057b7bd4af78fb3bae82f464c39.png)

- 프로젝트 생성 - 새 프로젝트

![image](/assets/images/039efd8a91764106a939217d8774c816.png)

- 프로젝트 이름 기입 후 생성

![image](/assets/images/b677ad5bc7c6492e9dec7695d38825b1.png)

- OAuth 동의 화면 이동, 앱 이름, 지원 및 개발자 메일 등록 후 저장

![image](/assets/images/c70cd0d7037a422295363434e6bb0241.png)

- 사용자 인증 정보 등록
    - 사용자 인증 정보 화면 → 사용자 인증 정보 만들기 → **OAuth 클라이언트 ID**

    - 애플리케이션 유형 : 웹 애플리케이션

    - 이름 : 원하는 이름 입력!

    - 승인된 리디렉션 URI : [http://localhost:8080/login/oauth2/code/google](http://localhost:8080/login/oauth2/code/google)

> 💡  위 URI는, 사용자가 구글 로그인을 완료했을 시 해당 URI로 code를 반환한다.
> 받은 코드를 통해 서버는 구글에게 Access Token을 요청하는 code로 사용한다.
> (스프링에서는 해당 부분을 OAuth2 라이브러리가 해줄 것이다 ㅎㅎ)
>
> 현재 로컬 개발환경이라고 생각하고 localhost로 URI를 등록했다.

![image](/assets/images/c071b15484fc47649e4c924143524c6f.png)

![image](/assets/images/906725dafa2e447ba3769a43fa9be041.png)

- 이렇게 입력한 뒤 만들게 되면 아래 화면처럼 ClientId, ClientSecret 을 생성해줄 것이다.
    - 이 id, secret 은 외부로 절대! 노출하면 안된다.

![image](/assets/images/03e0dda5a60845b0a36a36e20820e608.png)

#### 3. spring project setting

- build.gradle

{% raw %}
```java
// OAuth2
implementation 'org.springframework.boot:spring-boot-starter-oauth2-client'
```
{% endraw %}

- application.yml

{% raw %}
```java
spring:
	security:
	  oauth2:
	    client:
	      registration:
	        google:
	          client-id: YOUR_CLIENT_ID.apps.googleusercontent.com
	          client-secret: GOCSPX-REDACTED_CLIENT_SECRET
	          scope:
	            - email
	            - profile
```
{% endraw %}

- SecurityConfig(기존 설정 하위에 다음과 같이 추가)

{% raw %}
```java
....
.oauth2Login();
```
{% endraw %}

> 💡 이렇게 까지 하면, 
> [http://localhost:8080/oauth2/authorization/google](http://localhost:8080/oauth2/authorization/google)
> 위 페이지로 접속하게 되면 구글 로그인 창이 뜰 것이다!

![image](/assets/images/241c51b25f2743388ebc402b3dd40703.png)
