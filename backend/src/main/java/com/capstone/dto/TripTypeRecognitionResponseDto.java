package com.capstone.dto;

public class TripTypeRecognitionResponseDto {
    private String recognizedTripType; // 예: "편도", "왕복"

    public String getRecognizedTripType() {
        return recognizedTripType;
    }

    public void setRecognizedTripType(String recognizedTripType) {
        this.recognizedTripType = recognizedTripType;
    }
}


