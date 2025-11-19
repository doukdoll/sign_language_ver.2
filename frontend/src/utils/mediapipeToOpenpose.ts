/**
 * MediaPipe Holistic 결과를 OpenPose BODY_25 + Face70 + Hands42 형식으로 변환
 * 총 137개 키포인트 (25 + 70 + 42)
 * Python 코드(mediapipe_to_openpose.py)와 동일한 매핑 사용
 */

// MediaPipe Pose → OpenPose BODY_25 매핑 테이블
const MP_TO_BODY25_INDICES: (number | [number, number] | null)[] = [
  0,           // 0 Nose
  [11, 12],    // 1 Neck (avg of shoulders)
  12, 14, 16,  // 2-4 Right arm
  11, 13, 15,  // 5-7 Left arm
  [23, 24],    // 8 MidHip (avg of hips)
  24, 26, 28,  // 9-11 Right leg
  23, 25, 27,  // 12-14 Left leg
  5, 2, 8, 7,  // 15-18 Eyes/Ears
  31, null, 29,  // 19-21 Left foot
  32, null, 30   // 22-24 Right foot
];

// MediaPipe Face → OpenPose Face70 매핑 테이블
const MP_TO_FACE_INDICES: number[] = [
  356, 447, 401, 288, 397, 365, 378, 377, 152, 176, 150, 136, 172, 58, 132, 93, 127, // 0-16 Jawline
  107, 66, 105, 63, 70,  // 17-21 Right Eyebrow
  336, 296, 334, 293, 300,  // 22-26 Left Eyebrow
  168, 197, 5, 4,  // 27-30 Nose bridge
  59, 60, 2, 290, 289,  // 31-35 Nose bottom
  33, 160, 158, 133, 153, 163,  // 36-41 Right eye
  362, 385, 387, 263, 373, 380,  // 42-47 Left eye
  61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91, // 48-59 mouth outer
  78, 81, 13, 311, 308, 402, 14, 178,  // 60-67 mouth inner
  1, 2  // 68-69 nose tip points
];

export interface MediaPipeLandmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

export interface HolisticResults {
  poseLandmarks?: MediaPipeLandmark[];
  faceLandmarks?: MediaPipeLandmark[];
  leftHandLandmarks?: MediaPipeLandmark[];
  rightHandLandmarks?: MediaPipeLandmark[];
}

/**
 * MediaPipe Pose → OpenPose BODY_25 (25 × 3)
 */
function mediapipeToOpenPoseBody25(
  poseLandmarks: MediaPipeLandmark[] | undefined,
  width: number,
  height: number
): number[][] {
  const body25: number[][] = Array.from({ length: 25 }, () => [NaN, NaN, 0]);

  if (!poseLandmarks || poseLandmarks.length === 0) {
    return body25;
  }

  const points = poseLandmarks.map((p) => [
    p.x * width,
    p.y * height,
    p.visibility ?? 1.0
  ]);

  MP_TO_BODY25_INDICES.forEach((mpIdx, bodyIdx) => {
    if (mpIdx === null) {
      body25[bodyIdx] = [NaN, NaN, 0];
      return;
    }

    if (Array.isArray(mpIdx)) {
      // Neck, MidHip: 두 점의 평균
      const [i1, i2] = mpIdx;
      if (i1 < points.length && i2 < points.length) {
        const x = (points[i1][0] + points[i2][0]) / 2;
        const y = (points[i1][1] + points[i2][1]) / 2;
        const conf = (points[i1][2] + points[i2][2]) / 2;
        body25[bodyIdx] = [x, y, conf];
      } else {
        body25[bodyIdx] = [NaN, NaN, 0];
      }
    } else {
      // 일반 포인트
      if (mpIdx < points.length) {
        const [x, y, conf] = points[mpIdx];
        body25[bodyIdx] = [x, y, conf];
      } else {
        body25[bodyIdx] = [NaN, NaN, 0];
      }
    }
  });

  return body25;
}

