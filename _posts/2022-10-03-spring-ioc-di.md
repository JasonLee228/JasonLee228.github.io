---
title: "[Spring] IOC? DI?"
date: 2022-10-03 15:50:41 +0000
categories: ["Spring-Boot"]
---

## 1. IoC?

> 💡 IoC란 Inversion of Control의 줄임말이다. 의존성 역전이라고도 하는데, 스프링에서는 의존성의 제어권을 코드에서 갖는 것이 아닌, 스프링 컨테이너에게 양도한다. 때문에 의존성의 역전이라고 하는 것.
>
> 따라서, 스프링 컨테이너를 IoC 컨테이너라고도 부른다.

ioc 사용의 이유? → 불편함에서 나온 개념!

직접 무언가(객체)를 코드에서 만들고, 해제하는 것 자체가 사용자 및 개발자에게, 그리고 메모리에게도 부담을 주는 행위 그 자체임. 불필요한 리소스의 최소화 → 속도 증가!

#### 스프링 컨테이너의 종류

IoC 컨테이너 또는 DI 컨테이너라고 한다. 요새는 DI컨테이너라는 말을 사용하는 추세.

객체(인스턴스를) 관리하는 하나의 컨테이너 역할을 하기 때문에 스프링 ‘컨테이너’ 라는 말이 된 것 같다.

- BeanFactory

- ApplicationContext

> 💡 위 두가지가 스프링의 빈(Bean) 을 관리해주는 주체이다.
>
> ApplicationContext는 근데 BeanFactory를 상속받고 있기 때문에 사실상 본 주체는 BeanFactory.  
>   
> 우리가 스프링을 사용할 때의 실제 관리 주체는 ApplicationContext이다.  
> ApplicationContext는 빈 팩토리 말고도 다른 여러가지를 상속받고 있는 인터페이스이기에, 더 다양한 일들을 하고 있다.

참고)

[ApplicationContext (Spring Framework 5.3.23 API)](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/ApplicationContext.html)

> 💡 위는 스프링 공식 Docs인데, 
> 안의 내용에는 다음과 같이 Spring ApplicationContext에 대한 간략한 설명을 하고 있다.
>
>
> An ApplicationContext provides:
>
> - [ ] Bean factory methods for accessing application components. Inherited from ListableBeanFactory. The ability to load file resources in a generic fashion. Inherited from the ResourceLoader interface.
>
> - [ ] The ability to publish events to registered listeners. Inherited from the ApplicationEventPublisher interface.
>
> - [ ] The ability to resolve messages, supporting internationalization. Inherited from the MessageSource interface.
>
> - [ ] Inheritance from a parent context. Definitions in a descendant context will always take priority. This means, for example, that a single parent context can be used by an entire web application, while each servlet has its own child context that is independent of that of any other servlet.
>
> - [ ] In addition to standard BeanFactory lifecycle capabilities, ApplicationContext implementations detect and invoke ApplicationContextAware beans as well as ResourceLoaderAware, ApplicationEventPublisherAware and MessageSourceAware beans.
>
> 요약하면, ApplicationContext는 스프링의 어플리케이션에 대한 구성을 제공하는 중앙 인터페이스이다.  
> 빈, 파일 리소스, 여러 이벤트 리스너, 메시지 등을 관리하는 중앙 제어장치라고 봐도 됨.  
> 여기서 우리가 중요하게 봐야 할 것은 이 인터페이스에서는 Bean을 관리하는 기능 뿐 아니라 감지, 호출하는 기능을 모두 포함하고 있다는 것.  
> →  빈(Bean)을 만들고, 엮어주며, 제공해준다.

- 그럼 모든 클래스가 다 빈으로 등록되는가? →  아니다.

> 💡 인텔리제이에서는 어떤 클래스가 Bean 으로 등록되는지 쉽게 알 수 있는데, 클래스명 옆에 빈 모양 아이콘이 있다면 빈으로 등록되는 클래스라는 것
> 특정 클래스(인터페이스)를 상속하거나, 어노테이션(ex. @controller)을 적용하거나, 
> @Bean anotation 을 사용하여 주입해주는 방법으로 빈으로 등록할 수 있다.
> IoC컨테이너에서는 이렇게 등록된 Bean들 간의 의존성 주입을 도와주게 된다.

