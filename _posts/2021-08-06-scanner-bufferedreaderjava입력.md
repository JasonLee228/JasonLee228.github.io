---
title: "Scanner, BufferedReader(Java입력)"
date: 2021-08-06 01:37:40 +0000
categories: ["Java", "입출력"]
tags: ["입출력", "java"]
---

1. Scanner

> 💡 자바 입력의 가장 기본이 될 수 있는 Scanner이다.
>
> Scanner는 사용하기 쉽고, 예외처리가 없다는 장점을 가지고 있지만, 속도가 느리다는 단점을 가지고 있다.
> 이 때문에 알고리즘 등의 문제를 풀 때, 시간초과를 내는 원인이 될 수 있다.

---

1. Scanner 사용법

> 💡 Scanner은 java.util 내에 포함되어 있다. 따라서, import java.util.Scanner를 넣어줘야 사용 가능하다.

> 💡 Scanner클래스를 이용해 입력을 받게 되면, 입력 유형에 따라 달리 받을 수 있다는 장점을 가지고 있다. 
> 데이터 유형에 따라서 next~()의 형태를 띄는데, 가장 많이 사용하는 예는 다음과 같다.
>
> 정수형 : nextInt()
> 실수형 : nextFloat() , nextDouble()
> 문자형 : next() , charAt()→입력은 아님.
> 문자열 : nextLine()
> 등이 있다.
>
> 여기서 문자형에 대한 문제가 하나 있는데, Scanner은 입력을 문자열로밖에 받지 못한다고 한다. 때문에, next()로 입력을 받게 될 때는 문자열 변수에 저장을 하고, 
> charAt()의 사용은 입력받은 문자열의 원하는 index의 부분을 떼어 저장하는 데에 사용한다.
> 이 사용법은 아래 예제를 통해 보여질 수 있다.

---

1. Scanner 예제

{% raw %}
```java
import java.util.Scanner;

class queue {
	public static void main(String[] args) {
		Scanner s = new Scanner(System.in);
		
		int a = s.nextInt();
		float b = s.nextFloat();
		double c = s.nextDouble();
		String d = "asdf";
		char ch = d.charAt(0);
		String e = s.next();
		
		System.out.println();
		System.out.println(a);
		System.out.println(b);
		System.out.println(c);
		System.out.println(d);
		System.out.println(ch);
		System.out.println(e);
		
	}

}
```
{% endraw %}

{% raw %}
```java
결과

123
1.234
10.123
asdf

123
1.234
10.123
asdf
a
asdf
```
{% endraw %}

뭔가 이상하지 않은가? 분명 마지막 next()는 문자를 입력받을 수 있다고 했는데 출력에는 문자열이 출력이 되었다.  
이는 next()가 단순히 '문자'를 입력 받는 것이 아닌, 입력의 다음 토큰, 단어를 문자열로 반환하는 메소드이기 때문이다. 때문에 개행(\n)뿐 아니라 공백으로도 구분되어 출력된다. 이 예는 다음 예제로 볼 수 있다.(→ 정확히는 문자를 받는 것이 아닌 문자열을 받는 것.)

{% raw %}
```java
123
123
123
a sdf

int : 123
float : 123.0
double : 123.0
char : a
next() : a
```
{% endraw %}

---

1. BufferedReader()

> 💡 버퍼를 사용하는 BufferedReader이다.
> 이 방법이 Scanner보다 빠른 이유는, Scanner의 장점과도 연관성이 있다.
>
> 위에 설명했듯, Scanner은 입력된 데이터를 분석한 뒤, 데이터 유형에 따라서 저장할 수 있다는 장점을 가지고 있다고 했었다.
> → 데이터를 분석하는 시간이 필요하다는 말과도 같다.
>
> 하지만 BufferedReader은 단순히 문자/문자열을 읽어들인다. 
> 버퍼를 이용하여 한번에 받아들인다는 이점과 함께, 구분 분석이 없이 바로 문자 그대로 입력된다는 점에서 속도적 이득이 있는 것이다.

> 💡 BufferedReader은 한 라인 단위로 문자열을 받아들인다.
> 입력 받을 버퍼의 크기를 지정하거나 기본적으로 정해진 크기를 사용할 수 있으며, 이에 따른 생성자 두 가지는 다음과 같다.

{% raw %}
```java
BufferedReader (Reader in)
BufferedReader (Reader in, int sz) 
```
{% endraw %}

> 💡 BufferedReader를 사용하는 경우가 좋은 것은, 단순히 시간적 문제에 그치지 않고 파일 입출력과 같은 상황에서 비용 절감을 위해 특히 많이 사용한다.
>
> 또한, BufferedReader는 동기식이기 때문에, 다중 쓰레드의 상황에서는 꼭 BufferedReader를 사용해야 한다.
