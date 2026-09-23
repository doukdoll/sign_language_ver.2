import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { Holistic } from '@mediapipe/holistic';
import type { Results } from '@mediapipe/holistic';
import { startCameraPipeline } from '../utils/cameraPipeline';

export interface UseHolisticOptions {
  onResults?: (results: Results) => void;
  enabled?: boolean;
  restartKey?: number;
}

export function useHolistic(
  videoRef: RefObject<HTMLVideoElement | null>,
  { onResults, enabled = true, restartKey = 0 }: UseHolisticOptions = {},
) {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsCallback = useRef(onResults);
  useEffect(() => { resultsCallback.current = onResults; }, [onResults]);

  useEffect(() => {
    setIsReady(false);
    setError(null);
    const video = videoRef.current;
    if (!enabled || !video) return;

    return startCameraPipeline<Results>({
      video,
      getStream: () => navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      }),
      createProcessor: () => {
        const holistic = new Holistic({
          locateFile: file => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`,
        });
        holistic.setOptions({
          modelComplexity: 1,
          smoothLandmarks: true,
          enableSegmentation: false,
          smoothSegmentation: false,
          refineFaceLandmarks: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });
        return holistic;
      },
      onResults: results => resultsCallback.current?.(results),
      onReady: () => setIsReady(true),
      onError: failure => {
        console.error('카메라/MediaPipe 실행 실패:', failure);
        setIsReady(false);
        setError(failure.message || '카메라 권한과 연결 상태를 확인해주세요.');
      },
      schedule: callback => requestAnimationFrame(callback),
      cancel: id => cancelAnimationFrame(id),
    });
  }, [videoRef, enabled, restartKey]);

  return { isReady, error };
}
