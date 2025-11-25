package com.capstone.repository;

import com.capstone.entity.Booking;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface BookingRepository extends JpaRepository<Booking, Long> {
    
    Optional<Booking> findByBookingId(String bookingId);
    
    List<Booking> findByStatus(String status);
    
    @Query("SELECT b FROM Booking b WHERE b.departureStation = :station AND b.departureTime >= :startTime AND b.departureTime <= :endTime")
    List<Booking> findBookingsByStationAndTimeRange(
        @Param("station") String station,
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime
    );
    
    @Query("SELECT COUNT(b) FROM Booking b WHERE b.trainNumber = :trainNumber AND b.departureTime = :departureTime")
    Long countBookingsByTrainAndTime(@Param("trainNumber") String trainNumber, @Param("departureTime") LocalDateTime departureTime);
}

