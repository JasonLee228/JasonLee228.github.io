---
title: "Windows 개발 환경의 한글 인코딩 함정: PowerShell 5.1과 Gradle javadoc"
date: 2026-10-26 11:30:00 +0900
categories: ["개발환경", "Windows"]
tags: ["windows", "powershell", "gradle", "인코딩"]
permalink: /posts/windows-개발-환경의-한글-인코딩-함정-powershell-51과-gradle-javadoc/
---

Windows에서 개발하다 보면 코드는 멀쩡한데 한글만 깨지는 일이 반복된다. 이번에 겪은 건 서로 다른 두 가지였다.

1. PowerShell 5.1로 소스나 문서를 가공했더니 한글이 전부 `?`로 바뀌었다.
2. Gradle `javadoc` 태스크가 `unmappable character ... x-windows-949`로 실패했다.

두 문제 모두 원인은 같은 계열이다. **Windows 기본 인코딩이 UTF-8이 아니다.** 한국어 Windows에서는 보통 MS949(CP949)다. 이 글에서는 증상, 복구, 예방을 나눠서 정리한다.

## 1. PowerShell 5.1이 한글을 `?`로 바꾼다

### 증상

Java 소스의 Javadoc 한글 주석을 고치려고 PowerShell 파이프라인을 사용했다.

{% raw %}
```powershell
(Get-Content .\OrderHandler.java) -replace 'foo', 'bar' | Set-Content .\OrderHandler.java
```
{% endraw %}

실행 후 파일을 열어보니 한글 주석이 이렇게 바뀌어 있었다.

{% raw %}
```text
/** ??? ?? ??? ?? */
```
{% endraw %}

문제는 diff가 크게 나오지 않을 때가 있다는 점이다. 리뷰에서 "Javadoc 한글이 `???`로 깨졌다"는 Critical 지적을 받고서야 알았다.

### 원인

Windows PowerShell 5.1의 기본 동작은 다음과 같다.

| 동작 | 5.1 기본 동작 |
|---|---|
| `Get-Content` | BOM이 없으면 UTF-8이 아니라 시스템 기본 코드 페이지(ANSI)로 읽는다. |
| `Set-Content`, `Add-Content` | 시스템 기본 코드 페이지(ANSI)로 쓴다. |
| `>`, `>>`, `Out-File` | UTF-16LE로 쓴다. |
| 파이프로 네이티브 프로그램에 넘길 때 | `$OutputEncoding` 기준으로 변환한다. 기본값이 ASCII인 환경이 있다. |

BOM 없는 UTF-8 파일을 `Get-Content`가 CP949로 잘못 해석한다. 그 문자열을 `Set-Content`가 다시 CP949로 저장한다. 이 과정에서 표현할 수 없는 문자는 `?`로 대체된다. 한 번 `?`로 바뀐 정보는 되돌릴 수 없다.

PowerShell 7 이상은 기본 인코딩이 BOM 없는 UTF-8이라 이 문제가 거의 없다. 다만 정확한 기본값은 버전과 cmdlet에 따라 다를 수 있으니, 사용하는 버전의 문서를 확인하는 것이 좋다.

### 복구

`?`로 바뀐 파일은 **내용을 복원할 수 없다.** 그래서 파일을 고치는 방향이 아니라 원본으로 돌아가는 방향으로 복구했다.

1. 이번 작업에서 바꾼 부분이 무엇인지 따로 기록한다. (시그니처, 추가한 메서드 등)
2. 깨진 파일을 git에 커밋된 상태로 되돌린다. (`git restore <경로>` 등. 되돌리면 그 파일의 미커밋 변경은 사라지므로 1번을 먼저 한다.)
3. 기록해 둔 변경분만 다시 적용한다.

이때 다시 적용하는 도구가 중요하다. 같은 PowerShell 파이프라인을 쓰면 같은 사고가 반복된다. 에디터나 파일 편집 도구처럼 **UTF-8로 직접 쓰는 도구**를 사용했다.

### 예방

가장 확실한 방법은 PowerShell로 소스 텍스트를 가공하지 않는 것이다. 어쩔 수 없다면 인코딩을 명시한다.

{% raw %}
```powershell
# 읽기와 쓰기 모두 인코딩을 명시한다.
$text = Get-Content .\OrderHandler.java -Raw -Encoding UTF8
$text = $text -replace 'foo', 'bar'

# BOM 없는 UTF-8로 쓰려면 .NET API가 가장 확실하다. (5.1의 -Encoding UTF8은 BOM을 붙인다)
[System.IO.File]::WriteAllText(
    (Resolve-Path .\OrderHandler.java),
    $text,
    (New-Object System.Text.UTF8Encoding($false)))
```
{% endraw %}

변경 후에는 깨짐 여부를 빠르게 확인한다.

{% raw %}
```bash
# 추가된 줄에 연속된 물음표가 생겼는지 확인한다.
git diff | grep -nE '^\+.*\?\?\?'
git diff --stat
```
{% endraw %}

한글이 한 줄도 바뀌지 않았는데 diff stat이 큰 파일은 줄바꿈이나 인코딩이 통째로 바뀌었을 가능성이 높다.

