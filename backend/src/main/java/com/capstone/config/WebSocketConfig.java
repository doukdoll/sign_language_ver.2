package com.capstone.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.WebSocketHandler; // MyWebSocketHandler 주입을 위해 추가

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final WebSocketHandler myWebSocketHandler; // MyWebSocketHandler 타입 대신 WebSocketHandler 사용

    public WebSocketConfig(WebSocketHandler myWebSocketHandler) { // MyWebSocketHandler 타입 대신 WebSocketHandler 사용
        this.myWebSocketHandler = myWebSocketHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(myWebSocketHandler, "/sign/stream") // '/api/sign/stream' 경로에 핸들러 등록
                .setAllowedOrigins("*"); // 모든 Origin 허용 (CORS)
    }
}
