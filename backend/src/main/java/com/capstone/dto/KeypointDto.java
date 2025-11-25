package com.capstone.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class KeypointDto {
    // 프론트엔드가 "keypoints"라는 이름으로 보내므로, 여기서도 똑같이 맞춰야 합니다.
    // MediaPipe의 137개 점이 하나의 긴 리스트로 들어옵니다.
    private List<List<Double>> keypoints;
}