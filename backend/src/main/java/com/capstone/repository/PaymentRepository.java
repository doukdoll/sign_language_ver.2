package com.capstone.repository;

import com.capstone.entity.Payment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PaymentRepository extends JpaRepository<Payment, Long> {
    
    Optional<Payment> findByPaymentId(String paymentId);
    
    List<Payment> findByBookingId(Long bookingId);
    
    List<Payment> findByStatus(String status);
    
    @Query("SELECT p FROM Payment p WHERE p.bookingId = :bookingId AND p.status = 'completed'")
    Optional<Payment> findCompletedPaymentByBookingId(@Param("bookingId") Long bookingId);
}

