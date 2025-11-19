package com.capstone.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SlotDataDto {
    
    @JsonProperty("destination")
    private String destination;
    
    @JsonProperty("departure_time")
    private String departureTime;
    
    @JsonProperty("arrival_time")
    private String arrivalTime;
    
    @JsonProperty("date")
    private String date;
    
    @JsonProperty("passengers")
    private Integer passengers;
    
    @JsonProperty("seat_type")
    private String seatType;
    
    @JsonProperty("trip_type")
    private String tripType; // "one_way" or "round_trip"
    
    @JsonProperty("payment_method")
    private String paymentMethod;
    
    @JsonProperty("confidence")
    private Double confidence;
}

