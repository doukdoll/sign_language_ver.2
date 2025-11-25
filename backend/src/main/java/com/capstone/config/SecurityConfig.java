package com.capstone.config; // 패키지명은 본인 프로젝트 구조에 맞게 유지하세요.

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityCustomizer;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer; // 추가됨

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public WebSecurityCustomizer webSecurityCustomizer() {
        return (web) -> web.ignoring()
                .requestMatchers(new AntPathRequestMatcher("/swagger-ui.html"))
                .requestMatchers(new AntPathRequestMatcher("/swagger-ui/**"))
                .requestMatchers(new AntPathRequestMatcher("/v3/api-docs/**"))
                .requestMatchers(new AntPathRequestMatcher("/webjars/**"));
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            // CSRF 설정 (람다식 권장 방식으로 변경)
            .csrf(AbstractHttpConfigurer::disable)
            
            // HTTP 요청 권한 설정
            .authorizeHttpRequests(authz -> authz
                // ▼▼▼ [핵심 수정] 웹소켓 연결 경로 허용 ▼▼▼
                .requestMatchers("/sign/stream/**").permitAll()
                // ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                
                .requestMatchers("/health/**").permitAll()
                .requestMatchers("/train/**").permitAll()
                .requestMatchers("/booking/**").permitAll()
                .requestMatchers("/payment/**").permitAll()
                .requestMatchers("/h2-console/**").permitAll()
                .requestMatchers("/signlanguage/**").permitAll()
                // API로 시작하는 모든 요청을 일단 허용하려면 아래 줄 주석 해제
                // .requestMatchers("/api/**").permitAll()
                
                .anyRequest().authenticated()
            )
            // H2 Console 사용을 위한 Frame Options 설정
            .headers(headers -> headers.frameOptions(frame -> frame.disable()));
        
        return http.build();
    }
}