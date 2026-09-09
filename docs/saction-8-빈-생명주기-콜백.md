---
title: "saction 8 - 빈 생명주기 콜백"
grand_parent: "Spring-Boot"
parent: "[inflearn] 스프링 핵심 원리 - 기본편"
nav_order: 10
permalink: "/notes/saction-8-빈-생명주기-콜백/"
---

#### 8장 - 빈 생명주기 콜백

> 💡 스프링 빈은 간단하게 다음과 같은 라이프사이클을 가진다.
>
> - 객체 생성 → 의존관계 주입

_스프링 빈은 객체를 생성하고, 의존관계 주입이 다 끝난 다음에야 필요한 데이터를 사용할 수 있는 준비가 완료된다. _

따라서 초기화 작업은 의존관계 주입이 모두 완료되고 난 다음에 호출해야 한다. 그런데 개발자가 의존관계 주입이 모두 완료된 시점을 어떻게 알 수 있을까?

  


> 💡 스프링 빈의 이벤트 라이프사이클
>
> - 스프링 컨테이너 생성 → 스프링 빈 생성 → 의존관계 주입 → 초기화 콜백 → 사용  → 소멸전 콜백 → 스프링 종료 
>
> 여기서 의존관계 주입 단계는 필드 주입 또는 수정자 주입의 경우가 거의 해당되고, 생성자 주입의 경우에는 빈 생성 단계에서 생성자를 호출하기 때문에 빈 생성 단계에서 의존관계가 주입된다.

- 초기화 콜백: 빈이 생성되고, 빈의 의존관계 주입이 완료된 후 호출

- 소멸전 콜백: 빈이 소멸되기 직전에 호출

---

- 기본 코드(콜백지정 x)

{% raw %}
```java
public class NetworkClient {
    /**
     * 간단하게 외부 네트워크에 미리 연결하는 객체를 하나 생성한다고 가정해보자.
     * 실제로 네트워크에 연결하는 것은 아니고, 단순히 문자만 출력하도록 했다.
     * 이 NetworkClient 는 애플리케이션 시작 시점에 connect() 를 호출해서 연결을 맺어두어야 하고,
     * 애플리케이션이 종료되면 disconnect() 를 호출해 연결을 끊어야 한다
     */

    private String url;

    public NetworkClient() {

        System.out.println("생성자 호출, url = " + url);
				connect();
        call("초기화 연결 메시지");

    }

    public void setUrl(String url) {
        this.url = url;
    }

    // 서비스 시작시 호출
    public void connect() {
        System.out.println("connect: " + url);
    }

    public void call(String message) {
        System.out.println("call : " + url + ", message : " + message);
    }

    // 서비스 종료시 호출
    public void disconnect() {
        System.out.println("close : " + url);
    }
}
```
{% endraw %}

- 스프링 인터페이스인 `InitializingBean, DisposableBean` 을 통해 생명주기 콜백 지정

{% raw %}
```java
public class NetworkClient implements InitializingBean, DisposableBean {

   ...

    // 의존관계 주입이 끝나면 호출
    @Override
    public void afterPropertiesSet() throws Exception {
        System.out.println("NetworkClient.afterPropertiesSet");
        connect();
        call("초기화 연결 메시지");
    }

    // 빈 종료시 호출
    @Override
    public void destroy() throws Exception {
        System.out.println("NetworkClient.destroy");
        disconnect();
    }
```
{% endraw %}

{% raw %}
```java
생성자 호출, url = null
NetworkClient.afterPropertiesSet
connect: https://sotudy.com
call : https://sotudy.com, message : 초기화 연결 메시지
00:26:54.374 [main] DEBUG org.springframework.context.annotation.AnnotationConfigApplicationContext - Closing org.springframework.context.annotation.AnnotationConfigApplicationContext@5e0826e7, started on Wed Feb 08 00:26:54 KST 2023
NetworkClient.destroy
close : https://sotudy.com
```
{% endraw %}

---

- 설정 정보에 초기화, 종료 메소드 지정하여 빈 등록

{% raw %}
```java
public class NetworkClient {
    
...

    // 의존관계 주입이 끝나면 호출
    public void init() throws Exception {
        System.out.println("NetworkClient.init");
        connect();
        call("초기화 연결 메시지");
    }

    // 빈 종료시 호출
    public void close() throws Exception {
        System.out.println("NetworkClient.close");
        disconnect();
    }
}
```
{% endraw %}

{% raw %}
```java
	// configuration class, 빈 등록
	@Configuration
  static class LifeCycleConfig {

      @Bean(initMethod = "init", destroyMethod = "close")
      public NetworkClient networkClient() {
          NetworkClient networkClient = new NetworkClient();
          networkClient.setUrl("https://sotudy.com");
          return networkClient;
      }
}
```
{% endraw %}

{% raw %}
```java
생성자 호출, url = null
NetworkClient.init
connect: https://sotudy.com
call : https://sotudy.com, message : 초기화 연결 메시지
00:42:53.062 [main] DEBUG org.springframework.context.annotation.AnnotationConfigApplicationContext - Closing org.springframework.context.annotation.AnnotationConfigApplicationContext@5e0826e7, started on Wed Feb 08 00:42:52 KST 2023
NetworkClient.close
close : https://sotudy.com
```
{% endraw %}

---

- 어노테이션을 이용하여 생명주기 콜백 지정
    - `@PostConstruct`

    - `@PreDestroy`

{% raw %}
```java
public class NetworkClient {
    
		...

    // 의존관계 주입이 끝나면 호출
    @PostConstruct
    public void init() throws Exception {
        System.out.println("NetworkClient.init");
        connect();
        call("초기화 연결 메시지");
    }

    // 빈 종료시 호출
    @PreDestroy
    public void close() throws Exception {
        System.out.println("NetworkClient.close");
        disconnect();
    }
}
```
{% endraw %}

> 💡 어노테이션을 이용하는 방법이 스프링에서 가장 권장하고 있는 방법.
> javax 하위에 존재하는 어노테이션인데, 이는 스프링에 종속적인 기술이 아니라 JSR-250 이라는 자바 표준을 따르는 기술임을 나타낸다.

> 💡  결론 : `@PostConstruct` , `@PreDestroy` 어노테이션을 사용하자.
> 하지만 이는 외부 라이브러리에는 적용할 수 없기 때문에 초기화 과정에서 외부 라이브러리를 사용해야 한다면 @Bean 의 초기화, 종료 메소드 지정 방법을 사용하면 될 것이다.
