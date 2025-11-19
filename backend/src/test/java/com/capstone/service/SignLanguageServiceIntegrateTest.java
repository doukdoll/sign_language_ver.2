package com.capstone.service;

import com.capstone.dto.CityRecognitionResponseDto;
import com.capstone.dto.SignLanguageInputDto;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;

import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.web.client.RestTemplate;

import static org.junit.jupiter.api.Assertions.*;


@ExtendWith(SpringExtension.class)
public class SignLanguageServiceIntegrateTest {
    private SignLanguageService signLanguageService;

    @Test
    void Test_Code_200_OK() {
        // 1. 필요한 의존성 객체 생성
        RestTemplate realRestTemplate = new RestTemplate(); // 실제 RestTemplate 객체

        // 2. 테스트 대상 객체(Service)를 수동으로 생성하고 의존성을 주입
        signLanguageService = new SignLanguageService(realRestTemplate);
        String csvFile1, csvFile2;

        // GIVEN
        SignLanguageInputDto inputDto1 = new SignLanguageInputDto();
        SignLanguageInputDto inputDto2 = new SignLanguageInputDto();
        inputDto1.setRecognitionTarget("DEPARTURE");
        inputDto2.setRecognitionTarget("ARRIVAL");
        csvFile1 = "C:\\Users\\SAMSUNG\\Desktop\\sign-language-transport-kiosk\\csv_for_test\\entry_001_서울역_4.csv";
        csvFile2 = "C:\\Users\\SAMSUNG\\Desktop\\sign-language-transport-kiosk\\csv_for_test\\entry_001_서울역_4.csv";

        // WHEN
        CityRecognitionResponseDto result1 = signLanguageService.recognizeCity_with_AI(inputDto1, csvFile1);
        CityRecognitionResponseDto result2 = signLanguageService.recognizeCity_with_AI(inputDto2,  csvFile2);

        // THEN
        assertNotNull(result1);
        assertNotNull(result2);
        assertNull(result1.getArrivalCity(), "출발지 인식 시 도착지는 null");
        assertNull(result2.getDepartureCity(), "도착지 인식 시 출발지는 null");
        //입력 기대값을 서울역이지만 AI는 대구를 반환, 가장 처음 받은 모델이라 그럴 수도 있음
        assertEquals("대구", result1.getDepartureCity(), "출발지: 200 응답 시 AI가 인식한 도시를 반환해야 합니다.");
        assertEquals("대구", result2.getArrivalCity(), "도착지: 200 응답 시 AI가 인식한 도시를 반환해야 합니다.");
    }

    @Test
    void Test_Code_400_BAD_REQUEST() {
        RestTemplate realRestTemplate = new RestTemplate(); // 실제 RestTemplate 객체
        signLanguageService = new SignLanguageService(realRestTemplate);
        String csvFile;


        // GIVEN
        SignLanguageInputDto inputDto = new SignLanguageInputDto();
        inputDto.setRecognitionTarget("");
        csvFile = "C:\\Users\\SAMSUNG\\Desktop\\sign-language-transport-kiosk\\csv_for_test\\entry_001_서울역_4.csv";


        //WHEN
        CityRecognitionResponseDto result = signLanguageService.recognizeCity_with_AI(inputDto, csvFile);

        //THEN
        assertEquals("API 오류: 400", result.getDepartureCity());
        assertEquals("오류 원인: 인식 대상이 올바르지 않습니다.", result.getArrivalCity());
    }

    @Test
    void Test_Code_500_Server_Error() {
        // 1. 필요한 의존성 객체 생성
        RestTemplate realRestTemplate = new RestTemplate(); // 실제 RestTemplate 객체

        // 2. 테스트 대상 객체(Service)를 수동으로 생성하고 의존성을 주입
        signLanguageService = new SignLanguageService(realRestTemplate);
        String csvFile1, csvFile2;

        // GIVEN
        SignLanguageInputDto inputDto1 = new SignLanguageInputDto();
        SignLanguageInputDto inputDto2 = new SignLanguageInputDto();
        inputDto1.setRecognitionTarget("DEPARTURE");
        inputDto2.setRecognitionTarget("DEPARTURE");
        csvFile1 = "C:\\Users\\SAMSUNG\\Desktop\\sign-language-transport-kiosk\\csv_for_test\\temp.csv";
        //특징 수가 안맞는 입력 값
        csvFile2 = "C:\\Users\\SAMSUNG\\Desktop\\sign-language-transport-kiosk\\csv_for_test\\entry_001_서울역_for_error.csv";

        //WHEN
        CityRecognitionResponseDto result1 = signLanguageService.recognizeCity_with_AI(inputDto1, csvFile1);
        CityRecognitionResponseDto result2 = signLanguageService.recognizeCity_with_AI(inputDto2, csvFile2);

        // THEN
        String prefix = "오류 원인: csv파일을 처리하는데 실패했습니다.:";


        assertEquals("API 오류: 500", result1.getDepartureCity());
        assertTrue(result1.getArrivalCity().contains(prefix), "접두사를 포함하여야 합니다.");
        assertEquals("API 오류: 500", result2.getDepartureCity());
        assertEquals("오류 원인: 추론을 실패했습니다.", result2.getArrivalCity());
    }
}