#### Ex)

{% raw %}
```java
// 1
public testController(TestRepository testRepository){
	this.repository = testRepository;
}

// 2
private final ApplicationContext applicationContext;

	public testController(ApplicationContext applicationContext) {
		this.applicationContext = applicationContext;
	}

	TestRepotiroty testRepository = applicationContext.getBean(TestRepotiroty.class);
```
{% endraw %}

> 💡 1. 과 같이 컨트롤러에 이러한 생성자가 있을 때, testRepository라는 빈을 스프링 IoC컨테이너에서 찾아서 주입해주는 것이다.
>
> 이 때, 가장 중요한 것! 
> 의존성 주입은 "Bean" 끼리만 가능하다. IoC컨테이너에 등록되어 있는 빈들 끼리만 서로 의존성 주입을 할 수 있는 것.
>
> 물론 다른 방법으로 가져와서 사용할 수도 있다. 그것이 바로 2. 의 예제.
> ApplicationContext에 등록되어 있는 빈의 객체명을 통해 직접 가져와서 주입해주는 방법을 사용했다. 물론, 이런 방법은 거의 사용하지 않는다고 봐도 된다.
>

> 💡 그렇다면 1, 2의 두 TestRepository는 다른 인스턴스일까 ? → 아니다.
>
>
> 둘 다 ApplicationContext에 등록되어 있는 하나의 빈을 가져와서 사용하는 것이기 때문에 그렇고,  
> 이를 싱글톤 패턴이라고 한다.
>
> # 싱글톤 패턴 : 디자인 패턴의 한 종류. 싱글톤(Singleton) 패턴의 정의는 단순하다. 객체의 인스턴스가 오직 1개만 생성되는 패턴을 의미한다.

## 2. Bean?

- 위에서 계속 얘기하는 'Bean'은 그럼 도대체 무엇인가?

- Bean : 스프링 Ioc 컨테이너가 관리하는 객체, Ioc컨테이너에 등록된 객체 -> ApplicationContext가 알고 있는 객체

> 💡 스프링의 Bean은 빈으로 등록시키거나, 등록된 인스턴스에 한하여 관리된다.
> 이 말은, 다음과 같이 생성된 인스턴스는 빈이 아니라는 얘기다.

{% raw %}
```java
TestRepository testRepository = new TestRepository();
```
{% endraw %}

#### 2-1. Bean 등록 방법

> 💡 **1.컴포넌트 스캐닝(components scanning) : @component 어노테이션이 붙어 있는 객체 주입**
>
> * 라이프사이클 콜백 : 어노테이션 프로세서 중, 스프링 ioc 컨테이너가 사용하는, ioc 컨테이너를 만들고 그 안에 빈을 등록하는 데에 사용하는 여러가지 인터페이스가 있는데, 그런 인터페이스들을 말하는 것.
>
> 이런 라이프사이클 콜백 중에, 컴포넌트 어노테이션이 붙어 있는 모든 클래스를 찾아서 인스턴스를 생성하고, 등록해주는 역할을 하는 어노테이션 처리기가 스프링에 갖춰져 있다.
>
>
>  @SpringBootApplication 어노테이션 내부에 보면, @ComponentScan 어노테이션이 붙어있고,  
> 해당 어노테이션에는 컴포넌트 스캔 범위를 지정하고 있다.   
> 이에 따르면, @SpringBootApplication이 붙은(더 정확히 말하면 @ComponentScan이 붙은)   
> 메인 클래스가 있는 패키지 위치부터, 하위의 모든 패키지를 다 스캔하여   
> @Component라는 어노테이션이 붙은 클래스들을 찾아서 빈으로 등록해 준다.  
>   
> * @Component 어노테이션을 받고 있는 어노테이션들  
> - @Controller, @RestController, @Service, @Repository, @Configuration, ....  
> 위 어노테이션을 붙인 클래스는 우리가 직접 빈으로 올려주지 않아도, 어플리케이션이 실행되는 시점에 컴포넌트 스캔을 통해 스프링이 알아서 빈으로 등록해주는 것.  
> 이것이 컴포넌트 스캔을 통한 빈 등록 방법이다.

