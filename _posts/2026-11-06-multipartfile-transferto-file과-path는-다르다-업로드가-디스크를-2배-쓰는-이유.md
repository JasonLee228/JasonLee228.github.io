---
title: "MultipartFile.transferTo(File)과 transferTo(Path)는 다르다: 업로드가 디스크를 2배 쓰는 이유"
date: 2026-11-06 18:20:00 +0900
categories: ["Spring", "운영"]
tags: ["spring", "multipart", "tomcat", "파일업로드", "디스크"]
permalink: /posts/multipartfile-transferto-file과-path는-다르다-업로드가-디스크를-2배-쓰는-이유/
---

## 업로드 하나에 디스크가 두 배

파일 업로드 상한을 10GiB로 올리기 전에 pod 디스크 사용량을 봤다. 업로드 1건이 진행되는 동안 파일 크기의 **약 2배**가 쓰이고 있었다.

경로를 따라가니 복사가 두 번 일어났다.

1. Tomcat이 multipart 요청을 받으면서 part를 자기 임시 폴더(work dir)에 쓴다. 이건 서블릿 컨테이너의 기본 동작이다.
2. 우리 서비스가 `file.getInputStream()`을 읽어 **자기 temp 파일로 다시 복사**한다. 그 뒤 검사·전송을 한다.

같은 바이트가 두 곳에 있다. 1GB 파일이면 2GB, 10GB 파일이면 20GB다. 상한을 올리면 pod 디스크가 먼저 찬다.

---

## transferTo는 두 개다

Spring `MultipartFile`에는 `transferTo`가 두 개 있다. 이름이 같아서 아무거나 쓰기 쉽다.

{% raw %}
```java
void transferTo(File dest) throws IOException, IllegalStateException;
default void transferTo(Path dest) throws IOException, IllegalStateException;
```
{% endraw %}

Spring Framework 7.0.9의 `StandardMultipartHttpServletRequest.StandardMultipartFile` 구현은 이렇다.

{% raw %}
```java
@Override
public void transferTo(File dest) throws IOException, IllegalStateException {
    this.part.write(dest.getPath());
    if (dest.isAbsolute() && !dest.exists()) {
        // Servlet Part.write is not guaranteed to support absolute file paths:
        // may translate the given path to a relative location within a temp dir
        // (for example, on Jetty whereas Tomcat and Undertow detect absolute paths).
        // At least we offloaded the file from memory storage; it'll get deleted
        // from the temp dir eventually in any case. And for our user's purposes,
        // we can manually copy it to the requested location as a fallback.
        FileCopyUtils.copy(this.part.getInputStream(), Files.newOutputStream(dest.toPath()));
    }
}

@Override
public void transferTo(Path dest) throws IOException, IllegalStateException {
    FileCopyUtils.copy(this.part.getInputStream(), Files.newOutputStream(dest));
}
```
{% endraw %}

- `transferTo(Path)`는 **항상 복사**다. 스트림을 읽어 새 파일에 쓴다.
- `transferTo(File)`은 서블릿 `Part.write(String)`에 **위임**한다. 컨테이너가 어떻게 하는지는 컨테이너 몫이다.

`Path`가 더 현대적인 API라서 좋아 보이지만, 디스크 사용량 관점에서는 `File` 쪽이 다르게 동작할 여지가 있다.

---

## Tomcat의 Part.write는 rename이다

Tomcat 11.0.27 `ApplicationPart.write`는 경로를 `File`로 만들고 `DiskFileItem.write(File)`에 넘긴다.

{% raw %}
```java
@Override
public void write(String fileName) throws IOException {
    File file = new File(fileName);
    if (!file.isAbsolute()) {
        file = new File(location, fileName);   // 상대 경로면 multipart location 기준
    }
    try {
        fileItem.write(file);
    } catch (Exception e) {
        throw new IOException(e);
    }
}
```
{% endraw %}

`DiskFileItem.write(File)`의 핵심은 이 부분이다.

{% raw %}
```java
final File outputFile = getStoreLocation();      // Tomcat이 이미 디스크에 쓴 part 파일
...
if (file.exists() && !file.delete()) {
    throw new FileUploadException("Cannot write uploaded file to disk!");
}
if (!outputFile.renameTo(file)) {               // 1. 이동을 먼저 시도
    BufferedInputStream in = null;
    BufferedOutputStream out = null;
    try {
        in = new BufferedInputStream(new FileInputStream(outputFile));
        out = new BufferedOutputStream(new FileOutputStream(file));
        IOUtils.copy(in, out);                   // 2. 실패하면 복사
        out.close();
    } finally {
        IOUtils.closeQuietly(in);
        IOUtils.closeQuietly(out);
    }
}
```
{% endraw %}

