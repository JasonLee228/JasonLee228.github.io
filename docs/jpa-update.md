---
title: "jpa update"
grand_parent: "기타"
parent: "SPOTY-PROJECT(종료)"
nav_order: 2
permalink: "/notes/jpa-update/"
---

@Transactional 어노테이션 남발의 문제점인가,,,

{% raw %}
```java
public TeamDto create(TeamSaveDto req, MultipartFile logoFile) {

        req.setFormationName("4421"); // default formationName = 4421;
        Team entity = toEntity(req);
        teamRepository.save(entity);

        User leaderUser = userRepository.getById(entity.getLeaderUser().getId());

        // user team update
        updateUserTeam(leaderUser, entity);

        // user role update
        updateRoleLeader(leaderUser.getId());

        String extension = getExtension(logoFile.getOriginalFilename());

        try {

            updateLogo(logoFile, entity.getId(), extension);

        } catch (IOException e) {
            log.error(e.getMessage());
        }

        Optional<Team> resEntity = teamRepository.findById(entity.getId());

        TeamDto res = TeamDto.builder()
                .entity(resEntity.get()).build();
        return res;
    }

    @Transactional
    private void updateUserTeam(User user, Team team) {

        user.setTeam(team);


    }

    @Transactional
    private void updateRoleLeader(Long leaderId) {

        Optional<User> leaderUser = userRepository.findById(leaderId);
        leaderUser.get().setRole(Role.ROLE_LEADER);
        // userRepository.save(leaderUser.get()); // 주석 안 풀면 동작 안함

    }
```
{% endraw %}

위처럼 있는 코드에서 원래 원하는 실행은 save → update → update 인데, 

team create 이후에 user update 두 건이 안 된다. 왤까유~?
