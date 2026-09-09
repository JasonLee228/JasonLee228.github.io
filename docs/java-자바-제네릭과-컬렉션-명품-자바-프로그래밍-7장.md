---
title: "[JAVA, 자바] 제네릭과 컬렉션 (명품 자바 프로그래밍 7장)"
parent: "Java"
nav_order: 5
permalink: "/notes/java-자바-제네릭과-컬렉션-명품-자바-프로그래밍-7장/"
---

1. 컬렉션

> 💡 컬렉션은 배열이 가진 고정 크기의 단점을 극복하기 위해 객체들을 쉽게 삽입, 삭제, 검색할 수 있는 가변 크기의 컨테이너이다.
> 컬렉션은 제네릭이라는 기법으로 만들어져 있고, 컬렉션 클래스의 이름에는 <E><K><V>의 형태로 주어진 '타입 매개변수' 가 있다. 타입 매개변수는 컬렉션이 정해져 있는 타입의 형태가 아닌 일반화되어있는 제네릭 타입/ 일반화 시킨 타입으로 이루어져 있음을 알 수 있다.
> 중요한 것은, 컬렉션의 요소는 객체들만 가능하다는 것이다. Integer, 클래스 객체 등으로만 타입 매개변수를 이룰 수 있다.

---

1. 제네릭

> 💡 제네릭은 모든 종류의 타입을 다룰 수 있도록, 클래스나 메소드를 타입 매개변수를 이용하여 선언하는 기법이다. 
> 이는 클래스 코드를 찍어내듯이 생산할 수 있도록 일반화시키는 도구로써 사용된다.
> 제네릭 컬렉션의 요소들은 자동 박싱, 언박싱이 이루어짐.

> 💡 일반적으로 제네릭 표현으로 사용되는 문자는 하나의 대문자로 사용된다
> - E : Element 를 의미, 컬렉션에서 요소를 나타냄
> - T : Type
> - V : Value
> - K : Key

---

1. 제네릭 컬렉션 - Vector<E>

{% raw %}
```java
Vector<Integer> v = new Vector<>(); // 선언
Vector<Integer> v = new Vector<>(3); // 크기가 3인 벡터 선언
v.add(value) // 요소 추가. (index, value)의 형태로 입력하면 원하는 위치에 요소 추가 ㅇ
v.remove(index)// index위치의 요소 삭제
v.removeAllElements();//모든 요소 삭제
v.get(index); // index위치의 요소 가져오기 
```
{% endraw %}

> 💡 #java 10부터는 제네릭의 선언부에서 간단하게 할 수 있도록 
> **var**키워드를 도입하였다.
> 이를 사용하면, var a = new Arraylist<Integer>();의 형태로 간단하게 선언이 가능하다.

1. 제네릭 컬렉션 - Arraylist<E>

> 💡 Arraylist는 벡터와 거의 같지만, 멀티 스레드를 지원하지 않는다는 차이가 있다.
> 때문에 멀티스레드 상에서는 Arraylist가 훼손될 수 있다는 단점이 있지만, 단일스레드 상에서 더 빠른 속도를 지원한다.

{% raw %}
```java
Arraylist<Integer> a = new Arraylist<>(); // 선언
var a = new Arraylist<Integer>();// var키워드 이용한 선언
a.add(value) // 요소 추가. (index, value)의 형태로 입력하면 원하는 위치에 요소 추가 ㅇ
a.remove(index)// index위치의 요소 삭제
a.clear();//모든 요소 삭제
a.get(index); // index위치의 요소 가져오기 
```
{% endraw %}

1. Iterator - 컬렉션의 순차 검색을 위해

> 💡 

{% raw %}
```java
Iterator it = v.iterator(); // 위의 벡터 v를 저장한
//아래는 해쉬테이블에서 키를 iterator로 저장하기 위한 방법.
Set<String> keys=h.keySet();
Iterator<String> it=keys.iterator();

it.next(); // 현재 it이 가르키는 요소 
while(it.hasnext()) // it이 끝날 때 까지 반복
```
{% endraw %}

---

1. HashMap<K,V>

> 💡 키와 값의 쌍으로 구성되는 요소를 다루는 컬렉션이다.
> 키를 통해 값을 검색할 수 있고, 다른 컬렉션에 비해 삭제와 삽입이 매우 빠르다.

{% raw %}
```java

HashMap<K,V> name = new HashMap<>();
name.put(k,v); // 삽입
name.get(key); // 검색해서 값 리턴
name.remove(key); //키와 값 모두 삭제

Set<String> keys = name.keySet();
Iterator<String> it = keys.iterator();
while(it.hasnext())
{
	String key = it.next();
	String value = name.get(key);
	//키와 값 계속 받아오기. 특정 검색 또는 전체 출력을 위해
}
```
{% endraw %}

> 💡 
>
> 요소가 순차적으로 저장되어 있는 제네릭 컬렉션들의 경우, Iterator<>인터페이스를 사용하면 편리한 요소의 검색이 가능하다.
