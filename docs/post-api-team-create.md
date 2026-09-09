---
title: "[POST] api/team/create"
grand_parent: "기타"
parent: "SPOTY-PROJECT(종료)"
nav_order: 1
permalink: "/notes/post-api-team-create/"
---

#### /team/create

- 사용자는 팀을 생성할 수 있다.

- 팀을 생성하면 권한은 팀장(LEADER)으로 상승한다.

Request : form-data 형식으로 보내야 함.

|   |   |   |
| --- | --- | --- |
| KEY | VALUE | DISCRIPTION |
| teamInfo | {<br>"teamName": String,<br>"intro": String,<br>"area": String,<br>"leaderId": Long<br>} | 팀 정보.  |
| logoFile | FILE | 로고 파일.<br>png, pvg, jpg로 확장자 제한 |

예제

- Request Body

|   |   |
| --- | --- |
| KEY | VALUE |
| teamInfo | {<br>"teamName": "TEST TEAM",<br>"intro": "HIHI",<br>"area": "area",<br>"leaderId": 1<br>} |
| logoFile | FILE.PNG |

- Response

|   |
| --- |
|   |
| {<br>"id": 17,<br>"teamName": "TEST TEAM",<br>"logo": "TEST TEAM.png",<br>"intro": "HIHI",<br>"area": "area",<br>"leaderId": 1,<br>"formationName": "4421"<br>} |

---
