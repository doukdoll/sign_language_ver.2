# 1단계: 빌드 스테이지
FROM gradle:8.14.4-jdk17 AS builder
WORKDIR /app

# 설정 파일 복사
COPY build.gradle.kts .
COPY settings.gradle.kts .

# 소스 코드 복사 및 내장 gradle 명령어로 빌드
COPY src src
RUN gradle build -x test --no-daemon

# 2단계: 실행 스테이지
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]