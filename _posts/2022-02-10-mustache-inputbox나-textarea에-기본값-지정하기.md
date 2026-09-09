---
title: "mustache, inputBox나 TextArea에 기본값 지정하기"
date: 2022-02-10 10:50:43 +0000
categories: ["Spring", "웹서비스"]
tags: ["웹서비스", "spring"]
---

> 💡 게시판을 구성하던 와중, 글쓴이를 사용자가 직접 구성하는 것이 아닌 기본적으로 로그인한 사용자의 이름을 가져와 넣어주면 어떨까 생각하게 되었다.

#### #indexController

{% raw %}
```java
@GetMapping("/posts/save")
    public String postsSave(Model model, @LoginUser SessionUser user) {
        model.addAttribute("posts", postsService.findAllDesc());
        if (user != null) {
            model.addAttribute("userNames", user.getName());
        }

        return "posts-save";
    }
    /*
    @GetMapping("/posts/save")
    public String postsSave() {
        return "posts-save";
    }
    */
```
{% endraw %}

> 💡 주석처리된 부분은 책에서 나온 기본적인 글쓰기에 대한 controller부분인데, 
> 버튼을 클릭했을 시 게시글 쓰는 화면만 연결해주기 때문에 return으로 해당하는 mustache만 연결해주고 있다.
> 이를 바꿔 준 것이 위의 코드이다.
>
> 현재 로그인되어 있는 사용자의 정보를 SessionUser를 통해 가져오게 되고, model에 이를 추가 해 준다. 그리고 user.getName()을 통해 이름을 가져오는 것.
> 이후 return은 똑같이 posts-save로 연결 해 준다.

---

#### #posts-save.mustache

{% raw %}
```java
<div class="form-group">
                <label for="author"> 작성자 </label>
                <input type="text" class="form-control"
                       id="author" name="userName" value="{{userNames}}" 
											 placeholder="작성자를 입력하세요">
            </div>

```
{% endraw %}

> 💡 크게 바뀐 것은 없는데, 기존의 id=”author” 뒤에 controller에서 넘겨받은 userName을 default값으로 보여주기 위해 name, value 속성을 추가 해 주었다. 
> value="&#123;&#123;userNames}}" 를 통해 indexController에서 넘겨받은 userNames를 input 영역의 기본값으로 출력해주게 되고, 해당 값은 수정이 가능하다.

#### #수정 후 화면

![image](/assets/images/ae8027fc33c4495e9acbde3d26e477cc.png)
