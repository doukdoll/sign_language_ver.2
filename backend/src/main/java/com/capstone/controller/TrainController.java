package com.capstone.controller;

import com.capstone.dto.TrainInfoDto;
import com.capstone.service.KorailService;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import java.time.LocalDateTime;

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

            @RequestParam(name = "departureFrom", required = false)
            @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm") LocalDateTime departureFrom,

            @RequestParam(name = "departureTo", required = false)
            @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm") LocalDateTime departureTo
    ) {
        return korailService.findSchedules(departure, destination, departureFrom, departureTo);
    }
}

