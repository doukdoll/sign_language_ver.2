package com.capstone.service;

import com.capstone.entity.TrainSchedule;
import com.capstone.repository.TrainScheduleRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.core.io.ClassPathResource;
import com.opencsv.CSVReader;
import com.opencsv.exceptions.CsvValidationException;

import java.io.InputStreamReader;
import java.io.IOException;
import java.time.DayOfWeek;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.HashMap;
import java.util.Map;
import java.time.format.DateTimeParseException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Profile("!test") // 테스트 환경에서는 실행되지 않도록 설정
@Component
public class TrainDataLoader {

    private static final Logger logger = LoggerFactory.getLogger(TrainDataLoader.class);

    private final TrainScheduleRepository trainScheduleRepository;

    // CSV 파일에 있는 역 이름을 순서대로 매핑
    private static final List<String> STATIONS_DOWN = Arrays.asList(
            "행신", "서울역", "영등포", "수원", "광명", "천안아산", "오송", "대전", "김천구미",
            "서대구", "동대구", "경주", "울산", "경산", "밀양", "물금", "구포", "부산"
    );
    private static final List<String> STATIONS_UP = Arrays.asList(
            "부산", "구포", "물금", "밀양", "경산", "울산", "경주", "동대구",
            "서대구", "김천구미", "대전", "오송", "천안아산", "광명", "수원", "영등포", "서울역", "행신", "포항"
    );

    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("H:mm");

    public TrainDataLoader(TrainScheduleRepository trainScheduleRepository) {
        this.trainScheduleRepository = trainScheduleRepository;
    }

    @PostConstruct
    public void loadTrainData() {
        if (trainScheduleRepository.count() == 0) { // 데이터가 비어있을 때만 로드
            System.out.println("Loading train schedule data...");
            loadCsvData("gyeongbu_hahaeng.csv", STATIONS_DOWN, false); // 하행 방향
            loadCsvData("gyeongbu_sanghaeng.csv", STATIONS_UP, true); // 상행 방향
            System.out.println("Train schedule data loaded. Total: " + trainScheduleRepository.count() + " schedules.");
        } else {
            System.out.println("Train schedule data already exists. Skipping load.");
        }
    }

    private void loadCsvData(String filename, List<String> stationOrder, boolean isUpDirection) {
        try {
            ClassPathResource resource = new ClassPathResource(filename);
            try (CSVReader reader = new CSVReader(new InputStreamReader(resource.getInputStream(), "UTF-8"))) {
                String[] header = reader.readNext(); // 헤더 읽기
                System.out.println("CSV Header: " + Arrays.toString(header)); // 디버깅용 로그 추가
                // 헤더 맵 생성
                Map<String, Integer> headerMap = new HashMap<>();
                for (int i = 0; i < header.length; i++) {
                    headerMap.put(header[i].trim(), i);
                }

                // 각 역의 순서를 매핑
                Map<String, Integer> stationOrderMap = new HashMap<>();
                for (int i = 0; i < stationOrder.size(); i++) {
                    stationOrderMap.put(stationOrder.get(i), i);
                }

                // 각 행의 데이터 처리
                String[] record;
                while ((record = reader.readNext()) != null) {
                    // CSV 파일의 각 행(record)에서 모든 출발-도착 역 쌍에 대해 스케줄 생성
                    for (String depStationName : stationOrderMap.keySet()) {
                        for (String arrStationName : stationOrderMap.keySet()) {
                            // 출발역과 도착역이 다르고, 방향성이 일치하는 경우에만 처리
                            if (!depStationName.equals(arrStationName) &&
                                ((isUpDirection && stationOrderMap.get(depStationName) < stationOrderMap.get(arrStationName)) ||
                                 (!isUpDirection && stationOrderMap.get(depStationName) > stationOrderMap.get(arrStationName)))) {

                                // CSV 헤더에서 해당 역의 시간 컬럼 인덱스 찾기
                                Integer depTimeColIndex = headerMap.get(depStationName);
                                Integer arrTimeColIndex = headerMap.get(arrStationName);

                                if (depTimeColIndex != null && arrTimeColIndex != null) {
                                    String departureTimeStr = record[depTimeColIndex].trim();
                                    String arrivalTimeStr = record[arrTimeColIndex].trim();

                                    // 시간이 비어있지 않은 경우에만 스케줄 생성
                                    if (!departureTimeStr.isBlank() && !arrivalTimeStr.isBlank()) {
                                        String trainNumber = getCsvValue(headerMap, record, "열차번호");
                                        String trainName = getCsvValue(headerMap, record, "편성");
                                        String runningDays = getCsvValue(headerMap, record, "운행요일");

                                        try {
                                            // 날짜는 임시로 현재 년월일을 사용하고, 시간만 CSV에서 가져옴
                                            // 실제 서비스에서는 사용자가 선택한 날짜와 조합해야 함
                                            LocalDate today = LocalDate.now();
                                            LocalDateTime departureTime = LocalDateTime.of(today, LocalTime.parse(departureTimeStr, DateTimeFormatter.ofPattern("H:mm")));
                                            LocalDateTime arrivalTime = LocalDateTime.of(today, LocalTime.parse(arrivalTimeStr, DateTimeFormatter.ofPattern("H:mm")));

                                            // 열차 운행 요일 필터링 로직 추가 (추후 구현 예정)
                                            // 현재는 모든 요일로 가정

                                            // 데이터 저장
                                            trainScheduleRepository.save(TrainSchedule.builder()
                                                    .trainNumber(trainNumber)
                                                    .trainName(trainName)
                                                    .departureStation(depStationName)
                                                    .arrivalStation(arrStationName)
                                                    .departureTime(departureTime)
                                                    .arrivalTime(arrivalTime)
                                                    .operatingDays(runningDays)
                                                    .price(50000) // 임시로 가격 설정
                                                    .build());
                                        } catch (DateTimeParseException e) {
                                            logger.warn("Error parsing time for train {}: {} or {}. Skipping schedule. Error: {}", trainNumber, departureTimeStr, arrivalTimeStr, e.getMessage());
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } catch (IOException | CsvValidationException e) {
            System.err.println("Failed to load train data from " + filename + ": " + e.getMessage());
            e.printStackTrace();
        }
    }

    private String getCsvValue(Map<String, Integer> headerMap, String[] record, String headerName) {
        Integer index = headerMap.get(headerName);
        if (index == null) {
            throw new IllegalArgumentException("CSV header '" + headerName + "' not found.");
        }
        if (index >= record.length) {
            // 해당 인덱스에 데이터가 없는 경우 (예: 마지막 컬럼)
            return "";
        }
        return record[index].trim();
    }
}
