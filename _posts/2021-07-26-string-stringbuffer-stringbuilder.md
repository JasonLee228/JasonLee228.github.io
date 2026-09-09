---
title: "String, StringBuffer, StringBuilder"
date: 2021-07-26 04:08:11 +0000
categories: ["Java", "문법"]
tags: ["문법", "java"]
---

1. String, StringBuffer, StringBuilder의 차이점을 알아보자.

> 💡 String, StringBuffer, StringBuilder의 차이는 면접 질문으로도 자주 등장할 만큼 알아둬야 하고, 문자열 관리 측면에서 기본적이라고 할 수 있다.

---

1. String

> 💡 기본적으로 문자열을 생성하고, 내용을 더해주거나 빼 줄 경우, 우리(적어도 필자 본인)는
> Scanner를 이용해 String객체에 문자열을 저장하고, +를 이용해 더하는 등의 연산을 하게 된다. 하지만 String객체는 생성 이후 불변하다는 성질을 지니고 있다. 이는 String api를 확인해 보면, String객체는 final로 선언된 char형의 배열이기 때문에, 초기 생성 이후 불변할 수 밖에 없도록 만들어졌기 때문.

> 💡 그렇다면 문자열끼리 더해주거나, 기존의 문자열을 수정하는 경우, 기존의 객체를 건드는 것이 아닌, 새로운 문자열 공간을 만들고, 그 안에 연산의 결과값을 집어넣게 된다. 이후 기존의 변수는 새로 만들어진 영역을 참조한다. 기존의 영역은 가비지 컬렉션의 메모리 해제 전까지 존재하게 된다.
> 때문에, 문자열 연산이 새로 이루어질 때 마다 새로운 공간을 만들게 되고, 반복적인 연산은 String객체의 수를 늘려 메모리의 낭비를 불러 일으키게 된다.

---

1. Buffer

> 💡 버퍼는 기본적으로 데이터를 임시 저장하는 메모리이다.
> 기존의 문자열 연산은 String객체 공간을 만들어 결과를 집어넣었지만, 그러한 방법이 아닌 기존의 공간을 계속 이용한다면? 엄청난 메모리적 이득을 볼 것이다.
> 그래서 나온 방법이 '버퍼'를 이용하는 방법이다.

> 💡 StringBuffer과 StringBuilder은 버퍼에서 문자열 연산 작업을 하는 클래스이다. 
> 내부 버퍼에 문자열을 저장한 뒤, 그 안에서 추가/삭제,, 등의 연산을 진행하기 때문에 연산 시마다 새로운 공간을 만들지 않는다는 장점을 지니고 있다.

---

*StringBuffer/Stringbuilder 메소드

> 💡 .append(값)
>
> - StringBuffer, StringBuilder 뒤에 값을 붙인다
>
>
> .insert(인덱스, 값)
>
> - 특정 인덱스부터 값을 삽입한다
>
>  
> .delete(인덱스, 인덱스)
>
> - 특정 인덱스부터 인덱스까지 값을 삭제한다
>
>  
> .indexOf(값)
>
> - 값이 어느 인덱스에 들어있는지 확인한다
>
>  
> .substring(인덱스, 인덱스)
>
> - 인덱스부터 인덱스까지 값을 잘라온다
>
>  
> .length()
>
> - 길이 확인
>
>  
> .replace(인덱스, 인덱스, 값)
>
> - 인덱스부터 인덱스까지 값으로 변경
>
>  
> .reverse()
>
> - 글자 순서를 뒤집는다

---

1. StringBuffer/Stringbuilder 예제 코드

{% raw %}
```java
class Main {
	static public void main(String []args) {
		
		StringBuffer sbuffer = new StringBuffer("StringBuffer");
		StringBuilder sbuilder = new StringBuilder("StringBuilder");
		
		// StringBuffer, StringBuilder는 변하기(mutable)하기 때문에
		// StringBuffer, StringBuilder 예제 
		
				System.out.println(sbuilder);
        System.out.println(sbuffer);
				
				sbuilder.append("빌더"); // 삽입
				sbuffer.append("버퍼"); // 삽입
        System.out.println(sbuilder);
        System.out.println(sbuffer);

        sbuilder.insert(0, "builder"); // 중간에 삽입
        sbuffer.insert(0, "buffer"); // 중간에 삽입
        System.out.println(sbuilder);
        System.out.println(sbuffer);

				sbuilder.delete(3, 7); // 자르기
        sbuffer.delete(3, 7); // 자르기
        System.out.println(sbuilder);
        System.out.println(sbuffer);

        System.out.println(sbuilder.indexOf("abc")); // indexOf 예제(없는것)
        System.out.println(sbuffer.indexOf("abc")); // indexOf 예제(없는것)
        System.out.println(sbuilder.indexOf("Builder")); // indexOf 예제(있는것)
        System.out.println(sbuffer.indexOf("Buffer")); // indexOf 예제(있는것)

        sbuilder.reverse();//역순 
        sbuffer.reverse();//역순 
        System.out.println(sbuilder);
        System.out.println(sbuffer);
		
        sbuilder.substring(0, 4); // 자르기
				sbuffer.substring(0, 4); // 자르기

        System.out.println(sbuilder);
        System.out.println(sbuffer);
				System.out.println(sbuilder.length()); // 문자열 길이 예제
        System.out.println(sbuffer.length()); // 문자열 길이 예제
        System.out.println(sbuilder.replace(0, 4, "CCCC")); // replace 예제
				System.out.println(sbuffer.replace(0, 4, "DDDD")); // replace 예제
		
		
		
    }
}
```
{% endraw %}

결과

{% raw %}
```java
StringBuilder
StringBuffer
StringBuilder빌더
StringBuffer버퍼
builderStringBuilder빌더
bufferStringBuffer버퍼
buiStringBuilder빌더
buftringBuffer버퍼
-1
-1
9
8
더빌redliuBgnirtSiub
퍼버reffuBgnirtfub
더빌redliuBgnirtSiub
퍼버reffuBgnirtfub
18
16
CCCCdliuBgnirtSiub
DDDDffuBgnirtfub
```
{% endraw %}

1. String / StringBuffer / Stringbuilder을 사용하면 좋은 경우

> 💡 String은 값이 불변한다. 따라서 문자열을 단정지은 뒤, 단순히 꺼내 출력하는 상황이 많은 경우, String을 사용하는 것이 더 좋다고 알려져 있다. 
> 이외의 경우, 문자열에 추가/삭제 등 연산이 빈번하게 일어나는 경우에는 Stringbuffer, Stringbuilder을 사용하는 것이 더 좋다.
