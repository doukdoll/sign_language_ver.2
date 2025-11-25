package com.capstone.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TicketDto {
    private String bookingId;
    private String trainNumber;
    private String trainName;
    private String departureStation;
    private String arrivalStation;
    private LocalDateTime departureTime;
    private LocalDateTime arrivalTime;
    private String seatNumber; // 예: "15호차 23A석"
    private Integer ticketPrice;
    private String qrCodeData; // QR 코드 생성에 사용될 데이터
}
