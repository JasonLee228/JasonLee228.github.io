---
title: "[Spring] spring Bean 주입 방식"
date: 2022-10-19 11:36:42 +0000
categories: ["Spring-Boot"]
---

- 스프링에서 빈의 주입은 어떤 방식으로 이루어지는가?

> 💡 스프링에서는 DIP가 잘 지켜진다고 했다. 
> 근데 다형성(OCP)을 지키며  스프링에서 DIP를 어떻게 지키는가? 가 의문이 들었다.
>
> 하나의 인터페이스로 여러 개의 구현체를 지닐 때, 스프링에서는 내가 원하는 클래스가 뭔지 알고 넣어주는가? 라는 의문
>
> 결론 ) 스프링 빈 주입은 이름을 통해 이루어진다. → 이름의 중요성
> ITestRepository 인터페이스와 그 구현체 TestRepository1, TestRepository2 가 있다면, 
>
> 해당 인터페이스를 참조하는 클래스에서 변수 명을 testRepository1 이라 하냐, 2라 하냐에 따라 갈린다는 것.
> 이건 @Component 어노테이션을 사용하는 것 뿐 아니라 configure 파일을 통해 할 때도 같은 원리로 작용한다.

정리는 집에서,,,,꼭 하기,,,,

final / static / static final

빈으로 올라가는 거 이름은 스프링에서 사용할 클래스 이름으로 받아서 넣어준다.

해당 내용 정리하기,,  
집가서,,,하면 안될거같은데,,,,,

![image](/assets/images/0b59da8480b14d3eafd1a72601fc31b4.png)

---

![image](/assets/images/70be965e6ba146008ab9a29e900caadf.png)

---

![image](/assets/images/2f37a70b0cdc48bd958420acbf215fc1.png)

---

![image](/assets/images/cf56f009e74a4dc7aa697215c7b1bdfa.png)

---

![image](/assets/images/56556cd0b09b425bbdf131d680b3ac08.png)

---

![image](/assets/images/057f68d7830b4debbe8820c6db3412c2.png)

 

---

![image](/assets/images/e56dcb95fa8b4936928d7f3b34cb67be.png)
