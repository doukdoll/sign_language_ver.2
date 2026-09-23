package com.capstone.repository;

import com.capstone.SignLanguageTransportApplication;
import com.capstone.entity.TrainSchedule;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.ContextConfiguration;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

@DataJpaTest
@ActiveProfiles("test")
@ContextConfiguration(classes = SignLanguageTransportApplication.class)
class TrainScheduleRepositoryTest {
    @Autowired private TrainScheduleRepository repository;

    @Test void bookingLookupRequiresBothStationsAndBothTimes() {
        LocalDateTime departure = LocalDateTime.of(2026, 9, 22, 10, 0);
        LocalDateTime arrival = departure.plusHours(1);
        repository.saveAndFlush(TrainSchedule.builder().trainNumber("101").trainName("KTX")
                .departureStation("서울").arrivalStation("대전")
                .departureTime(departure).arrivalTime(arrival).operatingDays("매일").price(32000).build());

        assertTrue(repository.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "대전", departure, arrival).isPresent());
        assertTrue(repository.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "광명", "대전", departure, arrival).isEmpty());
        assertTrue(repository.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "부산", departure, arrival).isEmpty());
        assertTrue(repository.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "대전", departure.plusMinutes(1), arrival).isEmpty());
        assertTrue(repository.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "대전", departure, arrival.plusMinutes(1)).isEmpty());
    }
}
