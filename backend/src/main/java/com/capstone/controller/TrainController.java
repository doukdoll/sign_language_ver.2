package com.capstone.controller;

import com.capstone.dto.TrainInfoDto;
import com.capstone.service.KorailService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

@RestController
@RequestMapping("/train")
public class TrainController {
    private final KorailService korailService;

    public TrainController(KorailService korailService) {
        this.korailService = korailService;
    }

    @GetMapping("/search")
    public List<TrainInfoDto> search(
            @RequestParam(name = "departure", required = false) String departure,
            @RequestParam(name = "destination", required = false) String destination,
            @RequestParam(name = "departureFrom", required = false) String departureFrom,
            @RequestParam(name = "departureTo", required = false) String departureTo
    ) {
        LocalDateTime from = parseDateTime(departureFrom);
        LocalDateTime to = parseDateTime(departureTo);
        return korailService.findSchedules(departure, destination, from, to);
    }

    private LocalDateTime parseDateTime(String text) {
        if (text == null || text.isBlank()) return null;
        // ISO-8601 (예: 2025-10-14T09:00) 또는 yyyy-MM-dd HH:mm 둘 다 지원
        try {
            return LocalDateTime.parse(text);
        } catch (DateTimeParseException ignored) {}
        try {
            return LocalDateTime.parse(text, DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"));
        } catch (DateTimeParseException ignored) {}
        return null;
    }
}

