---
title: "[SpringBoot] 전체 회원 리스트 만들기"
date: 2022-02-10 11:59:00 +0000
categories: ["Spring-Boot", "스프링부트와 AWS로 혼자 구현하는 웹 서비스"]
---

#### #UserRepository 수정

{% raw %}
```java
//..추가
@Query("SELECT p FROM user p ORDER BY p.id DESC")
    List<User> findAllUser();

```
{% endraw %}

> 💡 여기서 문제가 발생한다.
> ”QuerySyntaxException is not mapped” 이라는 오류가 떴던 것.
>
> 알고 보니 해결법은 간단했다. 
> 쿼리를 통해 조회할 Table의 이름을 DB의 테이블명이 아닌 도메인(엔티티)클래스의 이름을 넣어줘야 했다.
> 때문에 다음과 같이 변경해주니 잘 돌아간다. 

(한글자 바뀐게 이렇게 중요하다는 걸 새삼 느낌.)

{% raw %}
```java
//..추가
@Query("SELECT p FROM User p ORDER BY p.id DESC")
    List<User> findAllUser();

```
{% endraw %}

---

#### #UserService 생성

{% raw %}
```java
package com.bookstudy.springboot.service.user;

import com.bookstudy.springboot.domain.user.UserRepository;
import com.bookstudy.springboot.web.dto.UserListResponseDto;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@RequiredArgsConstructor
@Service
public class userService {

    private final UserRepository userRepository;


    @Transactional(readOnly = true)
    public List<UserListResponseDto> findAllUser() {
        return userRepository.findAllUser().stream()
                .map(UserListResponseDto::new)
                .collect(Collectors.toList());
    }
}
```
{% endraw %}

---

#### #UserListResponseDto 생성

{% raw %}
```java
package com.bookstudy.springboot.web.dto;

import com.bookstudy.springboot.domain.posts.Posts;
import com.bookstudy.springboot.domain.user.Role;
import com.bookstudy.springboot.domain.user.User;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
public class UserListResponseDto {

    private Long id;
    private String name;
    private String email;
    private Role role;

    public UserListResponseDto(User entity)
    {
        this.id = entity.getId();
        this.name = entity.getName();
        this.email = entity.getEmail();
        this.role = entity.getRole();
    }
}
```
{% endraw %}

---

#### #Controller 수정

{% raw %}
```java
...
@GetMapping("/user/list")
    public  String userList(Model model)
    {
        model.addAttribute("user", userService.findAllUser());
        return "user-list";
    }//추가
```
{% endraw %}

  


#### #user-list.mustache 추가

{% raw %}
```java
{{>layout/header}}

<h1>전체 유저 목록</h1>

<div class="col-md-12">
    <table class="table table-horizontal table-bordered">
        <thead class="thead-strong">
        <tr>
            <th>Id</th>
            <th>Email</th>
            <th>userName</th>
            <th>Role</th>
        </tr>
        </thead>
        <tbody id="tbody">
        {{#user}}
            <tr>
                <td>{{id}}</td>
                <td>{{email}}</td>
                <td>{{name}}</td>
                <td>{{role}}</td>
            </tr>
        {{/user}}
        </tbody>
    </table>
</div>

{{>layout/footer}}
```
{% endraw %}
