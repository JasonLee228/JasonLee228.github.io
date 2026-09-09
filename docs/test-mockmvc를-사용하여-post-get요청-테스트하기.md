---
title: "[Test] MockMvc를 사용하여 POST, GET요청 테스트하기"
parent: "Spring-Boot"
nav_order: 3
permalink: "/notes/test-mockmvc를-사용하여-post-get요청-테스트하기/"
---

#### 1. MockMvc 란?

컨트롤러를 테스트 하는 경우, 동작 만을 확인할 것이라면 `@Mock`, `@InjectMocks`을 사용하면 되지만  
해당 방법으로는 실제로 Tomcat 서버를 구동하여 요청이 정상적으로 처리 되는지는 확인할 수 없다.

그래서 나타나게 된 것이 MockMvc!

> MockMvc는 서버를 직접 구동하여 웹 어플리케이션을 애플리케이션 서버에서 구동하여 직접 테스트하는 것이 아닌,  테스트용 MVC환경을 만들어 Http요청 등의 기능을 제공해주는 유틸리티 클래스이다.

> 풀어서 이야기하자면, MockMvc는 서블릿 컨테이너를 Mocking하여, 톰캣 서버와는 상관 없는 모형 서블렛 컨테이너를 메모리에 올려 구동할 수 있도록 만들어주는 것이고, 모든 웹 요청에 대하여 테스트용으로 시뮬레이션 할 수 있도록 해주는 Helper 클래스라고 할 수 있다.

#### 2. MockMvc 테스트의 종류

- @WebMvcTest

- @AutoConfigureMockMvc

@WebMvcTest는 @Controller, @RestController 어노테이션이 붙은 클래스들을 찾아서 메모리에 올린다.

@AutoConfigureMockMvc 는 위에 더해서, 컨트롤러뿐만 아니라 @Service, @Repository가 분은 객체들도 모두 메모리에 올린다는 점이다. 즉, 컨트롤러만 테스트할 때는 @WebMvcTest를 이외에 컴포넌트들도 테스트하려면 @AutoConfigureMockMvc를 사용하도록 하면 될 것 같다.

<details markdown="1"><summary>사용한 코드</summary>



</details>

#### 3. WebMvcTest

- WebMvcTest에서는, 정말 딱 MVC만을 위한 테스트를 지원한다. 등록해둔 모든 빈을 올리는 것이 아닌, Web layer, Controller부분만을 호출해서 사용하기 때문에 가볍다는 장점이 있다.

- 스캔하도록 되어 있는 빈(어노테이션 설정)은 다음과 같다. @Controller, @ControllerAdvice, @JsonComponent, @Convert, @GenericConverter, Filter, WebMvcConfigurer, HandlerMethodArgumentResolver

- 위의 빈만을 호출하기 때문에 컨트롤러의 작동 여부 등을 확인하기 좋고, 가볍게 운용될 수 있다는 장점이 있다.

- 하지만, 예외상황이나, 서비스 단의 구체적인 구동 여부 등은 정확하게 알 수 없다는 단점 또한 당연하게 가지고 있다.

예제 코드

{% raw %}
```java
@WebMvcTest
@ExtendWith(MockitoExtension.class)
public class WebMvcTestTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private userService userService; // mock이라 진짜 해줘야 하는지, 아니면 빈 올려버리는지.

    @Test
    @DisplayName("webMvcTest 테스트")
    public void webMvcTest() throws Exception {

        // given
        String reqId = "A";

        mockMvc.perform(get("/test")
                        .contentType(MediaType.APPLICATION_JSON)
                        .param("id", reqId))
                .andExpect(status().isOk())
                .andDo(print()); // response 확인

    }

    @Test
    @Order(1)
    @DisplayName("WebMvc를 통한 join 테스트")
    public void WebMvcJoin() throws Exception{

        // given
        String content = "{\"id\": \"a\", \"userName\": \"jason\"}";

        mockMvc.perform(post("/join")
                .contentType(MediaType.APPLICATION_JSON)
                .content(content))
                .andExpect(status().isOk())
                .andDo(print());
    }
}
```
{% endraw %}

> 💡 단순히 컨트롤러의 정상적인 호출 여부만을 확인하고, Request에 문제가 있는지 파악하기에는 괜찮은 것 같다.
>
> 위 WebMvcJoin이라는 테스트를 진행하면 성공, Status 200으로 확인이 되는데, 
> Response는 원래 로직대로라면 Id인 a가 리턴되어야 하지만, 실제 테스트에서는 null값으로 나온다. 
> 왜인가 생각해보았더니 진짜 Mock이기 때문에 컨트롤러에서의 조건이었던 Status 200이 나왔으니 테스트는 통과, Response의 확인은 따로 걸어줘야 한다.
>
> 그러므로 기존의 Mockito와 같이, Service 단은 미리 스텁을 만들어 줘야 한다.

> 💡 기존 코드에 Mock으로 `given``(userService.join(``any``(userDto.class))).willReturn("a");`
> 한줄 넣어주면 Response에서도 빈 값이 아닌 “a”를 확인할 수 있을 것이다.
> (더 자세한 건 나중에,,알아보도록 하자)

#### 4. AutoConfigureMockMvc

> AutoConfigureMockMvc는 @SpringBootTest 와 함께 사용한다. SpringBootTest 어노테이션과, @WebMvcTest 어노테이션은 둘 다 MockMvc를 모킹하기 때문에 둘은 같이 사용하게 되면 충돌이 발생, 함께 사용할 수 없다는 점을 인지하자.

{% raw %}
```java
@ExtendWith(MockitoExtension.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc
public class MockMvcControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("mockmvc example")
    public void MockMvcExample() throws Exception{

        // given
        String reqId = "A";

        mockMvc.perform(get("/test")
                        .contentType(MediaType.APPLICATION_JSON)
                        .param("id", reqId))
                .andExpect(status().isOk())
                .andDo(print());
    }

    @Test
    @DisplayName("mockmvc join test")
    public void MockMvcTestJoin() throws Exception {

        // given
        String content = "{\"id\": \"a\", \"userName\": \"jason\"}";

        // when
        mockMvc.perform(post("/join")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(content))
                .andExpect(status().isOk())
                .andDo(print());

    }
}
```
{% endraw %}

> 💡 WebMvcTest와 다른 점은, Service를 따로 MockBean으로 선언하지 않았다는 것.
> AutoConfigureMockMvc 는 위에서 말했듯, 선언되어 있는 모든 빈 객체를 다 올리기 때문에 더 무겁고, 실제와 같이 동작한다. 세부 동작에서 오류가 발생한다면 알아차릴 수 있을 수도 있을 것이다. 
> 때문에, Response도 당연하게 따로 정의해주지 않아도 잘 나온다.

> 💡 #Response
>
> MockHttpServletResponse:  
> Status = 200  
> Error message = null  
> Headers = [Content-Type:"text/plain;charset=UTF-8", Content-Length:"1"]  
> Content type = text/plain;charset=UTF-8  
> Body = a  
> Forwarded URL = null  
> Redirected URL = null  
> Cookies = []
