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
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.TextStyle;
import java.util.*;

@Profile("!test") // 테스트 환경에서는 실행되지 않도록 설정
@Component
public class TrainDataLoader {

    private final TrainScheduleRepository trainScheduleRepository;

    // CSV 파일에 있는 역 이름을 순서대로 매핑
    private static final List<String> STATIONS_DOWN = Arrays.asList(
        "행신", "서울", "영등포", "수원", "광명", "천안아산", "오송", "대전",
        "김천구미", "서대구", "동대구", "경주", "울산", "경산", "밀양", "물금", "구포", "부산"
    );
    private static final List<String> STATIONS_UP = Arrays.asList(
            "부산", "구포", "물금", "밀양", "경산", "울산", "경주", "동대구",
            "서대구", "김천구미", "대전", "오송", "천안아산", "광명", "수원", "영등포", "서울", "행신"
    );

    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("H:mm");
    // [추가됨] 로그 출력용 날짜 포맷터 선언 (이 부분이 없어서 오류가 났었습니다)
    private static final DateTimeFormatter LOG_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    public TrainDataLoader(TrainScheduleRepository trainScheduleRepository) {
        this.trainScheduleRepository = trainScheduleRepository;
    }

    @PostConstruct
    public void loadTrainData() {
        if (trainScheduleRepository.count() == 0) { // 데이터가 비어있을 때만 로드
            System.out.println("Loading train schedule data...");
            loadCsvData("gyeongbu_hahaeng.csv", STATIONS_DOWN);
            loadCsvData("gyeongbu_sanghaeng.csv", STATIONS_UP);
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

                    LocalDate startDate = LocalDate.now();                       // 시작일: 오늘
                    LocalDate endDate = startDate.plusMonths(1);     // 종료일: 한 달 뒤

                    // 가능한 모든 출발-도착 조합 생성 및 저장
                    for (int i = 0; i < stationOrder.size(); i++) {
                        String departureStation = stationOrder.get(i);
                        LocalTime depTime = stationTimes.get(departureStation);
                        if (depTime == null) continue; // 출발 시간이 없는 역은 건너뜀

                        for (int j = i + 1; j < stationOrder.size(); j++) { // 출발역 이후의 모든 역을 도착역으로
                            String arrivalStation = stationOrder.get(j);
                            LocalTime arrTime = stationTimes.get(arrivalStation);
                            if (arrTime == null) continue; // 도착 시간이 없는 역은 건너뜀


                            // ** 날짜 루프 시작 **
                            // startDate부터 endDate까지 하루씩 증가
                            for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {

                                // 1. 해당 날짜(요일)에 열차가 운행하는지 체크
                                if (!isRunningOnDate(operatingDays, date)) {
                                    continue; // 운행하지 않는 날이면 스킵
                                }

                                LocalDateTime departureDateTime = LocalDateTime.of(date, depTime);
                                LocalDateTime arrivalDateTime = LocalDateTime.of(date, arrTime);

                                // 2. 자정 넘김 처리 (도착 시간이 출발 시간보다 빠르면 다음날 도착으로 간주)
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
                                        .price(30000)
                                        .build());
                            }
                            // ** 날짜 루프 끝 **
                        }
                    }
                }

                // 모든 스케줄을 한 번에 저장
                if (!schedulesToSave.isEmpty()) {
                    trainScheduleRepository.saveAll(schedulesToSave);
                    // [추가된 코드 시작] ----------------------------------------------------------------
                    // 저장된 데이터의 상위 5개를 미리보기(head) 형태로 출력합니다.
                    System.out.println("===============================================================");
                    System.out.println("[Data Load Preview] 파일명: " + filename);
                    System.out.println(String.format("%-10s | %-6s | %-6s -> %-6s | %-16s -> %-16s",
                            "열차번호", "종류", "출발", "도착", "출발시간", "도착시간"));
                    System.out.println("---------------------------------------------------------------");

                    // 최대 5개까지만 출력 (head 기능 구현)
                    int limit = Math.min(schedulesToSave.size(), 5);
                    for (int i = 0; i < limit; i++) {
                        TrainSchedule s = schedulesToSave.get(i);
                        System.out.println(String.format("%-10s | %-6s | %-6s -> %-6s | %-16s -> %-16s",
                                s.getTrainNumber(),
                                s.getTrainName(),
                                s.getDepartureStation(),
                                s.getArrivalStation(),
                                s.getDepartureTime().format(LOG_TIME_FORMATTER),
                                s.getArrivalTime().format(LOG_TIME_FORMATTER)
                        ));
                    }

                    if (schedulesToSave.size() > 5) {
                        System.out.println("... 외 " + (schedulesToSave.size() - 5) + "건 생략됨");
                    }
                    System.out.println("[Total Count] 총 " + schedulesToSave.size() + "건 저장 완료");
                    System.out.println("===============================================================");
                    // [추가된 코드 끝] ------------------------------------------------------------------
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

    // [추가] 요일 체크 헬퍼 메서드
    // "매일", "월화수", "토일" 등의 문자열과 현재 날짜의 요일을 비교
    private boolean isRunningOnDate(String operatingDays, LocalDate date) {
        if (operatingDays.equals("매일")) {
            return true;
        }

        // 현재 날짜의 요일을 한국어 1글자로 변환 (예: MONDAY -> "월")
        String dayOfWeekArg = date.getDayOfWeek().getDisplayName(TextStyle.NARROW, Locale.KOREAN);

        // CSV의 운행요일 문자열에 해당 요일이 포함되어 있는지 확인
        // 예: operatingDays가 "월수금"이고 오늘이 "수"요일이면 true
        return operatingDays.contains(dayOfWeekArg);
    }
}
