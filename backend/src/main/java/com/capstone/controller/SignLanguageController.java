package com.capstone.controller;

import com.capstone.dto.*;
import com.capstone.service.SignLanguageService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/signlanguage")
public class SignLanguageController {

    private static final Logger logger = LoggerFactory.getLogger(SignLanguageController.class);
    private final SignLanguageService signLanguageService;

    public SignLanguageController(SignLanguageService signLanguageService) {
        this.signLanguageService = signLanguageService;
    }

    @PostMapping("/recognize")
    public ResponseEntity<CityRecognitionResponseDto> recognizeCity(@Valid @RequestBody SignLanguageInputDto signLanguageInputDto) {
        // [수정 1] getSignLanguageData() -> getKeypoints()
        logger.info("Received sign language recognition request: {}", signLanguageInputDto.getKeypoints());

        CityRecognitionResponseDto response = signLanguageService.recognizeCity(signLanguageInputDto);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/datetime")
    public ResponseEntity<DateTimeRecognitionResponseDto> recognizeDateTime(@Valid @RequestBody SignLanguageInputDto signLanguageInputDto) {
        // [수정 2] getSignLanguageData() -> getKeypoints()
        logger.info("날짜/시간 수어 인식 요청 수신: {}", signLanguageInputDto.getKeypoints());

        DateTimeRecognitionResponseDto response = signLanguageService.recognizeDateTime(signLanguageInputDto);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/passengers")
    public ResponseEntity<PassengerRecognitionResponseDto> recognizePassengers(@Valid @RequestBody SignLanguageInputDto signLanguageInputDto) {
        // [수정 3] getSignLanguageData() -> getKeypoints()
        logger.info("승객 수 수어 인식 요청 수신: {}", signLanguageInputDto.getKeypoints());

        PassengerRecognitionResponseDto response = signLanguageService.recognizePassengers(signLanguageInputDto);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/triptype")
    public ResponseEntity<TripTypeRecognitionResponseDto> recognizeTripType(@Valid @RequestBody SignLanguageInputDto signLanguageInputDto) {
        // [수정 4] getSignLanguageData() -> getKeypoints()
        logger.info("편도/왕복 수어 인식 요청 수신: {}", signLanguageInputDto.getKeypoints());

        TripTypeRecognitionResponseDto response = signLanguageService.recognizeTripType(signLanguageInputDto);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/seatclass")
    public ResponseEntity<SeatClassRecognitionResponseDto> recognizeSeatClass(@Valid @RequestBody SignLanguageInputDto signLanguageInputDto) {
        // [수정 5] getSignLanguageData() -> getKeypoints()
        logger.info("좌석 등급 수어 인식 요청 수신: {}", signLanguageInputDto.getKeypoints());

        SeatClassRecognitionResponseDto response = signLanguageService.recognizeSeatClass(signLanguageInputDto);
        return ResponseEntity.ok(response);
    }
}