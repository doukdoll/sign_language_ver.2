package com.capstone.repository;

import com.capstone.entity.TrainSchedule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface TrainScheduleRepository extends JpaRepository<TrainSchedule, Long> {
    // 출발역, 도착역, 출발 시간 이후 기준으로 정렬된 열차 시간표 조회
    List<TrainSchedule> findByDepartureStationAndArrivalStationAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            String departureStation,
            String arrivalStation,
            LocalDateTime departureTime,
            LocalDateTime nextDayMidnight
    );

    // 출발역, 도착역 기준으로 출발 시간 이후 정렬된 열차 시간표 조회 (departureTime이 null일 경우 전체 조회)
    List<TrainSchedule> findByDepartureStationAndArrivalStationAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            String departureStation,
            String arrivalStation,
            LocalDateTime nextDayMidnight
    );

    // 모든 열차 시간표를 출발 시간 이후 정렬하여 조회
    List<TrainSchedule> findByDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(LocalDateTime departureTime, LocalDateTime nextDayMidnight);

    // 모든 열차 시간표를 출발 시간 기준 정렬하여 조회
    List<TrainSchedule> findAllByOrderByDepartureTimeAsc();

    // 출발역과 출발 시간 이후 기준으로 정렬된 열차 시간표 조회
    List<TrainSchedule> findByDepartureStationAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            String departureStation,
            LocalDateTime departureTime,
            LocalDateTime nextDayMidnight
    );

    // 도착역과 출발 시간 이후 기준으로 정렬된 열차 시간표 조회
    List<TrainSchedule> findByArrivalStationAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            String arrivalStation,
            LocalDateTime departureTime,
            LocalDateTime nextDayMidnight
    );

    // 열차 번호, 출발 시간, 도착 시간을 기준으로 열차 시간표 조회
    Optional<TrainSchedule> findByTrainNumberAndDepartureTimeAndArrivalTime(
            String trainNumber,
            LocalDateTime departureTime,
            LocalDateTime arrivalTime
    );

    // 출발역, 도착역 리스트, 출발 시간 이후 기준으로 정렬된 열차 시간표 조회 (대구용)
    List<TrainSchedule> findByDepartureStationAndArrivalStationInAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            String departureStation,
            List<String> arrivalStations,
            LocalDateTime departureTime,
            LocalDateTime nextDayMidnight
    );

    // 출발역 리스트, 도착역, 출발 시간 이후 기준으로 정렬된 열차 시간표 조회 (대구용)
    List<TrainSchedule> findByDepartureStationInAndArrivalStationAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
            List<String> departureStation,
            String arrivalStations,
            LocalDateTime departureTime,
            LocalDateTime nextDayMidnight
    );
}
