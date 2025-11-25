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
import java.util.concurrent.CopyOnWriteArrayList;


//백엔드와 프론트엔드의 웹소켓!!
@Component
public class PredictionClientHandler extends TextWebSocketHandler {

    private static final Logger logger = LoggerFactory.getLogger(PredictionClientHandler.class);

    private final InferenceClientHandler inferenceClientHandler;
    private final CopyOnWriteArrayList<WebSocketSession> sessions = new CopyOnWriteArrayList<>();
    private final ObjectMapper objectMapper;

    public PredictionClientHandler(@Lazy InferenceClientHandler inferenceClientHandler, ObjectMapper objectMapper) {
        this.inferenceClientHandler = inferenceClientHandler;
        this.objectMapper = objectMapper;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        sessions.add(session);
        logger.info("✅ FE-BE WebSocket 연결 수립: {}", session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();

        try {
            // 1. JSON 파싱
            SignLanguageInputDto inputDto = objectMapper.readValue(payload, SignLanguageInputDto.class);

            // 2. 메시지 타입에 따른 분기 처리
            if ("START_SESSION".equals(inputDto.getType())) {
                handleStartSession(session, inputDto);
            } else if ("KEYPOINT_FRAME".equals(inputDto.getType())) {
                handleKeypointFrame(session, inputDto);
            } else {
                logger.warn("⚠️ 알 수 없는 메시지 타입: {}", inputDto.getType());
            }

        } catch (IOException e) {
            logger.error("❌ JSON 파싱 오류: {}", e.getMessage());
        } catch (Exception e) {
            logger.error("❌ WebSocket 처리 중 예외 발생: {}", e.getMessage());
        }
    }

    /**
     * 처리 로직 1: 세션 시작 (초기화)
     */
    private void handleStartSession(WebSocketSession session, SignLanguageInputDto dto) {
        logger.info("🚀 세션 시작 요청 받음 (FE SessionId: {}, Target: {})",
                dto.getSessionId(), dto.getRecognitionTarget());
        dto.setSessionId(session.getId());
        inferenceClientHandler.sendToAI(dto, session);
    }

    /**
     * 처리 로직 2: 키포인트 프레임 전송
     */
    private void handleKeypointFrame(WebSocketSession session, SignLanguageInputDto inputDto) throws IOException {
        // 데이터 유효성 검증
        if (inputDto.getKeypoints() == null || inputDto.getKeypoints().isEmpty()) {
            return;
        }

        // 3. AI 서버로 보낼 데이터 준비 (feSessionId를 위한 sessionId로 교체)
        SignLanguageInputDto sendInputDto = new SignLanguageInputDto();

        sendInputDto.setType(inputDto.getType());
        sendInputDto.setFrameIndex(inputDto.getFrameIndex());
        sendInputDto.setTimestamp(inputDto.getTimestamp());
        sendInputDto.setRecognitionTarget(inputDto.getRecognitionTarget());
        sendInputDto.setSessionId(session.getId());
        sendInputDto.setKeypoints(inputDto.getKeypoints());

        // (선택) 프론트에서 보낸 recognitionTarget도 AI가 필요하다면 추가
        // keypointDto.setTarget(inputDto.getRecognitionTarget());

        // 4. AI 핸들러에게 데이터 포워딩
        inferenceClientHandler.sendToAI(sendInputDto, session);
    }

    /**
     * 5. [응답 메서드] InferenceClientHandler -> FE 전송
     */
    public void sendResponseToClient(WebSocketSession feSession, CityRecognitionResponseDto resultDto) {
        try {
            if (feSession != null && feSession.isOpen()) {
                String jsonResponse = objectMapper.writeValueAsString(resultDto);
                feSession.sendMessage(new TextMessage(jsonResponse));
            }
        } catch (IOException e) {
            logger.error("❌ 결과 전송 실패: {}", e.getMessage());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessions.remove(session);
        logger.info("👋 FE-BE WebSocket 연결 종료: {}", session.getId());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        logger.error("⚠️ FE-BE 통신 에러 발생 (ID: {}): {}", session.getId(), exception.getMessage());

        // 필요하다면 세션 종료 시도
        if (session.isOpen()) {
            try {
                session.close();
            } catch (Exception e) {
                // close 실패 시 로그만 남김
                logger.warn("세션 종료 중 오류: {}", e.getMessage());
            }
        }
    }
}