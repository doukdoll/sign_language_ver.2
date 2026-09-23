package com.capstone.service;

import com.capstone.entity.TrainSchedule;
import com.capstone.repository.TrainScheduleRepository;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class KorailServiceTest {
    @Test void searchReturnsTheStoredFareUsedByBooking() {
        var repository = mock(TrainScheduleRepository.class);
        LocalDateTime from = LocalDateTime.of(2026, 9, 22, 9, 0);
        TrainSchedule schedule = TrainSchedule.builder().trainNumber("101").trainName("KTX")
                .departureStation("서울").arrivalStation("대전")
                .departureTime(from.plusHours(1)).arrivalTime(from.plusHours(2)).price(32000).build();
        when(repository.findByDepartureStationAndArrivalStationAndDepartureTimeGreaterThanEqualAndDepartureTimeLessThanOrderByDepartureTimeAsc(
                "서울", "대전", from, from.toLocalDate().plusDays(1).atStartOfDay()))
                .thenReturn(List.of(schedule));

        var results = new KorailService(repository).findSchedules("서울", "대전", from, null);

        assertEquals(1, results.size());
        assertEquals(32000, results.get(0).getPrice());
        assertEquals(60, results.get(0).getDuration());
    }
}
