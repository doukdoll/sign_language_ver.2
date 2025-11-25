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

@Profile("!test") // 테스트 환경에서는 실행되지 않도록 설정
@Component
public class TrainDataLoader {

    private final TrainScheduleRepository trainScheduleRepository;

    // CSV 파일에 있는 역 이름을 순서대로 매핑
    private static final List<String> STATIONS_DOWN = Arrays.asList(
            "행신", "서울", "영등포", "수원", "광명", "천안아산", "오송", "대전", "김천구미",
            "서대구", "동대구", "경주", "울산", "경산", "밀양", "물금", "구포", "부산"
    );
    private static final List<String> STATIONS_UP = Arrays.asList(
            "부산", "구포", "물금", "밀양", "경산", "울산", "경주", "동대구",
            "서대구", "김천구미", "대전", "오송", "천안아산", "광명", "수원", "영등포", "서울", "행신"
    );

    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("H:mm");

    public TrainDataLoader(TrainScheduleRepository trainScheduleRepository) {
        this.trainScheduleRepository = trainScheduleRepository;
    }

    @PostConstruct
    public void loadTrainData() {
        if (trainScheduleRepository.count() == 0) { // 데이터가 비어있을 때만 로드
            System.out.println("Loading train schedule data...");
            loadCsvData("경부선하행.csv", STATIONS_DOWN);
            loadCsvData("경부선상행.csv", STATIONS_UP);
            System.out.println("Train schedule data loaded. Total: " + trainScheduleRepository.count() + " schedules.");
        } else {
            System.out.println("Train schedule data already exists. Skipping load.");
        }
    }

    private void loadCsvData(String filename, List<String> stationOrder) {
        try {
            ClassPathResource resource = new ClassPathResource(filename);
            try (CSVReader reader = new CSVReader(new InputStreamReader(resource.getInputStream(), "UTF-8"))) {
                String[] header = reader.readNext(); // 헤더 읽기
                Map<String, Integer> headerMap = new HashMap<>();
                for (int i = 0; i < header.length; i++) {
                    headerMap.put(header[i].trim(), i);
                }

                String[] line;
                List<TrainSchedule> schedulesToSave = new ArrayList<>(); // 모든 스케줄을 저장할 리스트
                while ((line = reader.readNext()) != null) {
                    String trainNumber = getCsvValue(line, headerMap, "열차번호");
                    String trainName = getCsvValue(line, headerMap, "편성");
                    String operatingDays = getCsvValue(line, headerMap, "운행요일");

                    // 각 역의 시간 정보 파싱
                    Map<String, LocalTime> stationTimes = new HashMap<>();
                    for (String station : stationOrder) {
                        Integer index = headerMap.get(station);
                        if (index != null && index < line.length) {
                            String timeStr = line[index].trim();
                            if (!timeStr.isEmpty()) {
                                try {
                                    stationTimes.put(station, LocalTime.parse(timeStr, TIME_FORMATTER));
                                } catch (Exception e) {
                                    // 시간 파싱 오류 무시 (예: "" 빈 값)
                                }
                            }
                        }
                    }

                    if (trainNumber.isEmpty() || trainName.isEmpty() || operatingDays.isEmpty()) {
                        System.err.println("Skipping malformed train data in " + filename + ": " + Arrays.toString(line));
                        continue;
                    }

                    // 가능한 모든 출발-도착 조합 생성 및 저장
                    for (int i = 0; i < stationOrder.size(); i++) {
                        String departureStation = stationOrder.get(i);
                        LocalTime depTime = stationTimes.get(departureStation);
                        if (depTime == null) continue; // 출발 시간이 없는 역은 건너뜀

                        for (int j = i + 1; j < stationOrder.size(); j++) { // 출발역 이후의 모든 역을 도착역으로
                            String arrivalStation = stationOrder.get(j);
                            LocalTime arrTime = stationTimes.get(arrivalStation);
                            if (arrTime == null) continue; // 도착 시간이 없는 역은 건너뜀

                            // 임시 날짜 설정 (예: 2025년 10월 15일)
                            LocalDate baseDate = LocalDate.now();

                            LocalDateTime departureDateTime = LocalDateTime.of(baseDate, depTime);
                            LocalDateTime arrivalDateTime = LocalDateTime.of(baseDate, arrTime);

                            // 자정(00:xx)을 넘어가는 시간 처리 (예: 23:50 출발 -> 00:30 도착)
                            if (arrivalDateTime.isBefore(departureDateTime)) {
                                arrivalDateTime = arrivalDateTime.plusDays(1);
                            }

                            schedulesToSave.add(TrainSchedule.builder()
                                    .trainNumber(trainNumber)
                                    .trainName(trainName)
                                    .departureStation(departureStation)
                                    .arrivalStation(arrivalStation)
                                    .departureTime(departureDateTime)
                                    .arrivalTime(arrivalDateTime)
                                    .operatingDays(operatingDays)
                                    .price(30000) // 임시 가격 설정 (실제 로직 필요)
                                    .build());
                        }
                    }
                }

                // 모든 스케줄을 한 번에 저장
                if (!schedulesToSave.isEmpty()) {
                    trainScheduleRepository.saveAll(schedulesToSave);
                }
            }
        } catch (IOException | CsvValidationException e) {
            System.err.println("Failed to load train data from " + filename + ": " + e.getMessage());
            e.printStackTrace();
        }
    }

    private String getCsvValue(String[] line, Map<String, Integer> headerMap, String headerName) {
        Integer index = headerMap.get(headerName);
        if (index == null) {
            throw new IllegalArgumentException("CSV header '" + headerName + "' not found.");
        }
        if (index >= line.length) {
            // 해당 인덱스에 데이터가 없는 경우 (예: 마지막 컬럼)
            return "";
        }
        return line[index].trim();
    }
}
