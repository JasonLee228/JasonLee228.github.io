---
title: "[Test] MockWebServer"
date: 2023-12-13 04:48:20 +0000
categories: ["Spring-Boot"]
---

#### MockWebServer 란?

#### 예제 코드

- 서비스 코드

{% raw %}
```java
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

@Service
@RequiredArgsConstructor
public class TestService {

    private final WebClient testWebClient;

    public String test() {


        String response = testWebClient.get()
                .retrieve()
                .bodyToMono(String.class)
                .block();

        return response;

    }

}
```
{% endraw %}

- 테스트 코드

{% raw %}
```java
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TestServiceTest {

    @Mock
    private WebClient webClient;

    // @InjectMocks
    private TestService testService;

    private static MockWebServer mockWebServer;

    @BeforeAll
    static void setMockWebServer() throws IOException {
        mockWebServer = new MockWebServer();
        mockWebServer.start();
    }

    @BeforeEach
    public void init() throws IOException {
        webClient = WebClient.create(mockWebServer.url("/").toString());
        testService = new TestService(webClient);
    }

    @AfterAll
    static void tearDown() throws IOException {
        mockWebServer.shutdown();
    }

    @Test
    public void testMyMethod() throws Exception {
        // MockWebServer에 응답을 설정합니다.
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setBody("Hello, world!"));

        // 테스트 메소드를 호출합니다.
        String response = testService.test();

        System.out.println("response = " + response);
        // 테스트 결과를 검증합니다.
        assertEquals("Hello, world!", response);
    }

    @Test
    public void testMyMethod2() throws Exception {
        // MockWebServer에 응답을 설정합니다.
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setBody("Hello"));

        // 테스트 메소드를 호출합니다.
        String response = testService.test();

        System.out.println("response = " + response);
        // 테스트 결과를 검증합니다.
        assertEquals("Hello", response);
    }

    @Test
    public void testMyMethod3() throws Exception {
        // MockWebServer에 응답을 설정합니다.
        mockWebServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .setBody("world!"));

        // 테스트 메소드를 호출합니다.
        String response = testService.test();

        System.out.println("response = " + response);
        // 테스트 결과를 검증합니다.
        assertEquals("world!", response);
    }

}
```
{% endraw %}

#### 설정하기

{% raw %}
```java
private WebClient webClient;
private static MockWebServer mockWebServer;

@BeforeAll
static void setMockWebServer() throws IOException {
    mockWebServer = new MockWebServer();
    mockWebServer.start();
}

@BeforeEach
public void init() {

    webClient = WebClient.create(mockWebServer.url("/").toString());

}

@AfterAll
static void shutDownWebServer() throws IOException {
    mockWebServer.shutdown();
}
```
{% endraw %}

#### Error code 잡기!

{% raw %}
```java
try {
    apiResponse = poolWebClientForZtca.post()
            .uri(uri)
            .header(HEADER_KEY_AUTHORIZATION, authorization)
            .header(ApiConstants.X_SOFTCAMP_TRACEID, utilService.getSoftcampTraceId(null))
            .contentType(MediaType.APPLICATION_JSON)
            .bodyValue(conditionalPolicySearchFilter)
            .retrieve()
            .onStatus(HttpStatus::isError, response -> response.bodyToMono(String.class)
                    .flatMap(error -> Mono.error(new BusinessException(error, EErrorCode.INTERNAL_SERVER_ERROR))))
            .bodyToMono(ResResourceApiResponse.class)
            .block();

} catch (Exception e) {
    throw new InternalServerException("execute Conditional policy Search Api Error: " + e.getMessage(),
            ZTCA_RESOURCE_API_SERVER_ERROR);
}
```
{% endraw %}

위와 같은 WebClient 요청 코드가 있을 때, error response 에 대한 test 를 진행하고 싶다면 아래와 같이 작성한다.

{% raw %}
```java
mockWebServer.enqueue(new MockResponse().setResponseCode(400)
                .setBody("\"code\": -1,\n" +
                        "    \"message\": \"Fail\""));
```
{% endraw %}

- 요청 코드에 `onStatus()` 부분을 보면, 단순히 에러 코드만 보는 것이 아니라 response body 를 함께 보고 있기 때문에, `setResponseCode(400)` 만 설정한다면 onStatus() 에서 인식하지 않는다.

package com.softcamp.shieldgate.service;

import okhttp3.mockwebserver.MockResponse;  
import okhttp3.mockwebserver.MockWebServer;  
import org.junit.jupiter.api.*;  
import org.junit.jupiter.api.extension.ExtendWith;  
import org.mockito.InjectMocks;  
import org.mockito.Mock;  
import org.mockito.junit.jupiter.MockitoExtension;  
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;  
import static org.mockito.ArgumentMatchers.anyString;  
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)  
class TestServiceTest {

{% raw %}
```text
@Mock
private WebClient webClient;

// @InjectMocks
private TestService testService;

private static MockWebServer mockWebServer;

@BeforeAll
static void setMockWebServer() throws IOException {
    mockWebServer = new MockWebServer();
    mockWebServer.start();
}

@BeforeEach
public void init() throws IOException {
    webClient = WebClient.create(mockWebServer.url("/").toString());
    testService = new TestService(webClient);
}

@AfterAll
static void tearDown() throws IOException {
    mockWebServer.shutdown();
}

@Test
public void testMyMethod() throws Exception {
    // MockWebServer에 응답을 설정합니다.
    mockWebServer.enqueue(new MockResponse()
            .setResponseCode(200)
            .setBody("Hello, world!"));

    // 테스트 메소드를 호출합니다.
    String response = testService.test();

    System.out.println("response = " + response);
    // 테스트 결과를 검증합니다.
    assertEquals("Hello, world!", response);
}

@Test
public void testMyMethod2() throws Exception {
    // MockWebServer에 응답을 설정합니다.
    mockWebServer.enqueue(new MockResponse()
            .setResponseCode(200)
            .setBody("Hello"));

    // 테스트 메소드를 호출합니다.
    String response = testService.test();

    System.out.println("response = " + response);
    // 테스트 결과를 검증합니다.
    assertEquals("Hello", response);
}

@Test
public void testMyMethod3() throws Exception {
    // MockWebServer에 응답을 설정합니다.
    mockWebServer.enqueue(new MockResponse()
            .setResponseCode(200)
            .setBody("world!"));

    // 테스트 메소드를 호출합니다.
    String response = testService.test();

    System.out.println("response = " + response);
    // 테스트 결과를 검증합니다.
    assertEquals("world!", response);
}

```
{% endraw %}

}