> 💡 **2. JPA?**
>
> JPA Repository 같은 경우는 좀 다르다. 
> JPA를 사용하는 리포지토리의 경우 특정 인터페이스를 상속받아서 사용하고 있는데, 이 특정 인터페이스 또는 클래스를 상속받고 있는 클래스(인터페이스)를 찾아서, 구현체를 만들고, 빈으로 직접 JPA에서 등록해 준다.(굉장히 복잡..)

> 💡 **3. 직접 주입(@Configuration 이 붙은 클래스를 사용하는 방법(자바 설정 파일))
>
> **이는 코드를 통해 보면 더 이해가 쉬울 것이다.

{% raw %}
```java
@Configuration
				public class testConfig {
				
					@Bean
					public TestController testController() {
						return new TestController();
					}
				}
```
{% endraw %}

> 💡 위와 같은 형식으로 설정 클래스를 별도로 만들고, 해당 클래스 내에 @Bean 어노테이션을 사용하여 클래스를 정의해 두면, 스프링이 작동하면서 해당 클래스를 빈으로 올려주게 된다. 
>
> 이렇게 설정 파일로 선언해둔 클래스에는 따로 @Component 어노테이션이 필요 없어지게 되는 것.
>
> 원리는, @Configuration 어노테이션도 @Component 어노테이션을 사용하고 있고, 그렇게 올라간 설정 파일 내에 @Bean을 이용하여 선언된 파일을 자동으로 읽어주는 것이다.

#### 2-2. 의존성 주입 방법

- 의존성 주입에 대해서는 아래 DI 에서 더 자세하게 다룰 것인데, 그 전에 어떤 의존성 주입 방법이 있는지 간단하게 파악하는 용도로만 보기 바란다.

{% raw %}
```java
@Autowired 어노테이션 사용 : 클래스에서 생성자로 주입받는 방법이 아닌, 
@Autowired 어노테이션을 통해서 주입받아 사용할 수 있다.
		1. 생성자 주입 방법
		
			private final TestRepository testRepository;

			public TestController(TestRepository testRepository) {
				this.testRepository = testRepository;
			}
		
		2. @Autowired 어노테이션을 통해서 주입받는 방법
		
			@Autowired
			private TestRepository testRepository2;
```
{% endraw %}

## 3. DI (Dependency Injection)

- DI란 Dependency Injection의 약어로, 번역하면 의존성을 주입한다는 말이다. 말 그대로 객체를 직접 생성하는 것이 아니라 외부에서 생성한 후 주입을 시켜주는 방식을 말한다.

- 일반적으로 단순 자바 또는 객체지향 프로젝트에서 객제 의존성에 대한 제어권은 객체 자신이 갖는다.

{% raw %}
```java
Ex)
		class test {
			private TestController testController = new TestController();
		}
```
{% endraw %}

> 💡 하지만, 스프링에 빈으로 등록된 인스턴스들은 각각의 클래스에서 new 생성자를 통해서 생성해서 사용하는 것이 아님. 
>
> 스프링에 빈으로 등록되어 있는 각각의 객체들이 있을 것이고, 각각의 사용 방법을 통해서 스프링에서 의존성 주입을 통해 주입받아서 사용하는 방식이다.
>
> 이 말인 즉, 객체 생성의 주도권, 객체 의존성의 제어권은 각 클래스에서 갖고 있는 것이 아니라 스프링이 갖고 있다는 말이다.
>
> 결국 스프링의 ApplicationContext, IoC컨테이너가 의존성 주입의 주체가 되는 것이다. 이를 스프링의 DI, 의존성 주입이라고 한다.
>
> {% raw %}
> ```text
> 스프링의 의존성 주입에서 가장 중요한 것은, 주입받는 대상 인스턴스는 "무조건" 빈으로 등록이 되어 있어야 한다는 것.
> 빈으로 등록되지 않은 객체를 주입받으려 하면 무조건 오류오류
> NosuchBeanDefinitionException: Noqualifying bean of type ~~~~
> ->  ~~~~ 타입의 빈이 등록되지 않았는데 너가 주입받으려 해서 오류다 라고 뜹니다.
> ```
> {% endraw %}

