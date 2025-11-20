package com.capstone.dto;

import java.util.List;
// Lombok이 있다면 @Data 어노테이션을 쓰셔도 됩니다.
// 없다면 아래처럼 Getter/Setter를 다 적어줘야 합니다.

public class SignLanguageInputDto {

    // 1. 메시지 타입 (예: "KEYPOINT_FRAME")
    private String type;

    // 2. 세션 ID
    private String sessionId;

    // 타임스탬프
    private long timestamp;

    // 3. 프레임 번호
    private int frameIndex;

    // ★★★ 여기가 핵심! 이름은 keypoints, 타입은 리스트로 변경 ★★★
    // 기존: private String signLanguageData;
    private List<List<Double>> keypoints;

    // 4. 인식 대상 ("DEPARTURE", "ARRIVAL" 등)
    // 참고: 프론트엔드가 매 프레임마다 이걸 안 보낼 수도 있으니 Null 허용
    private String recognitionTarget;

    // --- Getter & Setter ---

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public int getFrameIndex() {
        return frameIndex;
    }

    public void setFrameIndex(int frameIndex) {
        this.frameIndex = frameIndex;
    }

    public long getTimestamp() {return timestamp;}

    public void setTimestamp(long timestamp) {this.timestamp = timestamp;}

    public List<List<Double>> getKeypoints() {
        return keypoints;
    }

    public void setKeypoints(List<List<Double>> keypoints) {
        this.keypoints = keypoints;
    }

    public String getRecognitionTarget() {
        return recognitionTarget;
    }

    public void setRecognitionTarget(String recognitionTarget) {
        this.recognitionTarget = recognitionTarget;
    }
}