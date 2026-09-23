package com.capstone.controller;

import com.capstone.config.GlobalExceptionHandler;
import com.capstone.repository.BookingRepository;
import com.capstone.repository.TrainScheduleRepository;
import com.capstone.service.BookingService;
import com.capstone.service.KorailService;
import com.capstone.util.QrGenerator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class ApiValidationTest {
    private final BookingRepository bookings = mock(BookingRepository.class);
    private final TrainScheduleRepository schedules = mock(TrainScheduleRepository.class);
    private final KorailService korail = mock(KorailService.class);
    private MockMvc mvc;

    private static final String REQUEST = """
            {"trainNumber":"101","departureStation":"서울","arrivalStation":"부산",
             "departureTime":"2026-09-22T10:00:00","arrivalTime":"2026-09-22T11:00:00",
             "passengers":2,"seatType":"STANDARD","paymentMethod":"card","tripType":"one_way"}
            """;

    @BeforeEach void setup() {
        mvc = MockMvcBuilders.standaloneSetup(
                new BookingController(new BookingService(bookings, schedules, new QrGenerator())),
                new TrainController(korail))
                .setControllerAdvice(new GlobalExceptionHandler()).build();
    }

    @Test void unmatchedJourneyReturnsBadRequestWithoutSaving() throws Exception {
        mvc.perform(post("/booking/train").contentType(MediaType.APPLICATION_JSON).content(REQUEST))
                .andExpect(status().isBadRequest()).andExpect(content().string("Invalid train schedule"));
        verifyNoInteractions(bookings);
    }

    @Test void missingTripTypeIsRejectedBeforeAccessingDatabase() throws Exception {
        mvc.perform(post("/booking/train").contentType(MediaType.APPLICATION_JSON)
                        .content(REQUEST.replace(",\"tripType\":\"one_way\"", "")))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.tripType").value("Trip type is required"));
        verifyNoInteractions(bookings, schedules);
    }

    @Test void invalidPassengerCountIsStillRejected() throws Exception {
        mvc.perform(post("/booking/train").contentType(MediaType.APPLICATION_JSON)
                        .content(REQUEST.replace("\"passengers\":2", "\"passengers\":0")))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.passengers").exists());
        verifyNoInteractions(bookings, schedules);
    }

    @Test void malformedJsonReturnsBadRequest() throws Exception {
        mvc.perform(post("/booking/train").contentType(MediaType.APPLICATION_JSON).content("{invalid"))
                .andExpect(status().isBadRequest()).andExpect(content().string("Invalid request"));
        verifyNoInteractions(bookings, schedules);
    }

    @Test void malformedSearchDateReturnsBadRequest() throws Exception {
        mvc.perform(get("/train/search").param("departureFrom", "not-a-date"))
                .andExpect(status().isBadRequest()).andExpect(content().string("Invalid request"));
        verifyNoInteractions(korail);
    }

    @Test void unexpectedFailuresDoNotExposeInternalMessages() throws Exception {
        when(korail.findSchedules(isNull(), isNull(), isNull(), isNull()))
                .thenThrow(new IllegalStateException("private database connection details"));
        mvc.perform(get("/train/search"))
                .andExpect(status().isInternalServerError())
                .andExpect(content().string("An unexpected error occurred"));
    }
}
