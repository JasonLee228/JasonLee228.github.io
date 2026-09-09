---
title: "스프링 MVC 3. 서블릿, JSP, MVC 패턴"
date: 2023-03-21 13:35:08 +0000
categories: ["Spring", "MVC"]
tags: ["mvc", "spring"]
permalink: /posts/saction-3-서블릿-jsp-mvc-패턴/
---

#### 회원 관리 기능 - 요구사항

- 회원 정보
    - 이름 : username

    - 나이 : age

- 기능 요구사항
    - 회원 저장

    - 회원 목록 조회

#### 회원 도메인, Repository

{% raw %}
```java
@Getter
@Setter
public class Member {

    private Long id;
    private String username;
    private int age;

    public Member() {
    }

    public Member(String username, int age) {
        this.username = username;
        this.age = age;
    }
}
```
{% endraw %}

{% raw %}
```java
public class MemberRepository {

    private static Map<Long, Member> store = new HashMap<>();
    private static Long sequence = 0L;

    private static final MemberRepository instance = new MemberRepository();

    public static MemberRepository getInstance() {
        return instance;
    }

    private MemberRepository() {
    }

    public Member save(Member member) {
        member.setId(++sequence);
        store.put(member.getId(), member);
        return member;
    }

    public Member findById(Long id) {
        return store.get(id);
    }

    public List<Member> findAll() {
        return new ArrayList<>(store.values());
    }

    public void clearStore() {
        store.clear();
    }
}
```
{% endraw %}

> 주의! HashMap 은 동시성 제어에 대한 고려를 하지 않는다.  
> 실제 동시성 등이 보장되어야 하는 상황에서는 멀티스레드 환경을 고려한 클래스인 `ConcurrentHashMap`_ 이나_`AtomicLong`_ 을 사용해야 한다._

- `ConcurrentHashMap`_ :  _`ConcurrentHashMap` 클래스는 해시 테이블 기반의 Map 인터페이스 구현체입니다.  `HashMap`과 유사하지만, 멀티스레드 환경에서 안전하게 사용할 수 있습니다.  `ConcurrentHashMap`은 내부적으로 분할 락을 사용하여 동시에 여러 스레드가 맵에 접근해도 안전하게 동작합니다. 이를 통해 멀티스레드 환경에서 안전하게 맵을 사용할 수 있습니다

- `AtomicLong`_ :  _`AtomicLong` 클래스는 원자적인 연산을 지원하는 `long` 타입 변수입니다.  `AtomicLong` 변수는 여러 스레드가 동시에 접근해도 안전하게 값을 읽고 쓸 수 있습니다.  `AtomicLong`은 `long` 타입 변수에 대해 원자적인 `get()`, `set()`, `incrementAndGet()`, `getAndIncrement()`, `decrementAndGet()`, `getAndDecrement()` 등의 연산을 제공합니다.  이를 통해 멀티스레드 환경에서 안전하게 `long` 타입 변수를 사용할 수 있습니다.

---

#### 서블릿으로 회원 관리 웹 애플리케이션 만들기

- 서블릿을 통해 회원 등록 HTML 폼 제공

{% raw %}
```java
@WebServlet(name = "memberFormServlet", urlPatterns = "/servlet/members/new-form")
public class MemberFormServlet extends HttpServlet {

    private MemberRepository memberRepository = MemberRepository.getInstance();

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse res) throws ServletException, IOException {

        res.setContentType("text/html");
        res.setCharacterEncoding("utf-8");

        PrintWriter w = res.getWriter();
        w.write("<!DOCTYPE html>\n" +
                "<html>\n" +
                "<head>\n" +
                "   <meta charset=\"UTF-8\">\n" +
                "   <title>Title</title>\n" +
                "</head>\n" +
                "<body>\n" +
                "<form action=\"/servlet/members/save\" method=\"post\">\n" +
                "   username: <input type=\"text\" name=\"username\" />\n" +
                "   age:      <input type=\"text\" name=\"age\" />\n" +
                "   <button type=\"submit\">전송</button>\n" +
                "</form>\n" +
                "</body>\n" +
                "</html>\n");
    }
}
```
{% endraw %}

결과

![image](/assets/images/672cf0fda3634841bf53a87912f7bf2f.png)

- 전송 버튼 클릭 시 /servlet/members/save 경로로 post 요청을 하도록 했다.

- 서블릿을 통해 회원 저장, 저장된 회원의 정보를 볼 수 있는 HTML 반환하기

