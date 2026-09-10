---
title: "퀵 정렬(Quick Sort)"
date: 2021-07-23 02:43:29 +0000
categories: ["알고리즘", "정렬"]
tags: ["정렬", "알고리즘"]
permalink: /posts/퀵-정렬quick-sort/
---

**1. 퀵 정렬**  
 : 퀵 정렬은 이전의 선택, 버블, 삽입 정렬보다 빠른 속도를 가진, 대표적인 분할 정복 알고리즘이다.   
처음 공부를 시작할 때, 퀵 정렬이 이전 다른 정렬 알고리즘보다 어렵다는 느낌을 준다는 얘기를 들었는데, 실제로 이해하고 코드를 작성하는 데에만 몇 시간이 걸린 것 같다.

퀵 정렬은 특정 값을 기준으로 큰 수와 작은 수를 나누자는 생각으로, Pivot이라는 개념을 사용한다. 오름차순 기준으로, pivot보다 작은 값은 pivot의 왼쪽으로, 큰 값은 pivot의 오른쪽으로 이동시킨 뒤, 좌/우로 나누어진 양쪽을 분할하여 정렬하는, 재귀적 방법을 사용하고 있다.

본인은 '동빈나의 알고리즘 강의' 를 보며 기본을 공부했기 때문에, 강의와 같이 현 배열의 가장 오른쪽 값을 pivot으로 정한 뒤 사용하는 방법을 택했다.

---

![image](/assets/images/e12019fa0dd44f6fb5afd055762f4203.gif)