/**
 * MediaPipe Face → OpenPose Face70 (70 × 3)
 */
function mediapipeToOpenPoseFace(
  faceLandmarks: MediaPipeLandmark[] | undefined,
  width: number,
  height: number
): number[][] {
  const face70: number[][] = Array.from({ length: 70 }, () => [NaN, NaN, 0]);

  if (!faceLandmarks || faceLandmarks.length === 0) {
    return face70;
  }

  const points = faceLandmarks.map((p) => [
    p.x * width,
    p.y * height,
    p.visibility ?? 1.0
  ]);

  MP_TO_FACE_INDICES.forEach((mpIdx, opIdx) => {
    if (mpIdx >= points.length) {
      face70[opIdx] = [0, 0, 0];
    } else {
      const [x, y, conf] = points[mpIdx];
      face70[opIdx] = [x, y, conf];
    }
  });

  return face70;
}

/**
 * MediaPipe Hands → OpenPose Hands42 (42 × 3)
 * Left hand: 0-20, Right hand: 21-41
 */
function mediapipeToOpenPoseHands(
  leftHandLandmarks: MediaPipeLandmark[] | undefined,
  rightHandLandmarks: MediaPipeLandmark[] | undefined,
  width: number,
  height: number
): number[][] {
  const hands42: number[][] = Array.from({ length: 42 }, () => [NaN, NaN, 0]);

  // Left hand (0-20)
  if (leftHandLandmarks && leftHandLandmarks.length > 0) {
    leftHandLandmarks.forEach((p, i) => {
      if (i < 21) {
        const x = isNaN(p.x) ? 0 : p.x * width;
        const y = isNaN(p.y) ? 0 : p.y * height;
        const conf = p.visibility ?? 1.0;
        hands42[i] = [x, y, conf];
      }
    });
  }

  // Right hand (21-41)
  if (rightHandLandmarks && rightHandLandmarks.length > 0) {
    rightHandLandmarks.forEach((p, i) => {
      if (i < 21) {
        const x = isNaN(p.x) ? 0 : p.x * width;
        const y = isNaN(p.y) ? 0 : p.y * height;
        const conf = p.visibility ?? 1.0;
        hands42[21 + i] = [x, y, conf];
      }
    });
  }

  return hands42;
}

/**
 * MediaPipe Holistic 결과를 OpenPose 137개 키포인트 배열로 변환
 * @param holisticResults MediaPipe Holistic 결과
 * @param width 영상 너비
 * @param height 영상 높이
 * @returns 137 × 3 배열 [[x, y, confidence], ...]
 */
export function buildKeypoints137(
  holisticResults: HolisticResults,
  width: number,
  height: number
): number[][] {
  const body25 = mediapipeToOpenPoseBody25(holisticResults.poseLandmarks, width, height);
  const face70 = mediapipeToOpenPoseFace(holisticResults.faceLandmarks, width, height);
  const hands42 = mediapipeToOpenPoseHands(
    holisticResults.leftHandLandmarks,
    holisticResults.rightHandLandmarks,
    width,
    height
  );

  // 137 = 25 + 70 + 42
  return [...body25, ...face70, ...hands42];
}

/**
 * 간단한 손 존재 여부 체크 (프론트 필터용)
 * 최소한의 손 키포인트가 있는지만 판단
 */
export function hasValidHands(keypoints137: number[][]): boolean {
  // Left hand: 95-115, Right hand: 116-136
  const leftHand = keypoints137.slice(95, 116);
  const rightHand = keypoints137.slice(116, 137);

  const leftValid = leftHand.filter(([x, y, c]) => !isNaN(x) && !isNaN(y) && c > 0).length;
  const rightValid = rightHand.filter(([x, y, c]) => !isNaN(x) && !isNaN(y) && c > 0).length;

  // 적어도 한 손에 5개 이상 키포인트가 있으면 유효
  return leftValid >= 5 || rightValid >= 5;
}