{% raw %}
```java
@WebServlet(name = "memberSaveServlet", urlPatterns = "/servlet/members/save")
public class MemberSaveServlet extends HttpServlet {

    private MemberRepository memberRepository = MemberRepository.getInstance();

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse res) throws ServletException, IOException {

        System.out.println("MemberSaveServlet.service");
        String username = req.getParameter("username");
        int age = Integer.parseInt(req.getParameter("age"));

        Member member = new Member(username, age);
        memberRepository.save(member);

        res.setContentType("text/html");
        res.setCharacterEncoding("utf-8");

        PrintWriter w = res.getWriter();
        // 동적으로 코드에서 html 값을 변화시키는 것을 볼 수 있다.
        w.write("<html>\n" +
                "<head>\n" +
                " <meta charset=\"UTF-8\">\n" +
                "</head>\n" +
                "<body>\n" +
                "성공\n" +
                "<ul>\n" +
                " <li>id="+member.getId()+"</li>\n" +
                " <li>username="+member.getUsername()+"</li>\n" +
                " <li>age="+member.getAge()+"</li>\n" +
                "</ul>\n" +
                "<a href=\"/index.html\">메인</a>\n" +
                "</body>\n" +
                "</html>");
    }
}
```
{% endraw %}

> 💡 `request.getParameter()` 의 결과는 항상 문자이다.
> 때문에 코드에서도 `Interger.parseInt()` 메소드 이용하여 형 변환.

---

> 💡 JSP 는 내부적으로 서블릿으로 변환된다.

#### JSP 로 변환하기

- 저장 폼의 jsp 화

{% raw %}
```java
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<html>
<head>
    <title>Title</title>
</head>
<body>
<form action="/jsp/members/save.jsp" method="post">
    username: <input type="text" name="username" />
    age: <input type="text" name="age" />
    <button type="submit">전송</button>
</form>
</body>
</html>
```
{% endraw %}

- 저장 기능

{% raw %}
```java
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ page import="hello.servlet.domain.member.Member" %>
<%@ page import="hello.servlet.domain.member.MemberRepository" %>
<%
    // request, response 는 그냥 사용할 수 있도록 지원됨.
    MemberRepository memberRepository = MemberRepository.getInstance();

    System.out.println("MemberSaveServlet.service");
    String username = request.getParameter("username");
    int age = Integer.parseInt(request.getParameter("age"));

    Member member = new Member(username, age);
    memberRepository.save(member);

%>
<html>
<head>
    <title>Title</title>
</head>
<body>
성공
<ul>
    <li>id=<%=member.getId()%></li>
    <li>username=<%=member.getUsername()%></li>
    <li>age=<%=member.getAge()%></li>
</ul>
<a href="/index.html">메인</a>
</body>
</html>
```
{% endraw %}

- 목록

{% raw %}
```java
<%@ page import="java.util.List" %>
<%@ page import="hello.servlet.domain.member.MemberRepository" %>
<%@ page import="hello.servlet.domain.member.Member" %>
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%
  MemberRepository memberRepository = MemberRepository.getInstance();
  List<Member> members = memberRepository.findAll();
%>
<html>
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
<a href="/index.html">메인</a>
<table>
    <thead>
    <th>id</th>
    <th>username</th>
    <th>age</th>
    </thead>
    <tbody>
    <%
        for (Member member : members) {
          out.write("   <tr>");
          out.write("   <td>" + member.getId() + "</td>");
          out.write("   <td>" + member.getUsername() + "</td>");
          out.write("   <td>" + member.getAge() + "</td>");
          out.write("   </tr>");
        }
    %>
    </tbody>
</table>
</body>
</html>
```
{% endraw %}

- JSP =Java Servlet Page

- JSP 특징
    - JSP는 자바 코드를 그대로 다 사용할 수 있다.
          - <%@ page import="hello.servlet.domain.member.MemberRepository" %> → 자바의 import 문과 같다.

    - <% ~~ %> 이 부분에는 자바 코드를 입력할 수 있다.

    - <%= ~~ %> 이 부분에는 자바 코드를 출력할 수 있다.

- JSP 장점
    - 뷰를 생성하는 HTML 작업을 깔끔하게 가져가고, 중간중간 동적으로 변경이 필요한 부분에만 자바 코드를 적용

- 단점
    - JSP 에 비즈니스 로직이 너무 많이 포함됨. 

    - 코드를 잘 보면, JAVA 코드, 데이터를 조회하는 리포지토리 등등 다양한 코드가 모두 JSP에 노출되어 있다.

- MVC 패턴의 필요, 등장
    - 비즈니스 로직은 서블릿 과 같은 다른곳에서 처리하고,  JSP는 목적에 맞게 HTML로 화면(View)을 그리는 일에 집중

  ---

#### MVC 패턴 - 작성

- MVC = Model / View / Controller
    - 컨트롤러: HTTP 요청을 받아서 파라미터를 검증하고, 비즈니스 로직을 실행한다.  그리고 뷰에 전달할 결과 데이터를 조회해서 모델에 담는다.

    - 모델: 뷰에 출력할 데이터를 담아둔다.  뷰가 필요한 데이터를 모두 모델에 담아서 전달해주는 덕분에 뷰는 비즈니스 로직이나 데이터 접근을 몰라도 되고, 화면을 렌더링 하는 일에 집중할 수 있다.

    - 뷰: 모델에 담겨있는 데이터를 사용해서 화면을 그리는 일에 집중한다.  여기서는 HTML을 생성하는 부분을 말한다.

  ![image](/assets/images/58144a31e2d24aafadd0ba52faeb65cb.png)

