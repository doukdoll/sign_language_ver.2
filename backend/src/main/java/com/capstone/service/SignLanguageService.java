package com.capstone.service;

import com.capstone.dto.CityRecognitionResponseDto;
import com.capstone.dto.DateTimeRecognitionResponseDto;
import com.capstone.dto.PassengerRecognitionResponseDto;
import com.capstone.dto.SeatClassRecognitionResponseDto;
import com.capstone.dto.SignLanguageInputDto;
import com.capstone.dto.TripTypeRecognitionResponseDto;
import com.capstone.dto.ErrorResponseDto;
import com.capstone.dto.KeypointDto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class SignLanguageService {

    private static final Logger logger = LoggerFactory.getLogger(SignLanguageService.class);
    private RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    // 포트 5001번 확인 (파이썬 서버와 일치해야 함)
    private final String flaskUrl = "http://localhost:5001/predict_keypoints";

    public SignLanguageService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    // 메인 AI 추론 메서드 (여기는 이미 잘 되어 있어서 수정 불필요)
    public CityRecognitionResponseDto recognizeCity_with_AI(KeypointDto keypointDto, String recognitionTarget) {
        logger.info("서비스에서 수어 키포인트 데이터를 처리 중입니다.");
        logger.info("인식 대상: {}", recognitionTarget);

        CityRecognitionResponseDto response = new CityRecognitionResponseDto();
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        java.util.Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("recognitionTarget", recognitionTarget);
        requestBody.put("keypointData", keypointDto);

        HttpEntity<java.util.Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<CityRecognitionResponseDto> server_response = restTemplate.exchange(
                    flaskUrl,
                    HttpMethod.POST,
                    entity,
                    CityRecognitionResponseDto.class
            );
            response = server_response.getBody();

            if (response != null && response.getDepartureCity() == null && response.getArrivalCity() == null) {
                // 매핑 로직 필요 시 추가
            }

        } catch (HttpClientErrorException e) {
            String errorResponseJson = e.getResponseBodyAsString();
            logger.warn("클라이언트 오류 발생. Code={}, JSON={}", e.getStatusCode(), errorResponseJson);
            handleErrorResponse(response, e.getStatusCode().value(), errorResponseJson);
        } catch (HttpServerErrorException e){
            String errorResponseJson = e.getResponseBodyAsString();
            logger.error("서버 오류 발생. Code={}, JSON={}", e.getStatusCode(), errorResponseJson);
            handleErrorResponse(response, e.getStatusCode().value(), errorResponseJson);
        } catch (ResourceAccessException e) {
            logger.error("HTTP 통신 중 에러가 발생하였습니다. {}", e.getMessage());
            response.setDepartureCity("연결 오류 발생");
            response.setArrivalCity("연결 오류 발생");
        } catch (Exception e) {
            logger.error("예상치 못한 오류 발생: {}", e.getMessage(), e);
            response.setDepartureCity("알 수 없는 오류");
            response.setArrivalCity("알 수 없는 오류");
        }
        return response;
    }

    private void handleErrorResponse(CityRecognitionResponseDto response, int statusCode, String errorJson) {
        try {
            ErrorResponseDto errorDto = objectMapper.readValue(errorJson, ErrorResponseDto.class);
            logger.warn("오류 상세: [{}], {}", errorDto.getErrorCode(), errorDto.getErrorMessage());
            response.setDepartureCity("API 오류: " + statusCode);
            response.setArrivalCity("오류 원인: " + errorDto.getErrorMessage());
        } catch (Exception jsonEx) {
            logger.error("오류 응답 본문 파싱 실패: 원본 JSON = {}", errorJson);
            response.setDepartureCity("알 수 없는 오류");
            response.setArrivalCity("알 수 없는 오류");
        }
    }

    // ▼▼▼ 아래 메서드들에서 getSignLanguageData() -> getKeypoints() 로 수정함 ▼▼▼

    public CityRecognitionResponseDto recognizeCity(SignLanguageInputDto signLanguageInputDto) {
        // [수정 1] getSignLanguageData() -> getKeypoints()
        logger.info("서비스에서 수어 데이터를 처리 중입니다: {}", signLanguageInputDto.getKeypoints());
        logger.info("인식 대상: {}", signLanguageInputDto.getRecognitionTarget());

        CityRecognitionResponseDto response = new CityRecognitionResponseDto();

        if ("DEPARTURE".equalsIgnoreCase(signLanguageInputDto.getRecognitionTarget())) {
            response.setDepartureCity("서울");
            response.setArrivalCity(null);
        } else if ("ARRIVAL".equalsIgnoreCase(signLanguageInputDto.getRecognitionTarget())) {
            response.setDepartureCity(null);
            response.setArrivalCity("부산");
        } else {
            response.setDepartureCity("알 수 없는 출발지");
            response.setArrivalCity("알 수 없는 도착지");
            logger.warn("유효하지 않은 인식 대상이 수신되었습니다: {}", signLanguageInputDto.getRecognitionTarget());
        }
        return response;
    }

    public DateTimeRecognitionResponseDto recognizeDateTime(SignLanguageInputDto signLanguageInputDto) {
        // [수정 2] getSignLanguageData() -> getKeypoints()
        logger.info("서비스에서 수어 데이터를 처리 중입니다 (날짜/시간): {}", signLanguageInputDto.getKeypoints());

        DateTimeRecognitionResponseDto response = new DateTimeRecognitionResponseDto();
        response.setRecognizedDate("2025-11-05");
        response.setRecognizedTime("14:30");
        return response;
    }

    public PassengerRecognitionResponseDto recognizePassengers(SignLanguageInputDto signLanguageInputDto) {
        // [수정 3] getSignLanguageData() -> getKeypoints()
        logger.info("서비스에서 수어 데이터를 처리 중입니다 (승객 수): {}", signLanguageInputDto.getKeypoints());

        PassengerRecognitionResponseDto response = new PassengerRecognitionResponseDto();
        response.setRecognizedPassengers(2);
        return response;
    }

    public TripTypeRecognitionResponseDto recognizeTripType(SignLanguageInputDto signLanguageInputDto) {
        // [수정 4] getSignLanguageData() -> getKeypoints()
        logger.info("서비스에서 수어 데이터를 처리 중입니다 (편도/왕복): {}", signLanguageInputDto.getKeypoints());

        TripTypeRecognitionResponseDto response = new TripTypeRecognitionResponseDto();
        response.setRecognizedTripType("왕복");
        return response;
    }

    public SeatClassRecognitionResponseDto recognizeSeatClass(SignLanguageInputDto signLanguageInputDto) {
        // [수정 5] getSignLanguageData() -> getKeypoints()
        logger.info("서비스에서 수어 데이터를 처리 중입니다 (좌석 등급): {}", signLanguageInputDto.getKeypoints());

        SeatClassRecognitionResponseDto response = new SeatClassRecognitionResponseDto();
        response.setRecognizedSeatClass("일반실");
        return response;
    }
}