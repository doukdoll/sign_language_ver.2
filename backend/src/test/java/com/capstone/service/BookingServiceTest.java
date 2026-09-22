package com.capstone.service;

import com.capstone.dto.BookingRequestDto;
import com.capstone.entity.Booking;
import com.capstone.entity.TrainSchedule;
import com.capstone.repository.BookingRepository;
import com.capstone.repository.TrainScheduleRepository;
import com.capstone.util.QrGenerator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class BookingServiceTest {
    private final BookingRepository bookings = mock(BookingRepository.class);
    private final TrainScheduleRepository schedules = mock(TrainScheduleRepository.class);
    private final BookingService service = new BookingService(bookings, schedules, new QrGenerator());
    private BookingRequestDto request;

    @BeforeEach void setup() {
        request = new BookingRequestDto("101", "서울", "대전",
                LocalDateTime.of(2026, 9, 22, 10, 0), LocalDateTime.of(2026, 9, 22, 11, 0),
                2, "STANDARD", "card", "one_way");
    }

    @Test void booksTheMatchedJourneyUsingItsStoredFare() {
        TrainSchedule schedule = TrainSchedule.builder().trainNumber("101").trainName("KTX")
                .departureStation("서울").arrivalStation("대전")
                .departureTime(request.getDepartureTime()).arrivalTime(request.getArrivalTime())
                .price(32000).build();
        when(schedules.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "대전", request.getDepartureTime(), request.getArrivalTime()))
                .thenReturn(Optional.of(schedule));

        var ticket = service.createBookingAndTicket(request);

        var saved = ArgumentCaptor.forClass(Booking.class);
        verify(bookings).save(saved.capture());
        assertEquals(64000, ticket.getTicketPrice());
        assertEquals("서울", ticket.getDepartureStation());
        assertEquals("대전", ticket.getArrivalStation());
        assertEquals(request.getDepartureTime(), ticket.getDepartureTime());
        assertEquals("KTX", ticket.getTrainName());
        assertEquals("one_way", saved.getValue().getTripType());
        assertEquals(ticket.getBookingId(), saved.getValue().getBookingId());
    }

    @Test void rejectsUnmatchedJourneyWithoutCreatingABooking() {
        request.setArrivalStation("부산");
        when(schedules.findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                "101", "서울", "부산", request.getDepartureTime(), request.getArrivalTime()))
                .thenReturn(Optional.empty());

        var error = assertThrows(ResponseStatusException.class, () -> service.createBookingAndTicket(request));

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verifyNoInteractions(bookings);
    }
}
