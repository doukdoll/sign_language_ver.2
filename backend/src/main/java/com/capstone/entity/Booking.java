package com.capstone.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Entity
@Table(name = "bookings")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Booking {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(nullable = false, unique = true)
    private String bookingId; // 예매 ID (UUID)
    
    @Column(nullable = false)
    private String trainNumber;
    
    @Column(nullable = false)
    private String departureStation;
    
    @Column(nullable = false)
    private String arrivalStation;
    
    @Column(nullable = false)
    private LocalDateTime departureTime;
    
    @Column(nullable = false)
    private LocalDateTime arrivalTime;
    
    @Column(nullable = false)
    private Integer passengers;
    
    @Column(nullable = false)
    private String seatType;
    
    @Column(nullable = false)
    private String seatNumber; // 할당된 좌석 번호 (예: "12호차 34A석")

    @Column(nullable = false)
    private Integer ticketPrice; // 티켓 총 가격
    
    @Column(nullable = false)
    private String paymentMethod;
    
    @Column(nullable = false)
    private String qrCodeData; // QR 코드에 인코딩될 데이터
    
    @Column(nullable = false)
    private String status; // "pending", "confirmed", "cancelled"
    
    @Column(nullable = false)
    private String tripType;
    
    @Column(nullable = false)
    private LocalDateTime bookingTime; // 예매 시간 (BookingService에서 추가됨)
    
    @Column(nullable = false)
    private LocalDateTime createdAt;
    
    @Column
    private LocalDateTime updatedAt;
    
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }
    
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}

