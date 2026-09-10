---
title: "Java Files.createDirectory, createDirectories 의 차이"
date: 2024-05-02 02:54:25 +0000
categories: ["Java", "문법"]
tags: ["문법", "java"]
permalink: /posts/java-filescreatedirectory-createdirectories-의-차이/
---

`Files.createDirectory()` 및 `Files.createDirectories()` 메서드는 모두 디렉터리를 생성하는데 사용되는 Java의 메서드입니다. 그러나 두 메서드 간에는 중요한 차이가 있습니다.

1. **Files.createDirectory(Path path)**:
    - 이 메서드는 지정된 경로에 새 디렉터리를 만듭니다.

    - 하지만 만약 **부모 디렉터리가 존재하지 않는다면 예외를 발생시킵니다**. 따라서 경로의 상위 디렉터리들이 모두 존재해야 합니다.

    - 즉, 단일 디렉터리를 생성할 때 사용됩니다.

1. **Files.createDirectories(Path path)**:
    - 이 메서드는 지정된 경로의 모든 부모 디렉터리를 만듭니다. 따라서 필요한 모든 디렉터리를 만듭니다.

    - 만약 부모 디렉터리가 존재하지 않아도 경로의 모든 부모 디렉터리를 자동으로 생성합니다.

    - 즉, 디렉터리를 재귀적으로 생성할 때 사용됩니다.

예를 들어, `/parent/child/grandchild` 경로에 디렉터리를 생성하려고 할 때:

- `Files.createDirectory(Path.of("/parent/child/grandchild"))`를 사용하면 `/parent/child` 디렉터리가 이미 존재해야 하며, 그렇지 않으면 예외가 발생합니다.

- `Files.createDirectories(Path.of("/parent/child/grandchild"))`를 사용하면 필요한 모든 부모 디렉터리인 `/parent`와 `/parent/child`도 함께 생성됩니다.
