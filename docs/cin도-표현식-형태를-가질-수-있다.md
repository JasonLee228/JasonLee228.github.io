---
title: "cin도 표현식 형태를 가질 수 있다?"
parent: "C++"
nav_order: 1
permalink: "/notes/cin도-표현식-형태를-가질-수-있다/"
---

{% raw %}
```java
#include<iostream>

using namespace std;

int main()
{
	int i;

	for (cin >> i;i != 0;cin >> i)
	{
		cout << "수를 입력하세요" << endl;
	}
	return 0;
}
```
{% endraw %}

for문 내부의 식은 표현식의 형태를 띄고 있어야 한다. 하지만 cin을 사용해도 문제가 없다.

거참 신기하군,,,

*표현식

표현식(expression)이란,

1.값 또는 값과 연산자의 조합이며 한가지 값을 갖는다.

2.대입표현식과 관계표현식 등이 존재하고, 대입표현식은 대입을 받는 좌변이 대입표현식의 값이되고, 표현식을 처리하는 과정에서 대입이라는 side effect가 발생한다.

값을 입력받는 cin이 표현식의 형태를 띌 수 있다는 것은 cin자체에서 하나의 값을 가지고 있어야 하고, 아래 링크의 내용을 보자니 true와 false의 값을 가질 수 있는 것 같다.

다음과 같이도 사용 가능하다.

{% raw %}
```java
for (cin >> i;i;cin >> i)
	{
		cout << "수를 입력하세요" << endl;
	}

또는

for (cin >> i;!i;cin >> i)
	{
		cout << "수를 입력하세요" << endl;
	}
```
{% endraw %}

참고)

[What does cin return? - C++ Forum](http://www.cplusplus.com/forum/beginner/91641/)

[Address and return values of cin](https://stackoverflow.com/questions/40896106/address-and-return-values-of-cin)
