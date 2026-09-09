---
title: "삽입 정렬(insertion Sort)"
date: 2021-07-23 02:43:30 +0000
categories: ["알고리즘", "정렬"]
tags: ["정렬", "알고리즘"]
---

**1. 삽입 정렬**  
 : 삽입 정렬의 기본은 '자리를 찾아서 넣어준다'이다. 숫자로 이루어진 배열을 정렬한다고 했을 때, 각 수에 알맞은 자리를 찾아서 위치를 바꿔주는 방식으로 진행된다.  
삽입 정렬이 선택 정렬/버블 정렬과 다른 점은, '필요 시' 에 만 위치를 바꾸는 방식으로 진행된다는 점인데, 이는 더 빠른 정렬을 도와줄 수 있게 된다. 

---

**2-1. 예제**

> 💡 아래 숫자들을 오름차순으로 정렬하는 프로그램을 작성하세요
>
> 1,10,5,8,7,6,4,3,2,9

#삽입 정렬은 기본적으로 두 번의 반복문이 들어가 있기에 선택, 버블 정렬과 비슷한 속도를 가지고 있다고 생각할 수 있지만, 아래 4,4-1을 보게 되면, '정렬이 되어 있을 시'에 위 두 정렬보다는 훨씬 빠른 정렬속도를 가지고 있는 특징을 가지고 있다.(이 경우에는 어떤 정렬 알고리즘보다 빠른 수행시간을 가지고 있다.)

![image](/assets/images/e8c8e4847c244fc58427d0faec15b1e6.gif)

출처)[https://github.com/GimunLee/tech-refrigerator/blob/master/Algorithm/resources/insertion-sort-001.gif](https://github.com/GimunLee/tech-refrigerator/blob/master/Algorithm/resources/insertion-sort-001.gif)  


---

**2-2.코드**

{% raw %}
```java
package test;
import java.util.*;
public class Main {

	public static void main(String[] args) {//3. 삽입 정렬
		
		int temp;
		int[] arr = {
				1,10,5,8,7,6,4,3,2,9
		};
		int i,k;
		
		for(i=0;i<10;i++)
		{
			k=i;
			while(k>0&&arr[k-1]>arr[k])
			{
				temp=arr[k-1];
				arr[k-1] = arr[k];
				arr[k] = temp;
				k--;
			}
			for(int j=0;j<arr.length;j++)
				System.out.print(arr[j]+" ");
			System.out.println();
		}
		System.out.println();
	}

}
```
{% endraw %}

2-3. 코드 수행

> 💡 1번 수행 : 1 10 5 8 7 6 4 3 2 9 
> 2번 수행 : 1 10 5 8 7 6 4 3 2 9 
> 3번 수행 : 1 5 10 8 7 6 4 3 2 9 
> 4번 수행 : 1 5 8 10 7 6 4 3 2 9 
> 5번 수행 : 1 5 7 8 10 6 4 3 2 9 
> 6번 수행 : 1 5 6 7 8 10 4 3 2 9 
> 7번 수행 : 1 4 5 6 7 8 10 3 2 9 
> 8번 수행 : 1 3 4 5 6 7 8 10 2 9 
> 9번 수행 : 1 2 3 4 5 6 7 8 10 9 
> 10번 수행 : 1 2 3 4 5 6 7 8 9 10

---

**3.시간 복잡도**

> 💡 삽입 정렬의 기본적인 시간 복잡도는 O(N^2)이다. 
> 하지만, 삽입 정렬의 장점은 이미 정렬이 완료되어있는 배열 내에서 삽입/삭제를 할 경우에 있다. 다음 예제를 보자.

> 💡 아래 숫자들을 오름차순으로 정렬하는 프로그램을 작성하세요
>
> 2,3,4,5,6,7,8,9,10,1

  
4**.코드**

{% raw %}
```java
package test;
import java.util.*;
public class Main {

	public static void main(String[] args) {//3. 삽입 정렬
		
		int temp;
		int[] arr = {
				2,3,4,5,6,7,8,9,10,1
		};
		int i,k;
		
		for(i=0;i<10;i++)
		{
			k=i;
			while(k>0&&arr[k-1]>arr[k])
			{
				temp=arr[k-1];
				arr[k-1] = arr[k];
				arr[k] = temp;
				k--;
			}
			for(int j=0;j<arr.length;j++)
				System.out.print(arr[j]+" ");
			System.out.println();
		}
		System.out.println();
	}

}
```
{% endraw %}

**4-1. 코드 수행**

> 💡 1번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 2번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 3번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 4번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 5번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 6번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 7번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 8번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 9번 수행 : 2 3 4 5 6 7 8 9 10 1 
> 10번 수행 : 1 2 3 4 5 6 7 8 9 10

위 실행 이미 정렬이 거의 완료되어있는 배열인 arr[]에서는while문의 조건에 맞는 경우가 맨 마지막 수인 1을 판별할 때 한 번 뿐이므로 단 한번의 실행만으로 정렬을 완료할 수 있음을 알 수 있다.

 때문에 최선의 상태에서 삽입 정렬의 시간 복잡도는 O(N)이다. 

참고) 안경잡이개발자 블로그 강의

[안경잡이개발자 : 네이버 블로그](https://blog.naver.com/ndb796/221226803544)