출처)[https://github.com/GimunLee/tech-refrigerator/blob/master/Algorithm/resources/quick-sort-001.gif](https://github.com/GimunLee/tech-refrigerator/blob/master/Algorithm/resources/quick-sort-001.gif)

---

다음 예제를 통해, 퀵 정렬이 구성되고 동작하는 방식을 알아보자.

**2-1. 예제**

> 💡 아래 숫자들을 오름차순으로 정렬하는 프로그램을 작성하세요
>
> (1)1,10,5,8,7,6,4,3,2,9
> (2)7,2,5,1,3,4
> (3)9,7,8,1,5,3,6,10,2,4
> (4)5,7,1,2,4,6,8,9

이중(3) →  9, 7, 8, 1, 5, 3, 6, 10, 2, 4 를 정렬하는 방법을 순서화했다.

> 💡 퀵 정렬은, pivot과 함께 사용하는 개념으로 Left(Start, 이하 l), Right(End, 이하 r)라는 개념을 사용한다. l은 배열의 앞쪽부터 오른쪽으로 나아가며 pivot보다 큰 값을 찾고, r은 배열의 오른쪽에서 왼쪽으로 나아가며 pivot보다 작은 값을 찾게 된다.
>

<details markdown="1"><summary>펼쳐서 정렬 단계 보기</summary>



</details>

  


**2-2.코드**

{% raw %}
```java
import java.util.*;
public class q {
	public static int[] arr = {//4가지 케이스의 정렬 test
			9,7,8,1,5,3,6,10,2,4
			//7,2,5,1,3,4
			//5,7,1,2,4,6,8,9
			//1,10,5,8,7,6,4,3,2,9
	};
	static int count=0;
	public static void main(String[] args) {//3. 퀵 정렬
		quicksort(arr, 0, arr.length-1);
		System.out.println(Arrays.toString(arr));
			System.out.println("종료.");
		}
	
	
    public static void swap(int[] arr, int i, int j) {
        int temp = arr[i];
        arr[i] = arr[j];
        arr[j] = temp; 
    }

    
    public static void quicksort(int[] arr, int left, int right) {
    	
    	int pivot = left;
         int l = left+1;
         int r = right;
         if(left>=right){           
            return;
         }
        do//while(l<r)는 사용 불가
        { 
            while(arr[l]<arr[pivot]&&l<right)
            {
                l++;
                
            }
            
            while(arr[r]>arr[pivot])
            {
                r--;
                
            }
            if(l<r)
            {
            	 swap(arr,l,r);
            }
            else 
                {
            	if(r!=pivot)
                        swap(arr,r,pivot);   
                }
        }while(l<r);
        quicksort(arr,left,r-1);
        quicksort(arr,r+1,right);
    }
}
```
{% endraw %}

2-3. 코드 수행

> 💡 (1)[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
> (2)[1, 2, 3, 4, 5, 7]
> (3)[1, 2, 4, 5, 6, 7, 8, 9]
> (4)[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

2-4. 설명

> 💡 

---

3**.특이점?**

> 💡 중간에 보면 do_while로 구성이 되어 있는 부분이 바로 정렬을 할지 안 할지 결정하는 부분이다. while을 쓰면 되지 않나 싶기도 하지만, 다음의 경우를 보면 do_while을 써야 하는 이유를 알 수 있다.

{% raw %}
```java
public static void quicksort(int[] arr, int left, int right) {
    	
    	int pivot = left;
         int l = left+1;
         int r = right;
         if(left>=right){
            System.out.println("left>=right로 이 순환은 종료 : "+Arrays.toString(arr)+"");
            System.out.println("고정된 값 : "+ arr[r]);
            System.out.println();
            return;
         }
         System.out.println("이번 시작시 pivot : "+arr[pivot]+", 
														l : "+arr[l]+", r : "+arr[r]);
         
         while(l<r)
        { 
        	System.out.println("한 사이클 시작");
            for(int w=left;w<=right;w++)
            	System.out.print(arr[w]+" ");
            System.out.println();
        	
            while(arr[l]<arr[pivot]&&l<right)
            {
            	System.out.println("현재 l값 : "+arr[l]);
            	l++;
               
            }
            System.out.println("현재 l값 : "+arr[l]);
            while(arr[r]>arr[pivot])
            {
            	System.out.println("현재 r값 : "+arr[r]);
            	r--;
                
            }
            System.out.println("현재 r값 : "+arr[r]);
            if(l<r)
            {
            	 System.out.println("arr[l] : ["+arr[l]+"] 이랑 arr[r] : ["
																									+arr[r] +"] 값 변경.(엇갈리지 않음)");
            	
            	 swap(arr,l,r);
            }
            else 
                {
            	if(r!=pivot)
            		System.out.println("arr[r] : ["+arr[r]+"] 이랑 arr[pivot] : ["
																									+arr[pivot] +"] 값 변경.(엇갈림)");
                        swap(arr,r,pivot);   
                }
        }//while(l<r);
        System.out.println("이번 종료시 pivot : "+arr[pivot]+", l : "
																									+arr[l]+", r : "+arr[r]);
        
        System.out.print("이번 종료시 배열 : ");
        for(int w=left;w<=right;w++)
        	System.out.print(arr[w]+" ");
        System.out.println();
        System.out.println("고정된 값 : "+ arr[r]);
        System.out.println();
        quicksort(arr,left,r-1);
        quicksort(arr,r+1,right);
    }

```
{% endraw %}

> 💡 위 예제 코드와 같이 순환되는 모든 과정에 출력을 달아 과정을 확인해 보았다. 결과는 다음과 같다.

<details markdown="1"><summary>while문 확인하기(펼치기)</summary>



</details>

> 💡 다른 부분은 do_while과 똑같이 동작하지만, 마지막 즈음 부분인 [7,6]을 정렬하는 과정에서 while의 문제점이 나오게 된다. while문의 조건은 l<r인데, [7,6]을 전달받을 때 l값과 r값이 같게 되면서 while문에 진입을 하지 못하게 되고, 교체를 해 주어야 하는 pivot의 배열값 7과 r의 배열값 6이 서로 교체되지 않고 단계가 끝나버리는 현상이 일어나는 것이다. 
> 이를 do_while문으로만 바꾸고 실행하게 되면 다음과 같은 결과가 나온다.

<details markdown="1"><summary>do_while 문 확인하기(펼치기)</summary>



</details>

> 💡 [7,6]부분을 보면 while 사용 시와 다르게 반복문에 한 번은 진입을 하게 되고, pivot과 r의 배열값 교체가 이루어지는 것을 볼 수 있다. 이와 같은 이유로 while을 사용할 수 없고, do_while을 사용하게 되었다.

---

4**.시간 복잡도**

> 💡 퀵 정렬의 시간 줄이기는 바로 "분할"에서 온다. 
> 직관적으로 생각해 보자. 만약 10개의 인수를 가진 배열을 정렬하게 된다면, 이전의 정렬을 사용하게 될 시 시간복잡도는 O(N^2) = 100인데, 단순히 배열을 둘로만 분할한다고 해도
> (O(N^2) = 25) + (O(N^2) = 25) = 50이 나온다. 같은 O(N^2)을 사용했는데에도 반이나 줄어드는데, 분할 정렬을 하게 되어 분할을 반복하게 되면 더 줄어들 수 있다는 것이다.
> 결국, 퀵 정렬의 평균 시간 복잡도는 다음과 같게 된다.

{% raw %}
```text
O(N*log N)
```
{% endraw %}

> 💡 하지만 퀵 정렬의 평균 시간 복잡도가 그러한 것이지, 퀵 정렬에도 한계는 존재한다. 만약 주어진 배열이 이미 오름차순 또는 내림차순으로 정렬되어 있다면, 한 개의 원소씩만 분할하게 되는 상황이 주어지고, 때문에 결국 O(N^2)의 시간복잡도를 갖게 된다.

> 💡 퀵 정렬은 다른 분할 알고리즘의 기초가 되는 중요한 알고리즘이다
> 하지만 퀵정렬은 시간복잡도의 최악의 경우 O(N^2)라는 좋지 못한 효율성을 지니고 있기 때문에 시간복잡도에 제한이 걸려 있는 알고리즘 문제같은 경우에는 사용하지 않는 것을 권장하고 있다.

참고) 안경잡이개발자 블로그 강의

[안경잡이개발자 : 네이버 블로그](https://blog.naver.com/ndb796)

참고2) 다보의 개발일기

[https://dabo-dev.tistory.com/16](https://dabo-dev.tistory.com/16)
