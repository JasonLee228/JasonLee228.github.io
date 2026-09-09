---
title: "Java String.isEmpty, isBlank 의 차이점"
parent: "Java"
nav_order: 11
permalink: "/notes/java-stringisempty-isblank-의-차이점/"
---

Java에서 `String.isEmpty()`와 `String.isBlank()`는 문자열이 비어있는지 또는 공백인지 확인하는 데 사용되는 메서드입니다. 이 두 메서드는 문자열의 상태를 검사하는데, 각각 다른 방식으로 동작합니다. 아래에서 그 차이점을 설명하겠습니다.

#### `String.isEmpty()`

- **Java 버전**: 이 메서드는 Java 6부터 사용할 수 있습니다.

- **동작**: 문자열이 길이가 0인지 확인합니다.

- **공백 문자열**: 공백만 있는 문자열(" ")은 비어있지 않다고 간주합니다.

- **예제**:
  {% raw %}
  ```java
  public class Main {
      public static void main(String[] args) {
          String str1 = "";
          String str2 = " ";
          String str3 = "Hello";

          System.out.println("str1 is empty: " + str1.isEmpty()); // true
          System.out.println("str2 is empty: " + str2.isEmpty()); // false
          System.out.println("str3 is empty: " + str3.isEmpty()); // false
      }
  }

  ```
  {% endraw %}

#### `String.isBlank()`

- **Java 버전**: 이 메서드는 Java 11부터 사용할 수 있습니다.

- **동작**: 문자열이 공백만 포함하거나 비어있는지를 확인합니다. 공백 문자는 유니코드에서 정의된 모든 공백 문자를 포함합니다.

- **공백 문자열**: 공백만 있는 문자열(" ")도 비어있다고 간주합니다.

- **예제**:
  {% raw %}
  ```java
  public class Main {
      public static void main(String[] args) {
          String str1 = "";
          String str2 = " ";
          String str3 = "Hello";
          String str4 = "   ";

          System.out.println("str1 is blank: " + str1.isBlank()); // true
          System.out.println("str2 is blank: " + str2.isBlank()); // true
          System.out.println("str3 is blank: " + str3.isBlank()); // false
          System.out.println("str4 is blank: " + str4.isBlank()); // true
      }
  }

  ```
  {% endraw %}

#### 차이점 요약

1. **사용 가능 버전**:
    - `isEmpty()`: Java 6부터 사용 가능

    - `isBlank()`: Java 11부터 사용 가능

1. **동작 방식**:
    - `isEmpty()`: 문자열이 길이가 0인지 확인

    - `isBlank()`: 문자열이 비어있거나 공백만 포함하는지 확인

1. **공백 문자열 처리**:
    - `isEmpty()`: 공백 문자열은 비어있지 않다고 간주 (길이가 0이 아님)

    - `isBlank()`: 공백 문자열도 비어있다고 간주 (공백 문자만으로 구성된 문자열도 빈 문자열로 처리)

#### 결론

- *`isEmpty()`*는 문자열의 길이가 0인지 확인하는 데 사용되며, 공백 문자가 포함된 문자열은 비어있지 않다고 간주합니다.

- *`isBlank()`*는 문자열이 비어있거나 공백 문자만 포함하는지를 확인하는 데 사용되며, 모든 공백 문자로만 이루어진 문자열도 비어있다고 간주합니다.

이 두 메서드를 적절하게 사용하면 문자열의 상태를 정확하게 검사할 수 있습니다. Java 11 이상을 사용하고 문자열이 공백만으로 구성되어 있는지도 확인해야 한다면 `isBlank()`를 사용하는 것이 더 적합합니다. Java 6 이상에서 단순히 문자열이 비어있는지만 확인하려면 `isEmpty()`를 사용할 수 있습니다.
