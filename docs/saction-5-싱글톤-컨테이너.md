---
title: "saction 5 - 싱글톤 컨테이너"
grand_parent: "Spring-Boot"
parent: "[inflearn] 스프링 핵심 원리 - 기본편"
nav_order: 7
permalink: "/notes/saction-5-싱글톤-컨테이너/"
---

## 싱글톤 컨테이너

### 1. 웹 애플리케이션과 싱글톤

> 💡 스프링이란, 기업용 온라인 서비스를 위해서 탄생함
> 이런 온라인 서비스에서는 수많은 고객들이 동시에 요청을 한다.
> → 같은 서비스에 대해서 동시에 많은 요청이 들어올 경우, 매번 객체 클래스를 생성한다면 속도, 메모리적인 부분에서 낭비가 심할 것이다.
> → 해결 방안 : 하나만 생성해서 공유하도록 하면 된다!

<details markdown="1"><summary>테스트 코드 - 스프링 없이 단순 DI 컨테이너로의 서비스 호출 예시</summary>



</details>

---

### 2. 싱글톤 패턴

> _싱글톤 패턴 : 클래스의 인스턴스가 딱 1개만 생성되는 것을 보장하는 디자인 패턴  
> _→ 객체 인스턴스를 2개 이상 생성하지 못하도록 막아야 한다.

- 싱글톤 패턴 구현

{% raw %}
```java
public class SingletonService {

    // 클래스 내부에서 private 로 선언 -> 타 클래스에서 instance 변수?에 접근 불가
    // static 으로 선언 -> 클래스 레벨에서 하나만 존재할 수 있다.
    private static final SingletonService instance = new SingletonService();

    // 이렇게 해두면 프로그램이 실행될 때 static 으로 선언된 instance 에 new 를 통해서 생성된 SingletonService 의 참조값을 넣어둔다.
    public static SingletonService getInstance() { // 이 메소드를 통해서 타 클래스에서 instance 에 접근할 수 있도록 한 것.
        return instance;
    }

    
    private SingletonService() {
    }

    public void logic() {
        System.out.println("싱글톤 객체 로직 호출");
    }

}
```
{% endraw %}

> 💡 **생성자를 private** 로 선언하게 되면, 외부에서는 SingletonService 자체를 생성할 수 없다.
>
> 1. static 영역에 객체 instance를 미리 하나 생성해서 올려둔다.
> 2. 이 객체 인스턴스가 필요하면 오직 getInstance() 메서드를 통해서만 조회할 수 있다. 이 메서드를 호출하면 항상 같은 인스턴스를 반환한다.
> 3. 딱 1개의 객체 인스턴스만 존재해야 하므로, 생성자를 private으로 막아서 혹시라도 외부에서 new 키워드로 객체 인스턴스가 생성되는 것을 막는다.

<details markdown="1"><summary>싱글톤 패턴을 적용 → 테스트</summary>



</details>

> 💡 # 싱글톤 패턴의 문제점
>
> - 싱글톤 패턴을 구현하는 코드 자체가 많이 들어간다.
>
> - 의존관계상 클라이언트가 구체 클래스에 의존한다. → DIP를 위반한다.
>     - 객체 인스턴스를 얻기 위해 클래스의 getInstance 메소드를 호출해야 하기 때문
>
> - 클라이언트가 구체 클래스에 의존해서 OCP 를 위반할 가능성이 높다.
>
> - 테스트가 어려움
>
> - 내부 속성을 변경하거나 초기화하기 어렵다.
>
> - private 생성자를 사용하기에 자식 클래스를 만들기 어려움.
>
> → 결론 : 유연성이 떨어짐.

---

### 3. 싱글톤 컨테이너

> 💡 스프링은 위의 싱글톤 패턴의 문제들을 해결하면서, 객체 인스턴스를 싱글톤으로 관리한다.
> 이러한 싱글톤으로 관리되는 객체 인스턴스가 바로 ‘빈(Bean)’
>
> - 스프링 컨테이너는 객체를 ‘하나만’ 생성해서 관리한다.
>
> - 스프링 컨테이너는 싱글톤 컨테이너 역할을 한다. 
>     - 싱글톤 객체를 생성하고 관리하는 기능을 _**싱글톤 레지스트리 **_라 한다.
>
> - 스프링 컨테이너의 기능 덕에 싱글톤 패턴의 단점을 해결하면서 객체를 싱글톤으로 유지할 수 있다.
>     - 싱글톤 패턴을 위한 코드 필요 x
>
>     - DIP, OCP, 테스트, private 생성자로부터 자유로움