part가 메모리에 있으면(`isInMemory()`, 작은 파일) 그냥 쓴다. 디스크에 있으면 **대상을 지우고 `renameTo`로 이동**한다. 이동이 안 될 때만 복사한다.

`renameTo`는 같은 파일 시스템 안에서는 디렉터리 엔트리만 바꾸는 작업이다. 데이터를 다시 쓰지 않는다. 그래서 Tomcat work dir와 서비스 temp 디렉터리가 **같은 볼륨**이면 디스크 사용량은 파일 크기 1배다.

---

## 바꾼 것

복사 루프를 지우고 `transferTo(File)` 한 줄로 바꿨다.

{% raw %}
```java
// 전
try (InputStream input = file.getInputStream()) {
    copyToTempFile(input, tempFile);           // 256KB 버퍼로 읽어 쓰기
}

// 후
// transferTo(Path)는 복사, transferTo(File)은 Tomcat part를 rename으로 이동해 디스크를 1배만 사용
// 상대 경로면 Tomcat이 multipart location 기준으로 풀기 때문에 절대 경로로 넘긴다
file.transferTo(tempFile.toAbsolutePath().toFile());
```
{% endraw %}

두 가지를 같이 챙겼다.

**절대 경로를 넘긴다.** 위 `ApplicationPart.write`에서 봤듯 상대 경로는 Tomcat의 multipart `location` 기준으로 풀린다. 우리가 의도한 temp 폴더가 아닌 곳에 파일이 생긴다. Spring 쪽 fallback(`dest.isAbsolute() && !dest.exists()`)도 절대 경로일 때만 동작한다.

**temp와 work dir를 같은 볼륨에 둔다.** Kubernetes라면 같은 `emptyDir`을 두 경로에 마운트하거나, `server.tomcat.basedir`과 서비스 temp를 한 볼륨 아래 둔다. 다른 볼륨이면 `renameTo`가 실패해 복사로 떨어진다. 동작은 정상이지만 디스크는 다시 2배다.

실패 처리는 그대로 유지했다. `transferTo`가 예외를 던지면 만들다 만 temp 파일을 지운다.

### 대상 테스트

업로드·드래그드롭·클립보드 붙여넣기 세 경로의 단위 테스트 25건이 그대로 통과했다. 호출부 입장에서 결과 파일의 내용은 같기 때문이다. 바뀐 것은 "어떻게 거기 도달했나"다.

---

## 확인하는 방법

바꾼 뒤 정말 이동이 됐는지 보려면 Tomcat work dir를 본다. `renameTo`가 성공했으면 업로드 직후 work dir에 part 파일이 없고 temp에만 있다. 복사로 떨어졌으면 요청이 끝날 때까지 두 곳에 다 있다.

로컬에서는 `server.tomcat.basedir`을 지정하고 큰 파일을 올리면서 `du`로 두 폴더를 같이 보면 된다.

---

## 정리

| 항목 | 내용 |
|---|---|
| 문제 | Tomcat part 파일 + 서비스 temp 복사로 업로드 1건이 디스크 2배 |
| `transferTo(Path)` | 항상 스트림 복사 (`FileCopyUtils.copy`) |
| `transferTo(File)` | 서블릿 `Part.write` 위임. Tomcat은 `renameTo` 이동, 실패 시 복사 |
| 조건 | work dir와 temp가 같은 파일 시스템이어야 이동 |
| 주의 1 | 상대 경로는 Tomcat multipart location 기준으로 풀림. 절대 경로로 넘긴다 |
| 주의 2 | 메모리에 있는 작은 part는 어차피 쓰기 한 번 |
| 주의 3 | Jetty 등 다른 컨테이너는 `Part.write` 동작이 다를 수 있음 |

Spring Framework 7.0.9, Tomcat 11.0.27 소스 기준이다. 운영 환경에서 `du`로 전후 디스크 사용량을 측정한 수치는 아직 없다. 같은 볼륨인지는 배포 매니페스트로만 확인했다.