- 구현

1. 회원 등록 Form 

-  Servlet

{% raw %}
```java
/**
 * /servlet-mvc/members/new-form 경로로 호출하면 servlet 을 먼저 타고,
 * servlet 에서는 viewPath 를 호출한다. (서버 내부 호출)
 * WEB-INF 하위에 있는 JSP 는 외부에서 직접 호출 할 수 없다. -> forward 를 거쳐야 함
 */
@WebServlet(name = "mvcMemberFormServlet", urlPatterns = "/servlet-mvc/members/new-form")
public class MvcMemberFormServlet extends HttpServlet {

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse res) throws ServletException, IOException {
        String viewPath = "/WEB-INF/views/new-form.jsp"; // jsp 경로
        RequestDispatcher dispatcher = req.getRequestDispatcher(viewPath);
        // 선언한 경로 호출 - 다른 서블릿이나 JSP 로 이동할 수 있는 기능
        // * 서버 내부 호출, redirect 가 아니기 때문에 client 는 알 수 없음.
        dispatcher.forward(req, res);
    }
}
```
{% endraw %}

- JSP

{% raw %}
```html
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<html>
<head>
  <meta charset="UTF-8">
  <title>Title</title>
</head>
<body>
<!-- 상대경로 사용, [현재 URL이 속한 계층 경로 + /save] -->
<%--여기서 form의 action을 보면 절대 경로( / 로 시작)가 아니라 상대경로( / 로 시작X)인 것을 확인할 수 있다.
    이렇게 상대경로를 사용하면 폼 전송시 현재 URL이 속한 계층 경로 + save가 호출된다.
    현재 계층 경로: /servlet-mvc/members/
    결과: /servlet-mvc/members/save--%>
<form action="save" method="post">
  username: <input type="text" name="username" />
  age: <input type="text" name="age" />
  <button type="submit">전송</button>
</form>
</body>
</html>
```
{% endraw %}

1. 회원 저장

- Servlet

{% raw %}
```java
@WebServlet(name = "mvcMemberSaveServlet", urlPatterns = "/servlet-mvc/members/save")
public class MvcMemberSaveServlet extends HttpServlet {

    private MemberRepository memberRepository = MemberRepository.getInstance();

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse res) throws ServletException, IOException {

        String username = req.getParameter("username");
        int age = Integer.parseInt(req.getParameter("age"));// request.getParameter() 의 결과는 항상 문자이다.

        Member member = new Member(username, age);
        memberRepository.save(member);

        // Model 에 data 보관
        req.setAttribute("member", member);

        String viewPath = "/WEB-INF/views/save-result.jsp";
        RequestDispatcher dispatcher = req.getRequestDispatcher(viewPath);
        dispatcher.forward(req, res);

    }
}
```
{% endraw %}

- JSP

{% raw %}
```html
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<html>
<head>
  <title>Title</title>
</head>
<body>
성공
<ul>
<%-- 프로퍼티 접근법을 통해 필요한 값 얻어오기 --%>
  <li>id=${member.id}</li>
  <li>username=${member.username}</li>
  <li>age=${member.age}</li>
</ul>
<a href="/index.html">메인</a>
</body>
</html>
```
{% endraw %}

1. 회원 목록

- Servlet

{% raw %}
```java
@WebServlet(name = "mvcMemberListServlet", urlPatterns = "/servlet-mvc/members")
public class MvcMemberListServlet extends HttpServlet {

    private MemberRepository memberRepository = MemberRepository.getInstance();

    @Override
    protected void service(HttpServletRequest req, HttpServletResponse res) throws ServletException, IOException {

        List<Member> members = memberRepository.findAll();

        req.setAttribute("members", members);

        String viewPath = "/WEB-INF/views/members.jsp";
        RequestDispatcher dispatcher = req.getRequestDispatcher(viewPath);
        dispatcher.forward(req, res);

    }
}
```
{% endraw %}

- JSP

{% raw %}
```html
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core"%>
<html>
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
<a href="/index.html">메인</a>
<table>
    <thead>
    <th>id</th>
    <th>username</th>
    <th>age</th>
    </thead>
    <tbody>
    <%--  jsp 에서 편하게 attribute 를 가져올 수 있도록 지원. (jstl)  기존 members.jsp 의 for 문 대체  --%>
    <c:forEach var="item" items="${members}">
        <tr>
            <td>${item.id}</td>
            <td>${item.username}</td>
            <td>${item.age}</td>
        </tr>
    </c:forEach>
    </tbody>
</table>
</body>
</html>
```
{% endraw %}

#### MVC 패턴 - 한계

- 공통 처리가 어렵다 → 중복이 많다.

> 해결 방법 : 컨트롤러 호출 전에 공통 기능을 처리해야 한다.   
> → _프론트 컨트롤러 (Front Controller)_ 패턴의 도입