- 싱글톤 컨테이너를 확인해보자

{% raw %}
```java
		@Test
    @DisplayName("스프링 컨테이너와 싱글톤")
    void springContainer() {

        ApplicationContext ac = new AnnotationConfigApplicationContext(AppConfig.class);

        MemberService memberService1 = ac.getBean("memberService", MemberService.class);
        MemberService memberService2 = ac.getBean("memberService", MemberService.class);

        System.out.println("memberService1 = " + memberService1);
        System.out.println("memberService2 = " + memberService2);

        // memberService1 == memberService2
        assertThat(memberService1).isSameAs(memberService2);
    }
```
{% endraw %}

> 💡 결과
>
> memberService1 = hello.core.member.MemberServiceImpl@4ebff610  
> memberService2 = hello.core.member.MemberServiceImpl@4ebff610  
> → 둘의 참조값이 같은 것을 확인할 수 있다!

- 싱글톤 컨테이너 도입 전 / 후

![image](/assets/images/fd31c596f1d44a5fa6af2b52a8d35f6c.png)

> 📌 스프링 컨테이너를 이용하게 되면, 빈 주입 요청이 올 때마다 빈을 새로 생성하는 것이 아닌(기존의 AppConfig만을 사용했던 방법), 이미 만들어진 객체를 공유해서 효율적으로 재사용을 할 수 있게 해 준다.

---

### 4. 싱글톤 방식 사용시 주의점

- 싱글톤 방식 사용시 주의할 점

> ⚠️ 싱글톤 패턴은 같은 객체 인스턴스를 하나만 만들어서 공유하는 방식이기 때문에 상태 유지(Stateful)하게 설계하면 안된다. → 무상태(Stateless) 설계의 중요성
>
> - 특정 클라이언트에 의존적인 필드가 존재하면 안됨
>
> - 특정 클라이언트가 값을 변경할 수 있는 필드가 있으면 안됨 
>     - 공유되는 필드의 사용 x 
>
>     - 공유되지 않는 지역변수, 파라미터 등을 사용
>
> - ‘쓰기’ 를 왠만해선 허용하면 안됨. 가급적 읽기만

- 공유 필드가 있을 경우 발생하는 문제

{% raw %}
```java
public class StatefulService {

    private int price;

    public void order(String name, int price) {
        System.out.println("name = " + name + " price = " + price);
        this.price = price; // 문제 발생 코드
    }

    public int getPrice() {
        return price;
    }
}

void statefulServiceSingleton() {

        AnnotationConfigApplicationContext ac = new AnnotationConfigApplicationContext(TestConfig.class);
        StatefulService statefulService1 = ac.getBean(StatefulService.class);
        StatefulService statefulService2 = ac.getBean(StatefulService.class);

        // Thread-A : A 사용자 10000원 주문
        statefulService1.order("A", 10000); // 1)

        // Thread-B : B 사용자 20000원 주문
        statefulService2.order("B", 20000); // 2)

        // Thread-A : A 사용자 주문 금액 조회
        int price = statefulService1.getPrice();
        System.out.println("price = " + price); // 3)

    }
```
{% endraw %}

> ⚠️ StatefulService는 싱글톤이 적용된 스프링 컨테이너에서 관리하는 객체이다. StatefulService 에는 price라는 공유 필드가 존재함. 이럴 때 발생하는 문제!
>
> 1) statefulService1을 통해 10000원 주문 → price = 10000
> 2) statefulService2를 통해 20000원 주문 → price = 20000
> 3) statefulService1 에서 금액을 조회
>
> 3)에서 일반적으로 생각하면 10000 이 나올 것이라고 생각, 하지만 실제로는 공유 필드였던 price의 값을 2)에서 바꾸었기 때문에 20000이라는 결과가 나오는 참사 발생,,, 
> 위 경우가 특정 클라이언트가 필드의 값을 변경할 수 있도록 잘못 설계한 경우
> 결론 : 무상태 설계, 공유 필드 사용 주의.(쓰지 말자)

---

### 5. @Configuration

- AppConfig 클래스

{% raw %}
```java
@Configuration
public class AppConfig {

    @Bean
    public MemberService memberService() {
        return new MemberServiceImpl(memberRepository());
    }

    @Bean
    private static MemberRepository memberRepository() {
        return new MemoryMemberRepository();
    }

    @Bean
    public OrderService orderService() {
        return new OrderServiceImpl(memberRepository(), discountPolicy());
    }

    @Bean
    public DiscountPolicy discountPolicy() {
        return new RateDiscountPolicy(); 
    }

}
```
{% endraw %}

