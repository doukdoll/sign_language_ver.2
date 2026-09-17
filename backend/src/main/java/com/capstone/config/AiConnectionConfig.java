package com.capstone.config;

import com.capstone.handler.InferenceClientHandler;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;

import java.util.concurrent.CompletableFuture;

/** Retry a failed AI connection without replaying old users' sessions. */
@Configuration
@EnableScheduling
public class AiConnectionConfig {
    private final InferenceClientHandler handler;
    private final StandardWebSocketClient client = new StandardWebSocketClient();
    private CompletableFuture<WebSocketSession> attempt;
    private boolean stopped;

    @Value("${ai-server.ws-url:ws://localhost:5001/ws/predict}")
    private String url;

    public AiConnectionConfig(InferenceClientHandler handler) { this.handler = handler; }

    @Scheduled(fixedDelayString = "${ai-server.reconnect-delay-ms:5000}")
    public synchronized void reconnect() {
        if (stopped || handler.isConnected() || (attempt != null && !attempt.isDone())) return;
        attempt = client.execute(handler, url);
    }

    @PreDestroy
    public synchronized void stop() {
        stopped = true;
        if (attempt != null) attempt.whenComplete((session, error) -> {
            if (session != null) {
                try { session.close(); } catch (java.io.IOException ignored) { }
            }
        });
    }
}
