package com.capstone.handler;

import com.capstone.dto.CityRecognitionResponseDto;
import com.capstone.dto.SignLanguageInputDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

//백엔드에서 추론 서버의 웹소켓!!
@Component
public class InferenceClientHandler extends TextWebSocketHandler {

    private static final Logger logger = LoggerFactory.getLogger(InferenceClientHandler.class);

    private WebSocketSession inferenceSession;
    private final ObjectMapper objectMapper;
    private final PredictionClientHandler predictionClientHandler;

    // Key: Spring WebSocket Session ID
    private final ConcurrentMap<String, WebSocketSession> feSessionMap = new ConcurrentHashMap<>();

    public InferenceClientHandler(ObjectMapper objectMapper, @Lazy PredictionClientHandler predictionClientHandler) {
        this.objectMapper = objectMapper;
        this.predictionClientHandler = predictionClientHandler;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        logger.info("✅ AI 추론 서버(Python)와 연결되었습니다: {}", session.getUri());
        this.inferenceSession = session;
    }

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();

        try {
            // 1. AI 응답 JSON 파싱
            CityRecognitionResponseDto aiResponse = objectMapper.readValue(payload, CityRecognitionResponseDto.class);

            // 2. 응답 대상(FE 세션) 찾기
            // AI 서버는 요청받았던 session ID를 그대로 돌려줘야 함
            String feSessionId = aiResponse.getSessionId();

            if (feSessionId != null) {
                WebSocketSession feSession = feSessionMap.get(feSessionId);

                if (feSession != null && feSession.isOpen()) {
                    // 3. FE로 응답 전송
                    predictionClientHandler.sendResponseToClient(feSession, aiResponse);
                } else {
                    // 세션이 종료된 경우 맵에서 제거
                    feSessionMap.remove(feSessionId);
                    logger.warn("⚠️ 해당 FE 세션 종료됨/없음: {}", feSessionId);
                }
            } else {
                logger.warn("⚠️ AI 응답에 Session ID가 없습니다.");
            }
        } catch (Exception e) {
            logger.error("❌ AI 응답 처리 중 오류: {}", e.getMessage());
        }
    }

    /**
     * PredictionClientHandler에서 호출
     */
    public void sendToAI(SignLanguageInputDto inputDto, WebSocketSession feSession) {
        if (this.inferenceSession != null && this.inferenceSession.isOpen()) {
            try {
                // 1. 세션 매핑 저장 (중요: 요청을 보낼 때마다 갱신하거나 최초 1회 저장)
                // feSession.getId()는 Spring WebSocket의 고유 ID입니다.
                feSessionMap.put(feSession.getId(), feSession);
                logger.info("세션 아이디: {}", feSession.getId());
                String jsonPayload = objectMapper.writeValueAsString(inputDto);
                // 2. AI 서버로 전송
                this.inferenceSession.sendMessage(new TextMessage(jsonPayload));

            } catch (IOException e) {
                logger.error("❌ AI 서버 전송 실패: {}", e.getMessage());
            }
        } else {
            logger.error("❌ AI 서버와 연결되어 있지 않습니다.");
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        logger.error("⚠️ AI 추론 서버 통신 중 에러 발생: {}", exception.getMessage());
        // 에러가 발생하더라도 close()가 호출되면 afterConnectionClosed로 넘어갑니다.
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        logger.info("❌ AI 추론 서버와의 연결이 종료되었습니다. ID: {}, 상태: {}", session.getId(), status);

        // 중요: 연결이 끊겼으므로 세션 객체를 null로 초기화하여
        // sendToAI 메서드에서 끊긴 세션에 접근하지 못하도록 막습니다.
        this.inferenceSession = null;
    }
}