---
title: "DateTimeFormatter의 SMART와 STRICT: 2026-02-30이 조용히 02-28이 되는 이유"
date: 2026-10-27 10:30:00 +0900
categories: ["Java", "문법"]
tags: ["java", "datetimeformatter", "java-time", "유효성검사"]
permalink: /posts/datetimeformatter의-smart와-strict-2026-02-30이-조용히-02-28이-되는-이유/
---

## 리뷰에서 나온 한 줄

커서 기반 페이징 API를 리뷰받다가 이런 지적을 받았다.

> `DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")`로 커서를 파싱하면 `2026-02-30 00:00:00`이 예외 없이 `2026-02-28`로 바뀐다. 커서 비교가 틀어진다.

처음 반응은 "그게 파싱이 되나?"였다. 된다. 기본 설정의 `DateTimeFormatter`는 존재하지 않는 날짜를 **보정**한다.

{% raw %}
```java
var f = DateTimeFormatter.ofPattern("yyyy-MM-dd");
LocalDate.parse("2026-02-30", f);   // 2026-02-28  (예외 없음)
LocalDate.parse("2026-04-31", f);   // 2026-04-30
```
{% endraw %}

---

## ResolverStyle 세 가지

`DateTimeFormatter`는 파싱한 필드 값을 날짜로 "해석(resolve)"할 때 `ResolverStyle`을 따른다. `ofPattern`으로 만든 formatter의 기본값은 **SMART**다.

| 스타일 | 동작 | `2026-02-30` |
|---|---|---|
| `STRICT` | 모든 필드가 유효 범위 안이어야 한다. 아니면 `DateTimeParseException` | 예외 |
| `SMART` (기본) | 일(day)이 그 달의 마지막 날을 넘으면 마지막 날로 **보정**. 월이 13이면 예외 | `2026-02-28` |
| `LENIENT` | 범위를 넘는 값을 다음 단위로 넘김 | `2026-03-02` |

SMART는 "사람이 입력한 값을 너그럽게 받는" 용도다. 월말 계산 같은 데서는 편하다. 하지만 **입력이 정확해야 하는 곳**(커서, 식별자, 감사 로그 시각)에서는 조용히 값이 바뀌는 쪽이 더 위험하다.

---

## STRICT로 바꿨더니 전부 실패한다

`withResolverStyle(ResolverStyle.STRICT)`를 붙이면 이번엔 **정상 날짜도** 실패한다.

{% raw %}
```java
var f = DateTimeFormatter.ofPattern("yyyy-MM-dd").withResolverStyle(ResolverStyle.STRICT);
LocalDate.parse("2026-02-28", f);
// java.time.format.DateTimeParseException: Text '2026-02-28' could not be parsed:
//   Unable to obtain LocalDate from TemporalAccessor: {MonthOfYear=2, DayOfMonth=28, YearOfEra=2026},ISO ...
```
{% endraw %}

원인은 패턴 문자 `y`다.

- `y` = **year-of-era**. 연대(era, BC/AD)와 함께 있어야 완전한 연도다.
- `u` = **year**. 연대 없이 그 자체로 연도다.

SMART는 era가 없으면 AD로 가정해 넘어가지만, STRICT는 "era 필드가 없으니 연도를 확정할 수 없다"고 거절한다. 그래서 STRICT와 짝은 `uuuu`다.

{% raw %}
```java
var f = DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss")
                         .withResolverStyle(ResolverStyle.STRICT);
LocalDateTime.parse("2026-02-28 00:00:00", f);   // OK
LocalDateTime.parse("2026-02-30 00:00:00", f);   // DateTimeParseException
```
{% endraw %}

`DateTimeFormatter.ISO_LOCAL_DATE` 같은 내장 상수는 이미 `uuuu`와 STRICT로 만들어져 있다. 그래서 `LocalDate.parse("2026-02-30")`은 기본 formatter로도 예외가 난다. 문제가 생기는 건 **`ofPattern`으로 직접 만든 formatter**다.

---

## 어디서 문제가 되는가

이번 리뷰의 자리는 "마지막으로 본 행의 시각"을 커서로 받는 API였다. 클라이언트가 보낸 커서가 보정되면 이런 일이 생긴다.

{% raw %}
```text
클라이언트 커서:  2026-02-30 00:00:00  (잘못된 값, 버그든 조작이든)
서버 해석:        2026-02-28 00:00:00
→ 2/28 ~ 2/29 사이 행이 다시 내려온다. 또는 비교 조건에 따라 건너뛴다.
```
{% endraw %}

페이징이라 데이터 손상은 없다. 하지만 "잘못된 입력은 400으로 거절한다"는 API 계약과 어긋난다. 같은 패턴이 더 아픈 곳은 이런 데다.

- **감사 로그·증적의 시각 필드**: 입력된 시각이 바뀐 채 저장되면 나중에 원본과 대조가 안 된다.
- **만료일·유효기간**: `02-30`을 `02-28`로 받아 이틀 짧게 설정된다.
- **DB 조회 조건**: `BETWEEN`의 경계가 소리 없이 이동한다.

---

## 정리: 패턴을 직접 만들면 두 가지를 같이 붙인다

{% raw %}
```java
// 입력 검증이 필요한 곳의 formatter
private static final DateTimeFormatter CURSOR =
        DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss")
                         .withResolverStyle(ResolverStyle.STRICT);
```
{% endraw %}

| 항목 | 내용 |
|---|---|
| 기본값 | `ofPattern`은 SMART. 없는 날짜를 월말로 보정한다 |
| STRICT | `withResolverStyle(ResolverStyle.STRICT)` |
| 패턴 | STRICT와 함께 쓸 때는 `yyyy` 대신 `uuuu` |
| 내장 상수 | `ISO_LOCAL_DATE` 등은 이미 STRICT + `uuuu` |
| 적용 대상 | 커서, 식별자, 증적, 기간처럼 입력이 바뀌면 안 되는 곳 |
| 예외 | 사용자 편의 입력(월말 자동 보정이 의도인 곳)은 SMART 유지 |

이번 건은 해당 API가 곧 제거될 예정이어서 Minor로 남기고 수정을 보류했다. 하지만 `ofPattern("yyyy-...")`로 만든 formatter가 입력 검증 자리에 있다면, 한 번은 `2026-02-30`을 넣어 볼 만하다.
