package com.capstone.service;

import com.capstone.dto.TrainInfoDto;
import com.capstone.repository.TrainScheduleRepository;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;
import com.capstone.entity.TrainSchedule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class KorailService {

    private static final Logger logger = LoggerFactory.getLogger(KorailService.class);

    private final TrainScheduleRepository trainScheduleRepository;

    public KorailService(TrainScheduleRepository trainScheduleRepository) {
        this.trainScheduleRepository = trainScheduleRepository;
    }

    public List<TrainInfoDto> findSchedules(
            String departure,
            String destination,
            LocalDateTime departureFrom,
            LocalDateTime departureTo
    ) {
        // departureFrom이 null일 경우 현재 시간으로 기본 설정
        final LocalDateTime effectiveDepartureFrom = (departureFrom == null) ? LocalDateTime.now() : departureFrom;
        logger.debug("Effective Departure From: {}", effectiveDepartureFrom);

        logger.debug("Departure: {}, Destination: {}, Effective Departure From: {}", departure, destination, effectiveDepartureFrom);

        List<TrainSchedule> filteredSchedules = new ArrayList<>();

        if (departure != null && !departure.isBlank() && destination != null && !destination.isBlank()) {
            filteredSchedules = trainScheduleRepository.findByDepartureStationAndArrivalStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
                    departure.trim(), destination.trim(), effectiveDepartureFrom
            );
            logger.debug("Filtered schedules (dep+arr): {}", filteredSchedules.size()); // 디버깅 로그
        } else if (departure != null && !departure.isBlank()) {
            // 출발지만 있을 경우, 해당 출발지의 모든 도착지에 대한 시간표를 필터링
            filteredSchedules = trainScheduleRepository.findByDepartureStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
                    departure.trim(), effectiveDepartureFrom
            );
            logger.debug("Filtered schedules (dep only): {}", filteredSchedules.size()); // 디버깅 로그
        } else if (destination != null && !destination.isBlank()) {
            // 목적지만 있을 경우, 해당 목적지의 모든 출발지에 대한 시간표를 필터링
            filteredSchedules = trainScheduleRepository.findByArrivalStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
                    destination.trim(), effectiveDepartureFrom
            );
            logger.debug("Filtered schedules (arr only): {}", filteredSchedules.size()); // 디버깅 로그
        } else {
            // 출발지/목적지 모두 없을 경우
            filteredSchedules = trainScheduleRepository.findByDepartureTimeAfterOrderByDepartureTimeAsc(effectiveDepartureFrom);
            logger.debug("Filtered schedules (none): {}", filteredSchedules.size()); // 디버깅 로그
        }

        // departureTo 필터링 추가
        if (departureTo != null) {
            int initialSize = filteredSchedules.size();
            filteredSchedules = filteredSchedules.stream()
                    .filter(s -> !s.getDepartureTime().isAfter(departureTo))
                    .collect(Collectors.toList());
            logger.debug("Filtered by departureTo (from {} to {}): {}", initialSize, filteredSchedules.size(), departureTo); // 디버깅 로그
        }

        logger.debug("Final filtered schedules count: {}", filteredSchedules.size()); // 최종 디버깅 로그

        return filteredSchedules.stream()
                .map(schedule -> TrainInfoDto.builder()
                        .trainNumber(schedule.getTrainNumber())
                        .trainName(schedule.getTrainName())
                        .departureStation(schedule.getDepartureStation())
                        .arrivalStation(schedule.getArrivalStation())
                        .departureTime(schedule.getDepartureTime())
                        .arrivalTime(schedule.getArrivalTime())
                        .duration((int) java.time.Duration.between(schedule.getDepartureTime(), schedule.getArrivalTime()).toMinutes())
                        .seatType("STANDARD") // CSV에 없으므로 임시로 설정
                        .availableSeats(50) // CSV에 없으므로 임시로 설정
                        .price(50000) // CSV에 없으므로 임시로 설정
                        .status("available") // CSV에 없으므로 임시로 설정
                        .build())
                .sorted(Comparator.comparing(TrainInfoDto::getDepartureTime))
                .limit(5) // 최대 5개의 결과만 반환
                .collect(Collectors.toList());
    }
}

