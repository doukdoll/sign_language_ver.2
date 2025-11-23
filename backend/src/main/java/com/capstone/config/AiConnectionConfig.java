package com.capstone.config;

import com.capstone.handler.InferenceClientHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.client.WebSocketConnectionManager;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class AiConnectionConfig {

    private final InferenceClientHandler inferenceClientHandler;

    @Bean
    public WebSocketConnectionManager wsConnectionManager() {
        // 1. Flask 주소 (ws://IP:PORT/경로)
        String aiServerUrl = "ws://localhost:5001/ws/predict";

        // 2. StandardWebSocketClient: Spring이 클라이언트가 되게 해주는 객체
        StandardWebSocketClient client = new StandardWebSocketClient();

        // 3. 매니저 생성 (Client, Handler, URL 연결)
        WebSocketConnectionManager manager = new WebSocketConnectionManager(
                client,
                inferenceClientHandler, // 기존 핸들러 재사용
                aiServerUrl
        );

        // 4. 자동 연결 설정
        manager.setAutoStartup(true);

        log.info("🔌 AI 서버 연결 관리자가 시작되었습니다. 대상: {}", aiServerUrl);
        return manager;
    }
}