#### @Autowired 어노테이션을 붙일 수 있는 곳은 많다. 

- 클래스의 생성자에도, Get / Setter에도, 필드 자체에도 붙일 수 있다.

- 생성자 주입 시, 기존에는 생성자에도 @Autowired 어노테이션을 붙였지만, 스프링 4.3버전부터 나온 새로운 기능으로 어떤 클래스에 생성자가 하나뿐이고, 해당 생성자에서 주입받는 클래스들이 빈으로 등록되어 있다면 생성자에 어노테이션을 생략해도 되도록 기능이 개선되었다.

#### 3.1 의존성 주입 방법

1. 생성자 주입(final 붙여 사용)

{% raw %}
```java
1. private final TestRepository testRepository;
    
		// @Autowired 생략
    public TestController(TestRepository testRepository) {
    this.testRepository = testRepository;
    }
```
{% endraw %}

1. Setter 주입(final 붙일 수 없음)

{% raw %}
```java
private TestRepository testRepository2;

    @Autowired
    public void setRepository(TestRepository testRepository2) {
        this.testRepository2 = testRepository2;
    }
```
{% endraw %}

1. 필드 주입(final 붙일 수 없음)

{% raw %}
```java
@Autowired
private TestRepository testRepository2;
```
{% endraw %}

> 💡 스프링프레임워크 레퍼런스에서 권장하고 있는 의존성 주입 방법은 생성자로 주입받는 방법이다.
>
> 생성자로 주입받는 방법이 좋은 이유는, 의존성 주입을 통해서 인스턴스를 띄워야 하는 특정 클래스가 있다고 할 때, 필수적으로 사용해야 하는 레퍼런스(주입받아야 할 객체) 가 없이는 해당 인스턴스를 생성조차 할 수 없게 강제할 수 있기 때문이다.
>
> 예를 들어, 다음과 같은 Test 라는 클래스가 있다고 해보자.

{% raw %}
```java
public class Test {	
		private final TestRepository testRepository;

		public TestController(TestRepository testRepository) {
			this.testRepository = testRepository;
		}
	}
```
{% endraw %}

  


> 💡 이 클래스에서는, TestRepository가 없이는 생성되지 못 하도록 강제할 수 있다는 말이다. 
>
> class 입장에서 TestRepository는 반드시 있어야 하는 필수 레퍼런스이기 때문.
>
> field Injection이나 Setter Injection에서는 참조해야 하는(의존성 주입을 받아야 하는) 인스턴스가 없을 때에도 일단 클래스 자체는 생성이 될 수도 있기 때문에 오류 발생의 여지가 충분하다. 그래서 생성자를 통한 Dependency Injection이 가장 좋은 수단이라고 말할 수 있다.
>
>
> 그럼에도 불구하고 다른 의존성 주입 방법이 존재하는 이유는, 순환 참조 오류 때문이다.  
>   
> A, B 두 클래스가 있을 때, A 클래스는 B 클래스를, B클래스는 A클래스를 참조할 때 서로가 서로를 참조하는 '상호 참조' 때문에 순환 참조 오류로 인해서 인스턴스 생성이 불가하다.   
> 이러한 경우에는 field Injection / Setter Injection을 사용하여 일단 인스턴스를 띄운 뒤에 서로가 서로를 참조할 수 있게 해주는 방법으로 해소시킬 수 있다.   
> 이것이 바로 다른 의존성 주입의 존재 이유이기도 하다.  
>
>
> 그래도 가장 안정적인 Dependency Injection은 생성자이기 때문에,   
> 가급적이면 circular dependency(상호 참조)가 발생하지 않게끔 개발하는 것이 좋다.
