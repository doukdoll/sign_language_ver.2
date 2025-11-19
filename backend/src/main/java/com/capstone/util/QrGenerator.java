package com.capstone.util;

import org.springframework.stereotype.Component;

@Component
public class QrGenerator {

    public String generateQrCodeData(String bookingId, String trainNumber) {
        // 실제 QR 코드 생성 로직은 여기에서 구현됩니다.
        // 여기서는 예시로 bookingId와 trainNumber를 조합한 문자열을 반환합니다.
        return "BookingID: " + bookingId + ", TrainNumber: " + trainNumber;
    }
}

