---
title: "Type definition error: [simple type, class …]"
date: 2022-12-13 11:12:56 +0000
categories: ["Spring-Boot"]
---

> 💡 프로젝트에서 API 요청을 보낼 때 났던 에러. 
> 전체 에러 로그는 아래와 같았다.

{% raw %}
```javascript
org.springframework.http.converter.HttpMessageConversionException: Type definition error: [simple type, class com.spring.loginmodule.dto.user.req.ReqJoinDto]
	at org.springframework.http.converter.json.AbstractJackson2HttpMessageConverter.readJavaType(AbstractJackson2HttpMessageConverter.java:403) ~[spring-web-6.0.2.jar:6.0.2]
	at org.springframework.http.converter.json.AbstractJackson2HttpMessageConverter.read(AbstractJackson2HttpMessageConverter.java:354) ~[spring-web-6.0.2.jar:6.0.2]
	at org.springframework.web.servlet.mvc.method.annotation.AbstractMessageConverterMethodArgumentResolver.readWithMessageConverters(AbstractMessageConverterMethodArgumentResolver.java:182) ~[spring-webmvc-6.0.2.jar:6.0.2]
	at org.springframework.web.servlet.mvc.method.annotation.RequestResponseBodyMethodProcessor.readWithMessageConverters(RequestResponseBodyMethodProcessor.java:163) ~[spring-webmvc-6.0.2.jar:6.0.2]
	at org.springframework.web.servlet.mvc.method.annotation.RequestResponseBodyMethodProcessor.resolveArgument(RequestResponseBodyMethodProcessor.java:136) ~[spring-webmvc-6.0.2.jar:6.0.2]
	at org.springframework.web.method.support.HandlerMethodArgumentResolverComposite.resolveArgument(HandlerMethodArgumentResolverComposite.java:122) ~[spring-web-6.0.2.jar:6.0.2]
	at org.springframework.web.method.support.InvocableHandlerMethod.getMethodArgumentValues(InvocableHandlerMethod.java:181) ~[spring-web-6.0.2.jar:6.0.2]
	at org.springframework.web.method.support.InvocableHandlerMethod.invokeForRequest(InvocableHandlerMethod.java:148) ~[spring-web-6.0.2.jar:6.0.2]
	
Caused by: com.fasterxml.jackson.databind.exc.InvalidDefinitionException: Cannot construct instance of `com.spring.loginmodule.dto.user.req.ReqJoinDto` (no Creators, like default constructor, exist): cannot deserialize from Object value (no delegate- or property-based Creator)
 at [Source: (org.springframework.util.StreamUtils$NonClosingInputStream); line: 2, column: 5]
	at com.fasterxml.jackson.databind.exc.InvalidDefinitionException.from(InvalidDefinitionException.java:67) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.DeserializationContext.reportBadDefinition(DeserializationContext.java:1909) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.DatabindContext.reportBadDefinition(DatabindContext.java:408) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.DeserializationContext.handleMissingInstantiator(DeserializationContext.java:1354) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.deser.BeanDeserializerBase.deserializeFromObjectUsingNonDefault(BeanDeserializerBase.java:1420) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.deser.BeanDeserializer.deserializeFromObject(BeanDeserializer.java:352) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.deser.BeanDeserializer.deserialize(BeanDeserializer.java:185) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.deser.DefaultDeserializationContext.readRootValue(DefaultDeserializationContext.java:323) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.ObjectReader._bindAndClose(ObjectReader.java:2105) ~[jackson-databind-2.14.1.jar:2.14.1]
	at com.fasterxml.jackson.databind.ObjectReader.readValue(ObjectReader.java:1481) ~[jackson-databind-2.14.1.jar:2.14.1]
	at org.springframework.http.converter.json.AbstractJackson2HttpMessageConverter.readJavaType(AbstractJackson2HttpMessageConverter.java:395) ~[spring-web-6.0.2.jar:6.0.2]
	... 98 common frames omitted

2022-12-13T20:13:19.601+09:00  WARN 42912 --- [nio-8080-exec-2] .m.m.a.ExceptionHandlerExceptionResolver : Resolved [org.springframework.http.converter.HttpMessageConversionException: Type definition error: [simple type, class com.spring.loginmodule.dto.user.req.ReqJoinDto]]
```
{% endraw %}

- 뭐 이래저래 많이 써 있지만 결국 생성자를 찾지 못해 body를 생성하지 못했다는 의미로 볼 수 있겠다.

- 에러가 났던 DTO

{% raw %}
```java
@Getter
@AllArgsConstructor
@Builder
public class ReqJoinDto {

    private String email;
    private String password;
    private String name;

}
```
{% endraw %}

- 생성자는 전부 어노테이션으로 생성했고,,,builder도 잘 작동하는 듯 싶었으나 아니었던 듯,,,

- 그래서 혹시나 하는 마음으로 `@NoArgsConstructor`_ _어노테이션까지 붙여봤다.

- 잘 작동한다!

#### 왜?

> 💡 **@AllArgsConstructor - 모든 필드 값을 파라미터로 받는 생성자를 만들어준다.**
>
> **@NoArgsConstructor - 파라미터가 없는 기본 생성자를 생성해준다.  
>   
> 에러 중간에 다음과 같은 말이 있다.**
>
> co[m.fasterxml.jackson.databind.exc.InvalidDefinitionException:](http://m.fasterxml.jackson.databind.exc.invaliddefinitionexception/) Cannot construct instance of "내 DTO"
>
> (no Creators, like default constructor, exist): cannot deserialize from Object value (no delegate- or property-based Creator)  
>
>
> **serialize(직렬화) - 객체의 상태를 바이트 스트림으로 변환하는 작업**
>
> **deserialize(역직렬화) - 바이트 스트림을 다시 객체형태로 변환하는 작업  
>   
> 문제는 역직렬화 과정에서 사용해야 할 기본 생성자가 존재하지 않아서 발생했던 것이었다.  
> 때문에 기본 생성자를 만들어주는**`@NoArgsConstructor`_ _가 있어야 했던 것

#### end.

> 💡 항상 다른 사람들의 코드를 보면서 기본 생성자를 왜 만들어 주나 했는데 다 이유가 있던 거였다.
>
> 역직렬화 → 기본 생성자 이용 → `@NoArgsConstructor`

#### **Reference**

[No Creators, like default construct, exist): cannot deserialize from Object value (no delegate- or property-based Creator](https://stackoverflow.com/questions/53191468/no-creators-like-default-construct-exist-cannot-deserialize-from-object-valu)
