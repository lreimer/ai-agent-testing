# syntax=docker/dockerfile:1
FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build

COPY agents/pom.xml ./pom.xml
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -ntp org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies \
        -DincludeScope=runtime -DoutputDirectory=/build/lib

COPY agents/src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -ntp package

FROM gcr.io/distroless/java17-debian13:nonroot
WORKDIR /app

COPY --from=build /build/lib/ ./lib/
COPY --from=build /build/target/agents-1.0-SNAPSHOT.jar ./agents.jar

ENV ADK_HOST=0.0.0.0 \
    ADK_PORT=8000 \
    GOOGLE_GENAI_USE_VERTEXAI=false
EXPOSE 8000
USER 65532:65532
ENTRYPOINT ["java", "-cp", "/app/agents.jar:/app/lib/*", "dev.lreimer.testing.AgentServer"]
