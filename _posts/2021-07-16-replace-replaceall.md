---
title: "replace() / replaceAll()"
date: 2021-07-16 06:21:22 +0000
categories: ["Java", "문법"]
tags: ["문법", "java"]
permalink: /posts/replace-replaceall/
---

replace(), replaceAll() 이 두 메소드는 문자열 내에서 원하는 문자열을 대체하는 기능으로 사용된다.

- replace()

#예제

{% raw %}
```java
import java.util.*;
class main {
	static public void main(String []args) {
        String str = "abcdefg";
        System.out.println("replace 사용 전 "+str);
        str = str.replace("abc","w");
        System.out.println("replace 사용 후 "+str);
    }
}
```
{% endraw %}

---

#실행 결과

{% raw %}
```java
replace 사용 전 abcdefg
replace 사용 후 wdefg
```
{% endraw %}

---

- replaceAll

#예제

{% raw %}
```java
import java.util.*;
class main {
	static public void main(String []args) {
        String str = "abcdefg";
        System.out.println("replaceAll 사용 전 "+str);
        str = str.replaceAll("abc","w");
        System.out.println("replaceAll 사용 후 "+str);
    }
}
```
{% endraw %}

---

#실행 결과

{% raw %}
```java
replaceAll 사용 전 abcdefg
replaceAll 사용 후 wdefg
```
{% endraw %}

---

- replace() vs replaceAll()

단순한 예제로만 봤을 때 둘의 기능은 같다고 할 수 있다.

그러면 굳이 두개로 나눌 필요 없이 하나만 쓰면 안 되나? 라는 생각을 할 수 있는데,   
사실 둘은 큰(?)차이를 가지고 있다.

replace()는 인자로 사용할 값이 단순 charSequence 값인데,   
replaceAll()은 인자로 사용할 값의 형태가 String 값이라는 것.

String 값을 인자로 사용한다는 것은 정규표현식 값을 사용할 수 있다는 것이다.

다음 예제를 통해 정규표현식 값 표현이 어떤 말인지 알아보자.

#정규표현식 예제

{% raw %}
```java
import java.util.*;
class main {
	static public void main(String []args) {
        String str = "abcdefg";
        System.out.println("replaceAll 사용 전 "+str);
        str = str.replaceAll("[abcdefg]","w");
        System.out.println("replaceAll 사용 후 "+str);
    }
}
```
{% endraw %}

---

#실행 결과

{% raw %}
```java
replaceAll 사용 전 abcdefg
replaceAll 사용 후 wwwwwww
```
{% endraw %}

위 예제와 기존 replaceAll()의 차이를 알겠는가? 바로 [abcdefg], 즉 []의 사용이다.

## 정규식은 문자열에서 특정 패턴을 찾거나 교체, 삭제 등 문자열을 원하는 형태로 편집하는 기능을 제공해 줍니다. 정규식은 자주 사용되지는 않지만, 어떤 경우에 일반적인 로직으로 처리하기 힘든것은 간편하게 처리할 수 있는 힘이 있습니다.

출처:

[https://offbyone.tistory.com/400](https://offbyone.tistory.com/400)

[쉬고 싶은 개발자]

위 예제를 보게 되면, [ ] 안에는 abcdefg 가 들어있고, 결과값을 보니 a~g 의 모든 문자열이 w로 대체되었음을 알 수 있다. 따라서, 정규식은 다음과 같이 이해할 수 있다.

: [문자들] 의 형식으로 []안에 값 각각을 모두 인자로 사용하겠다는 뜻과 같다.  
ex)[abcdefg] -> replaceAll("[abcdefg]","w");  
->a,b,c,d,e,f,g 각각 전부 다 e로 바꾸겠다는 뜻과 같음.

이외에도 정규식에 대한 내용은 많지만, 여기서는 replace()와 replaceAll()의 차이만을 알기 위한 정규식 내용이므로 다른 부가설명은 하지 않았다.

이것이 바로 replace()와 replaceAll()의 가장 큰 차이이자, 사용 방법이다.
