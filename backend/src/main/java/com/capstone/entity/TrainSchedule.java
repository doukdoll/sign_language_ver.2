package com.capstone.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "train_schedule")
public class TrainSchedule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String trainNumber; // 열차번호

    @Column(nullable = false)
    private String trainName; // 편성 (KTX, KTX-산천 등)

    @Column(nullable = false)
    private String departureStation; // 출발역

    @Column(nullable = false)
    private String arrivalStation; // 도착역

    @Column(nullable = false)
    private LocalDateTime departureTime; // 출발 시간 (날짜 + 시간)

    @Column(nullable = false)
    private LocalDateTime arrivalTime; // 도착 시간 (날짜 + 시간)

    @Column(nullable = false)
    private String operatingDays; // 운행 요일 (매일, 월, 금토일 등)

    @Column(nullable = false)
    private Integer price; // 가격
    // private String seatType;
    // private Integer availableSeats;
}
