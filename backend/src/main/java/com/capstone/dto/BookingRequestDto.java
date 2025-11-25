package com.capstone.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class BookingRequestDto {
    
    @NotBlank(message = "Train number is required")
    private String trainNumber;
    
    @NotBlank(message = "Departure station is required")
    private String departureStation;
    
    @NotBlank(message = "Arrival station is required")
    private String arrivalStation;

    @NotNull(message = "Departure time is required")
    private LocalDateTime departureTime;

    @NotNull(message = "Arrival time is required")
    private LocalDateTime arrivalTime;

    @NotNull(message = "Passengers count is required")
    @Min(value = 1, message = "At least 1 passenger required")
    @Max(value = 9, message = "Maximum 9 passengers allowed")
    private Integer passengers;
    
    @NotBlank(message = "Seat type is required")
    private String seatType;
    
    @NotBlank(message = "Payment method is required")
    private String paymentMethod;
    
    private String tripType; // "one_way" or "round_trip"
}

