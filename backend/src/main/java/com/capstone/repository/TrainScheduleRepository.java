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
    List<TrainSchedule> findByDepartureStationAndArrivalStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
            String departureStation,
            String arrivalStation,
            LocalDateTime departureTime
    );

    // 출발역, 도착역 기준으로 출발 시간 이후 정렬된 열차 시간표 조회 (departureTime이 null일 경우 전체 조회)
    List<TrainSchedule> findByDepartureStationAndArrivalStationOrderByDepartureTimeAsc(
            String departureStation,
            String arrivalStation
    );

    // 모든 열차 시간표를 출발 시간 이후 정렬하여 조회
    List<TrainSchedule> findByDepartureTimeAfterOrderByDepartureTimeAsc(LocalDateTime departureTime);

    // 모든 열차 시간표를 출발 시간 기준 정렬하여 조회
    List<TrainSchedule> findAllByOrderByDepartureTimeAsc();

    // 출발역과 출발 시간 이후 기준으로 정렬된 열차 시간표 조회
    List<TrainSchedule> findByDepartureStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
            String departureStation,
            LocalDateTime departureTime
    );

    // 도착역과 출발 시간 이후 기준으로 정렬된 열차 시간표 조회
    List<TrainSchedule> findByArrivalStationAndDepartureTimeAfterOrderByDepartureTimeAsc(
            String arrivalStation,
            LocalDateTime departureTime
    );

    // 열차 번호, 출발 시간, 도착 시간을 기준으로 열차 시간표 조회
    Optional<TrainSchedule> findByTrainNumberAndDepartureTimeAndArrivalTime(
            String trainNumber,
            LocalDateTime departureTime,
            LocalDateTime arrivalTime
    );
}
