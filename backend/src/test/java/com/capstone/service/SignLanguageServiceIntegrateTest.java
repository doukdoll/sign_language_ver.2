package com.capstone.service;

import com.capstone.dto.KeypointDto;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

/** HTTP contract tests, independent of historical CSV paths and a live AI model. */
class SignLanguageServiceIntegrateTest {
    private SignLanguageService service;
    private MockRestServiceServer server;
    private KeypointDto input;
    private static final String URL = "http://localhost:5001/predict_keypoints";

    @BeforeEach void setup() {
        RestTemplate rest = new RestTemplate();
        service = new SignLanguageService(rest);
        ReflectionTestUtils.setField(service, "flaskUrl", URL);
        server = MockRestServiceServer.bindTo(rest).build();
        input = new KeypointDto();
        input.setKeypoints(List.of(List.of(0.1, 0.2, 1.0)));
    }

    @Test void forwardsCurrentHttpPayloadAndPreservesCityResponse() {
        server.expect(requestTo(URL)).andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.recognitionTarget").value("ARRIVAL"))
                .andExpect(jsonPath("$.keypointData.keypoints[0][2]").value(1.0))
                .andRespond(withSuccess(
                        "{\"departureCity\":null,\"arrivalCity\":\"부산역\",\"recognizedProb\":98.7}", MediaType.APPLICATION_JSON));
        var result = service.recognizeCity_with_AI(input, "ARRIVAL");
        assertNull(result.getDepartureCity());
        assertEquals("부산역", result.getArrivalCity());
        server.verify();
    }

    @Test void preservesLegacyHttpClientErrorMapping() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.BAD_REQUEST)
                .contentType(MediaType.APPLICATION_JSON).body("{\"errorCode\":\"INVALID_TARGET\",\"errorMessage\":\"invalid target\"}"));
        var result = service.recognizeCity_with_AI(input, "");
        assertEquals("API 오류: 400", result.getDepartureCity());
        assertEquals("오류 원인: invalid target", result.getArrivalCity());
        server.verify();
    }

    @Test void preservesLegacyHttpServerErrorMapping() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                .contentType(MediaType.APPLICATION_JSON).body("{\"errorCode\":\"INFERENCE_FAILED\",\"errorMessage\":\"inference failed\"}"));
        var result = service.recognizeCity_with_AI(input, "DEPARTURE");
        assertEquals("API 오류: 500", result.getDepartureCity());
        assertEquals("오류 원인: inference failed", result.getArrivalCity());
        server.verify();
    }
}
