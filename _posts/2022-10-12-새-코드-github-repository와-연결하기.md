---
title: "새 코드 github repository와 연결하기"
date: 2022-10-12 12:44:49 +0000
categories: ["Git", "워크플로"]
tags: ["워크플로", "git"]
---

- 본 내용은 PC 에 git, git bash 가 설치되어 있다는 가정 하에 이루어집니다.

![image](/assets/images/e81444b36b6e428ca3d78ce48538513e.png)

1. 자신의 Github your Repositories 에 들어가서 New 를 클릭, 코드를 올릴 Repository 생성하기

![image](/assets/images/8f0d52cedc884a1ca3c247dbdd47fa48.png)

![image](/assets/images/f56703bc669f4dcf80f492ac2d962b46.png)

1. 올리고 싶은 파일이 있는 위치에서 Git Bash 실행하기

![image](/assets/images/4298b395abf042818011a8e7bfb6cbb2.png)

1. git bash 에서 $git init 명령을 실행하여 로컬 깃 저장소를 생성

![image](/assets/images/1d60e7b3a89b44189f85dca79874ec1d.png)

1. 아까 만들어둔 github repository로 가서, Code 버튼 클릭 후, 아래와 같은 .git 으로 끝나는 주소 복사

![image](/assets/images/2673912be29e479b9146016a8eece0ee.png)

1. git bash 에서 remote 추가하기

- $ git remote add origin [복사한주소] 

- 추가한 뒤에 $ git remote -v 명령을 실행해 보자. 아래와 같이 나온다면 원격 저장소와 로컬 저장소의 연결이 이루어진 것이다.

![image](/assets/images/545a59f44c314118a5f8bbb40835983a.png)

1. 원격 저장소의 브랜치와 로컬 저장소의 브랜치 맞춰주기

- `git branch -M main`  master → main 브랜치로 이동  (master)에서 (main)으로 바뀌었다면 성공입니다. 처음에 깃허브의 레포지토리를 생성할 때 defalut branch로 main 브랜치가 설정되었기 때문에 로컬 저장소의 브랜치도 맞춰주는 것!

- `git pull origin main` 원격 저장소와 로컬 저장소의 상태 맞추기.  원격 저장소의 최종 상태를 동기화 하는 것

![image](/assets/images/fe5407d7cdb64f4999e8a4f076af2b77.png)

1. 현재 폴더(bash가 실행된 위치, 올리고 싶은 파일이 존재하는 위치) 에서 `git add .` 명령 실행

- 현재 위치의 변경된 모든 파일을 커밋 할 코드로 올리는 것

![image](/assets/images/2fe9c0f13cdf4913ab29eba0c1fb3009.png)

1. add 된 변경 내역 commit 하기

- `git commit -m "[커밋 메시지]"`

![image](/assets/images/25e2332392074a49abe52658a0fdc26b.png)

1. 원격 브랜치로 commit 한 내용 push 하기

- `git push -u origin main`

![image](/assets/images/3f681542ecea4f11b8713ef200e42197.png)

1. Github에서 코드가 잘 올라왔나 확인하기~

![image](/assets/images/b33d1234b35748a3a4baa61874344478.png)
