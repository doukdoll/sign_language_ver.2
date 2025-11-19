import { useState, useCallback, useRef } from 'react';
import { Results } from '@mediapipe/holistic';
import { useHolistic } from './useHolistic';
import { useKeypointStreaming } from './useKeypointStreaming';
import { buildKeypoints137, hasValidHands } from '../utils/mediapipeToOpenpose';

export interface RecognitionFlowOptions {
  serverUrl: string;
  targetFps?: number;
  onRecognized?: (label: string, prob: number) => void;
  enableHandFilter?: boolean; // 손 필터 활성화 여부
}

export interface RecognitionFlowState {
  isRecognizing: boolean;
  isReady: boolean;
  recognizedLabel: string | null;
  recognizedProb: number | null;
  framesSent: number;
  error: string | null;
}

/**
 * 수어 인식 전체 플로우를 관리하는 통합 Hook
 * Holistic + Keypoint 변환 + 스트리밍을 하나로 묶음
 */
export function useRecognitionFlow(options: RecognitionFlowOptions) {
  const {
    serverUrl,
    targetFps = 10,
    onRecognized,
    enableHandFilter = true,
  } = options;

  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<RecognitionFlowState>({
    isRecognizing: false,
    isReady: false,
    recognizedLabel: null,
    recognizedProb: null,
    framesSent: 0,
    error: null,
  });

  // Holistic 결과 처리 콜백
  const handleHolisticResults = useCallback(
    (results: Results) => {
      if (!state.isRecognizing) return;

      try {
        const video = videoRef.current;
        if (!video) return;

        const width = video.videoWidth || 640;
        const height = video.videoHeight || 480;

        // 137개 키포인트로 변환
        const keypoints137 = buildKeypoints137(
          {
            poseLandmarks: results.poseLandmarks,
            faceLandmarks: results.faceLandmarks,
            leftHandLandmarks: results.leftHandLandmarks,
            rightHandLandmarks: results.rightHandLandmarks,
          },
          width,
          height
        );

        // 손 필터 적용 (옵션)
        if (enableHandFilter && !hasValidHands(keypoints137)) {
          return; // 손이 거의 없으면 전송 스킵
        }

        // 서버로 전송
        sendKeypoints(keypoints137);
      } catch (err) {
        console.error('키포인트 처리 실패:', err);
        setState((prev) => ({
          ...prev,
          error: err instanceof Error ? err.message : '키포인트 처리 실패',
        }));
      }
    },
    [state.isRecognizing, enableHandFilter]
  );

  // Holistic 초기화
  const { isReady: holisticReady, error: holisticError } = useHolistic(
    videoRef.current,
    {
      onResults: handleHolisticResults,
      enabled: state.isRecognizing,
    }
  );

  // 스트리밍 초기화
  const { sendKeypoints, state: streamingState } = useKeypointStreaming({
    enabled: state.isRecognizing,
    serverUrl,
    targetFps,
    onRecognized: (label, prob) => {
      setState((prev) => ({
        ...prev,
        recognizedLabel: label,
        recognizedProb: prob,
      }));
      if (onRecognized) {
        onRecognized(label, prob);
      }
    },
    onError: (error) => {
      setState((prev) => ({
        ...prev,
        error: error.message,
      }));
    },
  });

  // 상태 동기화
  useState(() => {
    setState((prev) => ({
      ...prev,
      isReady: holisticReady && streamingState.isConnected,
      framesSent: streamingState.framesSent,
      error: holisticError || streamingState.lastError || prev.error,
    }));
  });

  // 인식 시작
  const startRecognition = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isRecognizing: true,
      recognizedLabel: null,
      recognizedProb: null,
      error: null,
    }));
  }, []);

  // 인식 중지
  const stopRecognition = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isRecognizing: false,
    }));
  }, []);

  // 결과 초기화
  const resetResult = useCallback(() => {
    setState((prev) => ({
      ...prev,
      recognizedLabel: null,
      recognizedProb: null,
    }));
  }, []);

  return {
    videoRef,
    state,
    startRecognition,
    stopRecognition,
    resetResult,
  };
}

