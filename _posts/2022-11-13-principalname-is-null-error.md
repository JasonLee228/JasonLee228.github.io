---
title: "principalName is null error"
date: 2022-11-13 13:36:22 +0000
categories: ["기타", "SPOTY-PROJECT(종료)"]
---

계속 principalName is null 오류 발생,,,,

![image](/assets/images/97dd9b1c3fd143e9a888288ba10c1d8b.png)

PrincipalName 이란 변수명을 찾지 못했었는데, 결국 전부 디버그 찍어가면서 찾아보니 

- OAuth2LoginAuthenticationFilter 내부에 `OAuth2AuthorizedClient` principal 객체 등록하는 부분에 다음과 같은 코드가 존재했다.

![image](/assets/images/20d941a87279495188bc01d62cc8f564.png)

위 코드의 ` oauth2Authentication.getName()` 부분에서 null을 참조하고 있었던 것. 그럼 이 getName은 대체 어떤 name을 가져오는 것인가?

→ [AbstractAuthenticationToken.java](http://AbstractAuthenticationToken.java) 에서의 getName을 사용하고 있었는데, 내가 사용한 oauth2의 구현 객체는 UserDetails 객체를 사용했었다.

![image](/assets/images/80807cf13bbf425f831ce2a23c5a2786.png)

여기에서 문제가 발생한 것이고, 알고 보니 필요 없어 안 쓸거라고 생각해 구현하지 않았던

 `UserDetails` 를 상속받은 `CustomUserDetails` 클래스의 getUsername  메소드에 Null을 집어넣고 있었던 것…

![image](/assets/images/43f2b94d93a94e07a33dd720b6205b56.png)

필요할 시인데 모르고 구현 안해놓고 있었다;;

아래처럼 바꿔주니 동작한다!

![image](/assets/images/b137da1024eb4227b5125eeb89920cc3.png)
