package com.capstone.dto;

import org.springframework.web.socket.WebSocketSession;

public class CityRecognitionResponseDto {
    private String sessionId;
    private String departureCity;
    private String arrivalCity;


    public String getSessionId() {return this.sessionId;}

    public void setSessionId(String sessionId) {this.sessionId = sessionId;}

    public String getDepartureCity() {
        return departureCity;
    }

    public void setDepartureCity(String departureCity) {
        this.departureCity = departureCity;
    }

    public String getArrivalCity() {
        return arrivalCity;
    }

    public void setArrivalCity(String arrivalCity) {
        this.arrivalCity = arrivalCity;
    }
}


