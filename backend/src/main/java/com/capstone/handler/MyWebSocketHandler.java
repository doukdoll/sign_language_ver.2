package com.capstone.handler;

import com.capstone.dto.CityRecognitionResponseDto;
import com.capstone.dto.SignLanguageInputDto; // 아까 수정한 DTO 사용
import com.capstone.dto.KeypointDto;
import com.capstone.service.SignLanguageService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.concurrent.CopyOnWriteArrayList;

@Component
public class MyWebSocketHandler extends TextWebSocketHandler {

    private static final Logger logger = LoggerFactory.getLogger(MyWebSocketHandler.class);
    private final SignLanguageService signLanguageService;
    private final ObjectMapper objectMapper;
    private final CopyOnWriteArrayList<WebSocketSession> sessions = new CopyOnWriteArrayList<>();

    public MyWebSocketHandler(SignLanguageService signLanguageService, ObjectMapper objectMapper) {
        this.signLanguageService = signLanguageService;
        this.objectMapper = objectMapper;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        sessions.add(session);
        logger.info("WebSocket 연결 수립: {}", session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();

        // 로그로 데이터 크기 확인 (성공 시 2000 이상 나와야 함)
        // logger.info("메시지 수신: 세션 ID={}, 페이로드 크기={}", session.getId(), payload.length());

        try {
            // 1. [핵심 수정] Map 대신 아까 수정한 SignLanguageInputDto로 바로 파싱
            // 이렇게 하면 "keypoints" 필드가 자동으로 매핑됩니다.
            SignLanguageInputDto inputDto = objectMapper.readValue(payload, SignLanguageInputDto.class);

            // 2. 데이터 검증: 키포인트가 없으면 처리 중단 (에러 방지)
            if (inputDto.getKeypoints() == null || inputDto.getKeypoints().isEmpty()) {
                // logger.debug("빈 키포인트 데이터 수신 (무시함)");
                return;
            }

            // 3. 파이썬 서버로 보낼 DTO 생성 및 데이터 옮기기
            KeypointDto keypointDto = new KeypointDto();
            keypointDto.setKeypoints(inputDto.getKeypoints());

            // 4. 인식 대상 가져오기 (없으면 기본값 처리 등은 서비스에서)
            String recognitionTarget = inputDto.getRecognitionTarget();

            // 5. 서비스 호출 (AI 추론 요청)
            CityRecognitionResponseDto response = signLanguageService.recognizeCity_with_AI(keypointDto, recognitionTarget);

            // 6. 응답 전송
            String jsonResponse = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(jsonResponse));

            // 성공 로그 (너무 많이 뜨면 주석 처리하세요)
            logger.info("AI 응답 전송 완료: {}", response.getDepartureCity());

        } catch (IOException e) {
            logger.error("메시지 처리 중 I/O 오류: {}", e.getMessage());
        } catch (Exception e) {
            logger.error("WebSocket 예외 발생: {}", e.getMessage());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        sessions.remove(session);
        logger.info("WebSocket 연결 종료: {}", session.getId());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        logger.error("WebSocket 전송 오류: {}", exception.getMessage());
    }
}