import { useEffect, useRef, useState, useCallback } from 'react';

export interface StreamingOptions {
    enabled: boolean;
    serverUrl: string;
    targetFps?: number;
    recognitionTarget?: string;
    onRecognized?: (label: string, prob: number) => void;
    onError?: (error: Error) => void;
}

export interface StreamingState {
    isConnected: boolean;
    framesSent: number;
    lastError: string | null;
}

export function useKeypointStreaming(options: StreamingOptions) {
    const {
        enabled,
        serverUrl,
        targetFps = 10,
        recognitionTarget = "DEPARTURE",
        onRecognized,
        onError,
    } = options;

    const [state, setState] = useState<StreamingState>({
        isConnected: false,
        framesSent: 0,
        lastError: null,
    });

    const wsRef = useRef<WebSocket | null>(null);
    const lastSentTimeRef = useRef<number>(0);
    const frameCountRef = useRef<number>(0);
    // 🔍 로그 폭탄 방지용 카운터 (30번에 1번만 찍기 위함)
    const logThrottleRef = useRef<number>(0);

    const sessionIdRef = useRef<string>(
        `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    );

    const onRecognizedRef = useRef(onRecognized);
    const onErrorRef = useRef(onError);

    useEffect(() => {
        onRecognizedRef.current = onRecognized;
        onErrorRef.current = onError;
    }, [onRecognized, onError]);

    useEffect(() => {
        if (!enabled) {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            setState((prev) => ({ ...prev, isConnected: false }));
            return;
        }

        const connectWebSocket = () => {
            try {
                const wsUrl = serverUrl.replace(/^http/, 'ws');
                const ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    console.log('WebSocket 연결 성공');
                    setState((prev) => ({ ...prev, isConnected: true, lastError: null }));

                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({
                            type: 'START_SESSION',
                            sessionId: sessionIdRef.current,
                            timestamp: Date.now(),
                            recognitionTarget: recognitionTarget
                        }));
                    }
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        // 서버로부터 온 응답 로그 (디버깅용)
                        console.log("📩 서버 응답 수신:", data);

                        if (data.departureCity && onRecognizedRef.current) {
                            onRecognizedRef.current(data.departureCity, data.recognizedProb ?? 0);
                        } else if (data.type === 'RESULT' && onRecognizedRef.current) {
                            onRecognizedRef.current(data.label, data.prob ?? 0);
                        }
                    } catch (err) {
                        console.error('메시지 파싱 실패:', err);
                    }
                };

                ws.onerror = (event) => {
                    console.error('WebSocket 에러:', event);
                    setState((prev) => ({
                        ...prev,
                        isConnected: false,
                        lastError: 'WebSocket 연결 오류',
                    }));
                    if (onErrorRef.current) {
                        onErrorRef.current(new Error('WebSocket 연결 오류'));
                    }
                };

                ws.onclose = () => {
                    console.log('WebSocket 연결 종료');
                    setState((prev) => ({ ...prev, isConnected: false }));
                    wsRef.current = null;
                };

                wsRef.current = ws;
            } catch (err) {
                console.error('WebSocket 초기화 실패:', err);
                setState((prev) => ({
                    ...prev,
                    lastError: err instanceof Error ? err.message : 'WebSocket 초기화 실패',
                }));
                if (onErrorRef.current && err instanceof Error) {
                    onErrorRef.current(err);
                }
            }
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [enabled, serverUrl, recognitionTarget]);

    const sendKeypoints = useCallback(
        (keypoints: number[][]) => {
            if (!enabled || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                return;
            }

            const now = Date.now();
            const minInterval = 1000 / targetFps;
            if (now - lastSentTimeRef.current < minInterval) {
                return;
            }

            const sanitizedKeypoints = keypoints.map(point =>
                point.map(val => val ?? 0)
            );

            try {
                const message = {
                    type: 'KEYPOINT_FRAME',
                    sessionId: sessionIdRef.current,
                    timestamp: now,
                    frameIndex: frameCountRef.current++,
                    keypoints: sanitizedKeypoints,
                    recognitionTarget: recognitionTarget
                };

                // 🔍 [디버깅용] 30프레임마다 한 번씩 전송 데이터 로그 출력
                logThrottleRef.current += 1;
                if (logThrottleRef.current % 30 === 0) {
                    console.log("🚀 [전송 중] WebSocket 데이터 확인:", message);
                    console.log(`   - 키포인트 개수: ${sanitizedKeypoints.length}`);
                    console.log(`   - 타겟: ${recognitionTarget}`);
                }

                wsRef.current.send(JSON.stringify(message));
                lastSentTimeRef.current = now;
                setState((prev) => ({ ...prev, framesSent: prev.framesSent + 1 }));
            } catch (err) {
                console.error('키포인트 전송 실패:', err);
                if (onErrorRef.current && err instanceof Error) {
                    onErrorRef.current(err);
                }
            }
        },
        [enabled, targetFps, recognitionTarget]
    );

    return {
        sendKeypoints,
        state,
    };
}