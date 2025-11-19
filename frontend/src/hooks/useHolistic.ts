import { useEffect, useRef, useState } from 'react';
import { Holistic, Results } from '@mediapipe/holistic';
import { Camera } from '@mediapipe/camera_utils';

export interface UseHolisticOptions {
  onResults?: (results: Results) => void;
  enabled?: boolean;
}

export interface UseHolisticReturn {
  isReady: boolean;
  error: string | null;
}

/**
 * MediaPipe Holistic을 초기화하고 비디오 프레임을 처리하는 Hook
 * @param videoElement 비디오 엘리먼트 ref
 * @param options 옵션 (onResults 콜백, enabled 플래그)
 */
export function useHolistic(
  videoElement: HTMLVideoElement | null,
  options: UseHolisticOptions = {}
): UseHolisticReturn {
  const { onResults, enabled = true } = options;
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const holisticRef = useRef<Holistic | null>(null);
  const cameraRef = useRef<Camera | null>(null);

  useEffect(() => {
    if (!videoElement || !enabled) {
      setIsReady(false);
      return;
    }

    let mounted = true;

    const initHolistic = async () => {
      try {
        // Holistic 인스턴스 생성
        const holistic = new Holistic({
          locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/holistic/${file}`;
          },
        });

        // 설정
        holistic.setOptions({
          modelComplexity: 1,
          smoothLandmarks: true,
          enableSegmentation: false,
          smoothSegmentation: false,
          refineFaceLandmarks: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        // 결과 콜백 등록
        holistic.onResults((results: Results) => {
          if (mounted && onResults) {
            onResults(results);
          }
        });

        await holistic.initialize();
        holisticRef.current = holistic;

        // Camera 유틸 초기화
        const camera = new Camera(videoElement, {
          onFrame: async () => {
            if (holisticRef.current && mounted) {
              await holisticRef.current.send({ image: videoElement });
            }
          },
          width: 640,
          height: 480,
        });

        cameraRef.current = camera;
        await camera.start();

        if (mounted) {
          setIsReady(true);
          setError(null);
        }
      } catch (err) {
        console.error('Holistic 초기화 실패:', err);
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Holistic 초기화 실패');
          setIsReady(false);
        }
      }
    };

    initHolistic();

    return () => {
      mounted = false;
      if (cameraRef.current) {
        cameraRef.current.stop();
        cameraRef.current = null;
      }
      if (holisticRef.current) {
        holisticRef.current.close();
        holisticRef.current = null;
      }
      setIsReady(false);
    };
  }, [videoElement, enabled, onResults]);

  return { isReady, error };
}

