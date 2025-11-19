package com.capstone.dto;

public class SeatClassRecognitionResponseDto {
    private String recognizedSeatClass; // 예: "일반실", "특실"

    public String getRecognizedSeatClass() {
        return recognizedSeatClass;
    }

    public void setRecognizedSeatClass(String recognizedSeatClass) {
        this.recognizedSeatClass = recognizedSeatClass;
    }
}