- @Bean memberRepository() 가 호출되는 횟수를 보면, 
    - @Bean memberService 

    - @Bean orderService 

    - 이렇게 총 두 번 호출된다. → new MemoryMemberRepository() 또한 두 번 호출 → 빈이 두개 생성되어 싱글톤이 깨지는 것처럼 보일 수 있다.

- 그렇다면 memberService 의 memberRepository와 orderService 의 memberRepository가 다른지 확인해 보자.

{% raw %}
```java
public class ConfigurationSingletonTest {

    @Test
    void configurationTest() {

        ApplicationContext ac = new AnnotationConfigApplicationContext(AppConfig.class);

        MemberServiceImpl memberService = ac.getBean("memberService", MemberServiceImpl.class);
        OrderServiceImpl orderService = ac.getBean("orderService", OrderServiceImpl.class);
        MemberRepository memberRepository = ac.getBean("memberRepository", MemberRepository.class);

        MemberRepository memberRepository1 = memberService.getMemberRepository();
        MemberRepository memberRepository2 = orderService.getMemberRepository();

        System.out.println("memberService -> memberRepository1 = " + memberRepository1); // 1)
        System.out.println("orderService -> memberRepository2 = " + memberRepository2); // 2)
        System.out.println("memberRepository = " + memberRepository); // 3)
        // 1,2,3은 모두 같은 memberRepository 를 가리킨다.

        assertThat(memberService.getMemberRepository()).isSameAs(memberRepository);
        assertThat(orderService.getMemberRepository()).isSameAs(memberRepository);

    }
}
```
{% endraw %}

> ⚠️ 음 ?
>
> ![image](/assets/images/fb15981aa0d544b38afd449928ce3124.png)

> ⚠️ **..? 왜 다른거 가리키니?
> 원래대로면 다 같은 걸 가리켜야 하고 **memberRepository는 한번만 호출되어야 한다.
> 근데 AppConfig를 찍어 보니 스프링 로그는 memberRepository를 한번만 호출하는 것처럼 보이는데 실제로는 세 번 호출함..
> ????????????
> 스프링 로그도 싱글톤 보장! 이라고 뜨는데 실제로는 보장 안되고 있다니까?
>
> → private static 붙어서 싱글톤 안된다
>

> 💡 @Configuration 을 사용하게 되면, 스프링에서 싱글톤을 보장해줌. @Configuration 이 붙은 클래스 내부의 @Bean으로 생성된 빈은 최초 생성된 이후 다시 부를 때 새로 생성하지 않도록 해 주는 것
> 관련 포스팅
> [https://mangkyu.tistory.com/234](https://mangkyu.tistory.com/234)

---

### 6. @Configuration 과 바이트코드 조작

> 📌 @Configuration 이 붙은 클래스는 빈으로 등록될 때 해당 클래스가 빈으로 올라가는 것이 아닌, 그 클래스를 상속받아 만든 임의의 클래스를 만들고,
> 스프링이 만든 클래스를 빈으로 등록한다.
> 그래서 빈.class를 조회해 보면 xxx..CGLIB 식의 이름으로 되어 있는 것.

{% raw %}
```java
    void configurationDeep() {

        ApplicationContext ac = new AnnotationConfigApplicationContext(AppConfig.class);

        AppConfig bean = ac.getBean(AppConfig.class);

        System.out.println("bean.getClass() = " + bean.getClass());
        // 결과 : bean.getClass() = class hello.core.AppConfig$$EnhancerBySpringCGLIB$$5881c3ba
    }
```
{% endraw %}

- AppConfig를 상속받은 어떤 클래스가 AppConfig 대신 빈으로 등록되고, 해당 클래스가 싱글톤을 보장하도록 해준다.
    - @Bean 이 붙은 메소드마다 이미 존재하는 빈을 호출하면 존재하는 빈을 반환

    - 빈이 없다면 생성해서 스프링 빈으로 등록 후 반환

    - → 싱글톤 보장(하나의 빈은 하나만 생성되도록)

> 참고: _스프링이 생성한 싱글톤 보장 클래스는 AppConfig를 상속받아 만들었으므로, AppConfig.class로 조회가 가능하다.  
> _참고:_ __**AnnotationConfigApplicationContext 에 넘긴 클래스는 스프링 빈으로 등록된다.**_

> 정리:
