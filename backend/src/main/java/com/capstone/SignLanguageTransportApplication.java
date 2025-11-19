package com.capstone;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

@SpringBootApplication
public class SignLanguageTransportApplication {

    public static void main(String[] args) {
        SpringApplication.run(SignLanguageTransportApplication.class, args);
    }

    // RestTemplate을 Spring 컨테이너에 빈으로 등록하는 메서드
    @Bean
    public RestTemplate restTemplate() {
        // 이제 이 객체는 다른 모든 컴포넌트(Service, Controller 등)에서 주입받아 사용 가능합니다.
        return new RestTemplate();
    }
}

