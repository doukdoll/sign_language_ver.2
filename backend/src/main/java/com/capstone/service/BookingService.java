package com.capstone.service;

import com.capstone.dto.BookingRequestDto;
import com.capstone.dto.TicketDto;
import com.capstone.entity.Booking;
import com.capstone.entity.TrainSchedule;
import com.capstone.repository.BookingRepository;
import com.capstone.repository.TrainScheduleRepository;
import com.capstone.util.QrGenerator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class BookingService {

    private final BookingRepository bookingRepository;
    private final TrainScheduleRepository trainScheduleRepository;
    private final QrGenerator qrGenerator;

    public BookingService(
            BookingRepository bookingRepository,
            TrainScheduleRepository trainScheduleRepository,
            QrGenerator qrGenerator) {
        this.bookingRepository = bookingRepository;
        this.trainScheduleRepository = trainScheduleRepository;
        this.qrGenerator = qrGenerator;
    }

    @Transactional
    public TicketDto createBookingAndTicket(BookingRequestDto request) {
        // Match the complete requested journey before creating a demo ticket.
        TrainSchedule trainSchedule = trainScheduleRepository
                .findByTrainNumberAndDepartureStationAndArrivalStationAndDepartureTimeAndArrivalTime(
                        request.getTrainNumber(), request.getDepartureStation(), request.getArrivalStation(),
                        request.getDepartureTime(), request.getArrivalTime())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid train schedule"));

        // 2. 좌석 할당 (현재는 더미, 실제로는 복잡한 좌석 관리 로직 필요)
        String seatNumber = "12호차 34A석"; // 더미 좌석 번호

        // 3. QR 코드 데이터 생성
        String bookingId = UUID.randomUUID().toString();
        String qrCodeData = qrGenerator.generateQrCodeData(bookingId, trainSchedule.getTrainNumber());

        // 4. Booking 엔티티 생성 및 저장
        Booking booking = Booking.builder()
                .bookingId(bookingId)
                .trainNumber(trainSchedule.getTrainNumber())
                .departureStation(trainSchedule.getDepartureStation())
                .arrivalStation(trainSchedule.getArrivalStation())
                .departureTime(trainSchedule.getDepartureTime())
                .arrivalTime(trainSchedule.getArrivalTime())
                .passengers(request.getPassengers())
                .seatType(request.getSeatType())
                .seatNumber(seatNumber)
                .paymentMethod(request.getPaymentMethod())
                .ticketPrice(trainSchedule.getPrice() * request.getPassengers()) // 열차 스케줄 가격 사용
                .qrCodeData(qrCodeData)
                .bookingTime(LocalDateTime.now())
                .status("CONFIRMED") // 예약 상태를 "CONFIRMED"로 설정
                .tripType(request.getTripType()) // tripType 필드 추가
                .build();
        bookingRepository.save(booking);

        // 5. TicketDto 생성 및 반환
        return TicketDto.builder()
                .bookingId(booking.getBookingId())
                .trainNumber(booking.getTrainNumber())
                .trainName(trainSchedule.getTrainName()) // TrainSchedule에서 열차 이름 가져오기
                .departureStation(booking.getDepartureStation())
                .arrivalStation(booking.getArrivalStation())
                .departureTime(booking.getDepartureTime())
                .arrivalTime(booking.getArrivalTime())
                .seatNumber(booking.getSeatNumber())
                .ticketPrice(booking.getTicketPrice())
                .qrCodeData(booking.getQrCodeData())
                .build();
    }
}

