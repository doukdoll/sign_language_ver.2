import { useState, useCallback, useRef } from 'react';
import type { Results } from '@mediapipe/holistic';
import { useHolistic } from './useHolistic';
import { useKeypointStreaming } from './useKeypointStreaming';
import type { RecognitionTarget } from '../utils/recognitionSession';
import { buildKeypoints137, hasValidHands } from '../utils/mediapipeToOpenpose';

export interface RecognitionFlowOptions {
  serverUrl: string;
  recognitionTarget: RecognitionTarget;
  targetFps?: number;
  onRecognized?: (label: string, prob: number) => void;
  enableHandFilter?: boolean;
}
export interface RecognitionFlowState {
  isRecognizing: boolean;
  isReady: boolean;
  recognizedLabel: string | null;
  recognizedProb: number | null;
  framesSent: number;
  error: string | null;
}

export function useRecognitionFlow(options: RecognitionFlowOptions) {
  const { serverUrl, recognitionTarget, targetFps = 10, onRecognized, enableHandFilter = true } = options;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [result, setResult] = useState<{ label: string | null; probability: number | null }>({
    label: null, probability: null,
  });
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [cameraAttempt, setCameraAttempt] = useState(0);
  const { sendKeypoints, state: streamingState, resetSession } = useKeypointStreaming({
    enabled: isRecognizing, serverUrl, targetFps, recognitionTarget,
    onRecognized: (label, probability) => {
      setResult({ label, probability: label ? probability : null });
      if (label) onRecognized?.(label, probability);
    },
    onError: () => setResult({ label: null, probability: null }),
  });

  const handleHolisticResults = useCallback((results: Results) => {
    if (!isRecognizing) return;
    try {
      const points = buildKeypoints137(results);
      if (!enableHandFilter || hasValidHands(points)) sendKeypoints(points);
    } catch (error) {
      setProcessingError(error instanceof Error ? error.message : '키포인트 처리 실패');
    }
  }, [isRecognizing, enableHandFilter, sendKeypoints]);

  const { isReady: holisticReady, error: holisticError } = useHolistic(videoRef, {
    onResults: handleHolisticResults, enabled: isRecognizing, restartKey: cameraAttempt,
  });
  const state: RecognitionFlowState = {
    isRecognizing,
    isReady: holisticReady && streamingState.isConnected,
    recognizedLabel: result.label,
    recognizedProb: result.probability,
    framesSent: streamingState.framesSent,
    error: holisticError || streamingState.lastError || processingError,
  };
  const startRecognition = useCallback(() => {
    setResult({ label: null, probability: null });
    setProcessingError(null);
    setIsRecognizing(true);
  }, []);
  const stopRecognition = useCallback(() => setIsRecognizing(false), []);
  const resetResult = useCallback(() => {
    setResult({ label: null, probability: null });
    setProcessingError(null);
    resetSession();
    if (holisticError) setCameraAttempt(attempt => attempt + 1);
  }, [resetSession, holisticError]);

  return { videoRef, state, startRecognition, stopRecognition, resetResult };
}

