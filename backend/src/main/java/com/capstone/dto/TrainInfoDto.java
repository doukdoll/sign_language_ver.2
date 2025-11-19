package com.capstone.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TrainInfoDto {
    
    private String trainNumber;
    private String trainName;
    private String departureStation;
    private String arrivalStation;
    private LocalDateTime departureTime;
    private LocalDateTime arrivalTime;
    private Integer duration; // minutes
    private String seatType;
    private Integer availableSeats;
    private Integer price;
    private String status; // "available", "sold_out", "delayed"
    private List<String> stops;
}