## 2. PowerShell에서 Maven `-Dtest=A,B`가 동작하지 않는다

인코딩은 아니지만 같은 PowerShell 환경에서 자주 만나서 같이 적는다. 테스트를 여러 개 지정하려고 쉼표를 썼다.

{% raw %}
```powershell
mvn -Dtest=OrderServiceTest,PaymentServiceTest test
```
{% endraw %}

PowerShell은 쉼표를 배열 구분자로 해석하는 경우가 있어, Maven에 인자가 의도와 다르게 전달될 수 있다. **인자 전체를 따옴표로 감싸면** 한 문자열로 전달된다.

{% raw %}
```powershell
mvn "-Dtest=OrderServiceTest,PaymentServiceTest" test
```
{% endraw %}

Bash 계열에서는 문제가 없지만 Windows 터미널 스크립트에서는 처음부터 따옴표를 습관으로 두는 편이 안전하다.

## 3. Gradle javadoc의 `unmappable character ... x-windows-949`

### 증상

라이브러리를 로컬 저장소에 배포하려고 했다.

{% raw %}
```powershell
gradle clean publishToMavenLocal
```
{% endraw %}

`compileJava`와 `jar`는 성공했는데 `javadoc` 단계에서 실패했다.

{% raw %}
```text
error: unmappable character (0xEC) for encoding x-windows-949
```
{% endraw %}

소스 파일은 UTF-8이고 한글 Javadoc이 들어 있었다. `javadoc` 도구는 소스를 **시스템 기본 인코딩(여기서는 MS949)** 으로 읽으려 했다.

### 시도했지만 해결되지 않은 것

가장 먼저 JVM 인코딩 옵션을 주었다.

{% raw %}
```powershell
gradle clean build "-Dfile.encoding=UTF-8"
```
{% endraw %}

같은 오류로 실패했다. `javadoc` 태스크는 Gradle 데몬과 별개로 도구를 실행하고, 소스 인코딩은 `-encoding` 옵션으로 따로 받는다. JVM의 `file.encoding`을 바꾼다고 이 옵션이 바뀌지 않는다. (JDK 18 이상은 기본 인코딩이 UTF-8로 바뀌었다. 여기서는 Java 17을 썼다.)

### 해결

태스크의 인코딩 옵션을 직접 지정한다.

{% raw %}
```groovy
// build.gradle
tasks.withType(JavaCompile).configureEach {
    options.encoding = 'UTF-8'
}

tasks.withType(Javadoc).configureEach {
    options.encoding = 'UTF-8'
}
```
{% endraw %}

이 설정 후 `publishToMavenLocal`이 성공했다. 남은 것은 Javadoc 경고뿐이었다.

### 빌드 스크립트를 수정할 수 없을 때

남의 라이브러리를 소스에서 직접 빌드해야 하고, 필요한 산출물이 런타임 jar와 pom뿐이라면 javadoc을 건너뛰는 방법도 있다.

{% raw %}
```powershell
gradle clean build -x javadoc -x javadocJar
# 또는 jar와 pom만 생성
gradle clean jar generatePomFileForMavenJavaPublication
```
{% endraw %}

단, 이 방식은 javadoc jar가 필요 없다는 판단이 있을 때만 쓴다. 결과물이 "전체 빌드 성공"이 아니라는 점을 작업 기록에 남겨 두었다. `jar` 태스크가 실행되었다고 해서 전체 빌드가 통과했다는 근거는 아니기 때문이다.

## 정리

| 증상 | 원인 | 대응 |
|---|---|---|
| PowerShell로 가공한 파일의 한글이 `?` | 5.1의 기본 읽기/쓰기가 ANSI(CP949) | 원본 복원 후 변경분만 재적용. 이후 UTF-8을 명시하거나 편집 도구 사용 |
| `>` 리다이렉션 결과가 이상함 | 5.1의 `>`는 UTF-16LE | `Out-File -Encoding utf8` 또는 .NET API 사용 |
| `mvn -Dtest=A,B`가 먹지 않음 | 쉼표가 PowerShell에서 배열 구분자 | `"-Dtest=A,B"`로 따옴표 처리 |
| Gradle javadoc `unmappable character` | javadoc이 기본 인코딩으로 소스를 읽음 | `options.encoding = 'UTF-8'`. `-Dfile.encoding`으로는 해결되지 않음 |

체크리스트로 줄이면 이렇다.

- [ ] 소스 파일 수정은 에디터나 UTF-8로 직접 쓰는 도구로 한다.
- [ ] PowerShell 5.1에서 파일을 읽고 쓰면 `-Encoding`을 명시한다.
- [ ] 수정 후 `git diff`에서 `???`와 diff stat을 확인한다.
- [ ] Maven 인자는 PowerShell에서 따옴표로 감싼다.
- [ ] Gradle 프로젝트는 `JavaCompile`과 `Javadoc`의 `options.encoding`을 명시한다.
- [ ] javadoc을 제외하고 빌드했다면 그 사실을 기록한다.

한글 깨짐은 한 번 일어나면 원본을 복원할 수 없는 종류의 사고다. 그래서 고치는 방법보다 **쓰기 전에 인코딩을 확인하는 습관**이 더 중요하다.
