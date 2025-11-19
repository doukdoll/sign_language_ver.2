package com.capstone.controller;

import com.capstone.dto.BookingRequestDto;
import com.capstone.dto.TicketDto;
import com.capstone.service.BookingService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/booking")
public class BookingController {

    private final BookingService bookingService;

    public BookingController(BookingService bookingService) {
        this.bookingService = bookingService;
    }

    @PostMapping("/train")
    public ResponseEntity<TicketDto> bookTrain(@Valid @RequestBody BookingRequestDto request) {
        TicketDto ticket = bookingService.createBookingAndTicket(request);
        return new ResponseEntity<>(ticket, HttpStatus.CREATED);
    }
}

