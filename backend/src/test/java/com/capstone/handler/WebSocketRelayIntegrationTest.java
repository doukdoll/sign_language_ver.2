package com.capstone.handler;

import com.capstone.config.WebSocketConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration;
import org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration;
import org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Import;
import org.springframework.web.socket.*;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.config.annotation.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(classes = WebSocketRelayIntegrationTest.App.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"server.servlet.context-path=/api", "spring.main.banner-mode=off"})
class WebSocketRelayIntegrationTest {
    @SpringBootConfiguration
    @EnableAutoConfiguration(exclude = {DataSourceAutoConfiguration.class, HibernateJpaAutoConfiguration.class,
            SecurityAutoConfiguration.class, UserDetailsServiceAutoConfiguration.class})
    @Import({WebSocketConfig.class, PredictionClientHandler.class, InferenceClientHandler.class})
    static class App implements WebSocketConfigurer {
        @Override public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
            // Deterministic protocol double, NOT an ONNX model or Python server.
            registry.addHandler(new TextWebSocketHandler() {
                final ObjectMapper mapper = new ObjectMapper();
                @Override protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
                    ObjectNode response = (ObjectNode) mapper.readTree(message.getPayload());
                    switch (response.path("type").asText()) {
                        case "START_SESSION" -> response.put("type", "SESSION_STARTED");
                        case "RESET_SESSION" -> response.put("type", "SESSION_RESET");
                        case "END_SESSION" -> response.put("type", "SESSION_ENDED");
                        case "KEYPOINT_FRAME" -> {
                            response.put("type", "RESULT").put("recognizedProb", 98.7);
                            boolean departure = "DEPARTURE".equals(response.path("recognitionTarget").asText());
                            response.put("departureCity", departure ? "서울역" : null);
                            response.put("arrivalCity", departure ? null : "부산역");
                            response.remove("keypoints");
                        }
                        default -> throw new IllegalArgumentException("Unexpected request");
                    }
                    session.sendMessage(new TextMessage(response.toString()));
                }
            }, "/test-ai");
        }
    }

    static class Inbox extends TextWebSocketHandler {
        final LinkedBlockingQueue<JsonNode> messages = new LinkedBlockingQueue<>();
        @Override protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
            messages.add(new ObjectMapper().readTree(message.getPayload()));
        }
        JsonNode take() throws Exception {
            JsonNode value = messages.poll(5, TimeUnit.SECONDS);
            assertNotNull(value, "Timed out waiting for WebSocket response");
            return value;
        }
    }

    @LocalServerPort int port;
    @Autowired InferenceClientHandler relay;
    final ObjectMapper mapper = new ObjectMapper();

    ObjectNode request(String type, String id, int revision, String target) {
        ObjectNode message = mapper.createObjectNode().put("protocolVersion", 1).put("type", type)
                .put("revision", revision).put("timestamp", 1).put("recognitionTarget", target);
        if (id != null) message.put("sessionId", id);
        if ("KEYPOINT_FRAME".equals(type)) {
            message.put("frameIndex", 0);
            var points = message.putArray("keypoints");
            for (int i = 0; i < 137; i++) points.addArray().add(0.1).add(0.2).add(1);
        }
        return message;
    }

    void send(WebSocketSession socket, ObjectNode message) throws Exception {
        socket.sendMessage(new TextMessage(message.toString()));
    }

    @Test void twoRealBrowserSocketsRoundTripThroughSharedAiSocket() throws Exception {
        var client = new StandardWebSocketClient();
        String base = "ws://localhost:" + port + "/api";
        Inbox a = new Inbox(), b = new Inbox();
        try (WebSocketSession ai = client.execute(relay, base + "/test-ai").get(5, TimeUnit.SECONDS);
             WebSocketSession feA = client.execute(a, base + "/sign/stream").get(5, TimeUnit.SECONDS);
             WebSocketSession feB = client.execute(b, base + "/sign/stream").get(5, TimeUnit.SECONDS)) {
            send(feA, request("START_SESSION", null, 0, "DEPARTURE"));
            send(feB, request("START_SESSION", null, 0, "ARRIVAL"));
            JsonNode ackA = a.take(), ackB = b.take();
            assertEquals("SESSION_STARTED", ackA.path("type").asText());
            assertEquals("SESSION_STARTED", ackB.path("type").asText());
            String idA = ackA.path("sessionId").asText(), idB = ackB.path("sessionId").asText();
            assertNotEquals(idA, idB);
            send(feA, request("KEYPOINT_FRAME", idA, 0, "DEPARTURE"));
            send(feB, request("KEYPOINT_FRAME", idB, 0, "ARRIVAL"));
            assertEquals("서울역", a.take().path("departureCity").asText());
            assertEquals("부산역", b.take().path("arrivalCity").asText());
            send(feA, request("RESET_SESSION", idA, 1, "ARRIVAL"));
            assertEquals("SESSION_RESET", a.take().path("type").asText());
            send(feA, request("KEYPOINT_FRAME", idA, 1, "ARRIVAL"));
            assertEquals("부산역", a.take().path("arrivalCity").asText());
            send(feA, request("KEYPOINT_FRAME", idB, 1, "ARRIVAL"));
            assertEquals("SESSION_MISMATCH", a.take().path("errorCode").asText());
            ai.close();
            assertEquals("AI_UNAVAILABLE", a.take().path("errorCode").asText());
            assertEquals("AI_UNAVAILABLE", b.take().path("errorCode").asText());
        }
    }
}
