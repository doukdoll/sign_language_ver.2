package com.capstone.config;

import com.capstone.handler.InferenceClientHandler;
import com.capstone.handler.PredictionClientHandler;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.WebSocketHandler; // MyWebSocketHandler 주입을 위해 추가

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final WebSocketHandler myWebSocketHandler; // MyWebSocketHandler 타입 대신 WebSocketHandler 사용
    private final PredictionClientHandler predictionClientHandler;

    public WebSocketConfig(WebSocketHandler myWebSocketHandler,
                           PredictionClientHandler predictionClientHandler)
    { // MyWebSocketHandler 타입 대신 WebSocketHandler 사용
        this.myWebSocketHandler = myWebSocketHandler;
        this.predictionClientHandler = predictionClientHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        //HTTP를 통한 통신
//        registry.addHandler(myWebSocketHandler, "/sign/stream") // '/api/sign/stream' 경로에 핸들러 등록
//                .setAllowedOrigins("*"); // 모든 Origin 허용 (CORS)

        //WebSocket을 이용한 통신
        // 1. 프론트엔드(React)가 접속할 주소 설정
        // 예: ws://localhost:8080/sign/stream
        registry.addHandler(predictionClientHandler, "/sign/stream")
                .setAllowedOriginPatterns("*"); // 모든 도메인 허용 (CORS 해결)
    }
}
