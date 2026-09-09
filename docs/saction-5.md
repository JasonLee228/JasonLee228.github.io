---
title: "saction 5"
grand_parent: "Spring-Boot"
parent: "[inflearn] 스프링 MVC 1편"
nav_order: 5
permalink: "/notes/saction-5/"
---

[5. 스프링 MVC - 구조 이해.pdf](https://s3-us-west-2.amazonaws.com/secure.notion-static.com/4209c4b8-91d5-4537-80cc-9631fd50cefa/5._%EC%8A%A4%ED%94%84%EB%A7%81_MVC_-_%EA%B5%AC%EC%A1%B0_%EC%9D%B4%ED%95%B4.pdf)

#### 스프링 부트의 DispacherServlet 상속 구조

- HttpServlet 이 결국 포함되어 있다.

![image](/assets/images/db5f9fd25f95420ea0e3bfe3722e68a2.png)

> 💡 스프링을 사용함에도 우리가 직접 만든 서블렛이 동작하는 이유는, 
> 서블렛의 우선순위는 더 상세한 URL 경로가 더 높기 때문이다.

> 💡 FrontController = DispatcherServlet
> handlerMappingMap = HandlerMapping
> MyHandlerAdapter = HandlerAdapter
> ModelView = ModelAndView
> viewResolver = ViewResolver
> MyView = View

![image](/assets/images/c07613914f704dbbb9afe75b8ba09cbc.png)

---

---

- 23.05.31

### 스프링 MVC 사용하기

#### RequestMapping 어노테이션

- RequestMappingHandlerMapping

- RequestMappingHandlerAdapter

> 위 두 가지 어댑터, 매핑정보를 스프링에서 이용할 수 있게 해준다.  
> `@RequestMapping` 어노테이션의 핸들러 매핑과 핸들러 스프링에서 어댑터는 가장 우선순위가 높다.

---

#### 기존 코드 변경하기

1. 등록 폼

{% raw %}
```java
@Controller
public class SpringMemberFormControllerV1 {

    // 요청 정보 매핑
    @RequestMapping("/springmvc/v1/members/mew-form")
    public ModelAndView process(){

        // view 반환
        return new ModelAndView("new-form");

    }
}
```
{% endraw %}

1. 회원 저장

{% raw %}
```java
@Controller
public class SpringMemberSaveControllerV1 {

    MemberRepository memberRepository = MemberRepository.getInstance();

    @RequestMapping("springmvc/v1/members/save")
    public ModelAndView process(HttpServletRequest request, HttpServletResponse response) {
        String username = request.getParameter("username");
        int age = Integer.parseInt(request.getParameter("age"));

        Member member = new Member(username, age);
        memberRepository.save(member);

        ModelAndView modelAndView = new ModelAndView("save-result");
        modelAndView.addObject("member", member);

        return modelAndView;
    }
}
```
{% endraw %}

1. 회원 목록

{% raw %}
```java
@Controller
public class SpringMemberListControllerV1 {


    MemberRepository memberRepository = MemberRepository.getInstance();

    @RequestMapping("/springmvc/v1/members")
    public ModelAndView process() {

        List<Member> members = memberRepository.findAll();
        ModelAndView modelAndView = new ModelAndView("members");

        modelAndView.addObject("members", members);

        return modelAndView;
    }
}
```
{% endraw %}

> 💡 `@Controller`어노테이션이 붙어 있다면 아래2의 역할을 수행한다.
> 1.컴포넌트 스캔의 대상이 되어 빈으로 자동 등록
> 2. `RequestMappingHandlerMapping`에서 컨트롤러로 인식하여 매핑 정보를 수행한다.
> → 스프링 빈 중에서 `@RequestMapping` | `@Controller`가 **클래스 레벨**에 붙어 있는 경우에 매핑정보로 인식
> → 스프링에서 어노테이션 기반 컨트롤러로 인식

> 💡 @Controller 과 @RequestMapping 어노테이션 모두 RequestMappingHandlerMapping 의 인식 대상이기 때문에 클래스 레벨에 아래와 같이 선언하면 동일하게 동작한다.

{% raw %}
```java
@Controller
public class ...

@Component
@RequestMapping
public class ...
```
{% endraw %}

> 🚫 Spring boot 3.0 이후부터는 동작 방식이 변경되어 @RequestMapping 이 클래스 레벨에 붙었다고 스프링 컨트롤러로 인식하지 않는다. 오로지 @Controller 만 인식.

---

### 컨트롤러 통합

<details markdown="1"><summary>코드</summary>



</details>

> 💡 기존의 세 클래스로 나뉘어 있던 컨트롤러들을 통합하였고, 중복을 제거할 수 있었다.
> 클래스 레벨에서 `@RequestMapping(”/springmvc/v2/members”)` 를 선언하여 중복되는 url 을 보기 좋게 하나로 통합했다!

### 실용적인 방식으로의 변경

- 스프링에서도 ModelAndView 가 아닌 view의 논리 이름을 반환해도 된다.

- Http Method 가 없었던 지금까지의 방식과 달리 HttpMethod 를 사용하도록 변경한다.
    - 실무에서는 거의 이런 방식으로 사용한다고 보면 된다.

{% raw %}
```java
@Controller
@RequestMapping("/springmvc/v3/members")
public class SpringMemberControllerV3 {

    private MemberRepository memberRepository = MemberRepository.getInstance();

//    @RequestMapping(value = "/mew-form", method = RequestMethod.GET)
    @GetMapping("/mew-form")
    public String newForm(){

        // view 반환
        return "new-form";

    }

//    @RequestMapping(value = "/save", method = RequestMethod.POST)
    @PostMapping("/save")
    public String save(
            @RequestParam("username") String username,
            @RequestParam("age") int age,
            Model model) {

        Member member = new Member(username, age);
        memberRepository.save(member);

        model.addAttribute("member", member);
        
        return "save-result";
    }

//    @RequestMapping(method = RequestMethod.GET)
    @GetMapping
    public String members(Model model) {
        
        List<Member> members = memberRepository.findAll();

        model.addAttribute("members", members);
        
        return "members";
    }

}
```
{% endraw %}
