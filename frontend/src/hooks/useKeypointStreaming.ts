import { useEffect, useRef, useState, useCallback } from 'react';
import { RecognitionSession } from '../utils/recognitionSession';
import type { RecognitionTarget, StreamingState } from '../utils/recognitionSession';

export type { StreamingState } from '../utils/recognitionSession';
export interface StreamingOptions {
  enabled: boolean;
  serverUrl: string;
  targetFps?: number;
  recognitionTarget: RecognitionTarget;
  onRecognized?: (label: string | null, prob: number) => void;
  onError?: (error: Error) => void;
}

export function useKeypointStreaming(options: StreamingOptions) {
  const { enabled, serverUrl, targetFps = 10, recognitionTarget, onRecognized, onError } = options;
  const [state, setState] = useState<StreamingState>({ isConnected: false, framesSent: 0, lastError: null });
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const sessionRef = useRef<RecognitionSession | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastSentTimeRef = useRef(0);
  const callbacks = useRef({ onRecognized, onError });
  useEffect(() => { callbacks.current = { onRecognized, onError }; }, [onRecognized, onError]);

  useEffect(() => {
    if (!enabled) {
      setState(prev => ({ ...prev, isConnected: false }));
      return;
    }
    let disposed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let ackTimer: ReturnType<typeof setTimeout> | undefined;
    let retryDelay = 1000;
    let current: WebSocket | null = null;

    const connect = () => {
      if (disposed) return;
      const ws = new WebSocket(serverUrl.replace(/^http/, 'ws'));
      current = ws;
      wsRef.current = ws;
      const live = () => !disposed && current === ws;
      const session = new RecognitionSession(recognitionTarget,
        message => {
          ws.send(JSON.stringify(message));
          if (message.type === 'START_SESSION' || message.type === 'RESET_SESSION') {
            clearTimeout(ackTimer);
            ackTimer = setTimeout(() => {
              if (live() && session.phase !== 'active') {
                session.fail('인식 서버 확인 응답이 없습니다. 다시 연결합니다.');
                ws.close();
              }
            }, 10000);
          }
        },
        next => {
          if (!live()) return;
          if (next.isConnected) { clearTimeout(ackTimer); retryDelay = 1000; }
          setState(next);
        },
        (label, prob) => { if (live()) callbacks.current.onRecognized?.(label, prob); },
        error => { if (live()) callbacks.current.onError?.(error); });
      sessionRef.current = session;
      lastSentTimeRef.current = 0;
      setState({ isConnected: false, framesSent: 0, lastError: null });
      callbacks.current.onRecognized?.(null, 0);

      ws.onopen = () => { if (live()) session.start(); };
      ws.onmessage = event => {
        if (!live()) return;
        try { session.receive(JSON.parse(event.data)); }
        catch { session.fail('인식 서버 응답을 처리하지 못했습니다.'); ws.close(); }
      };
      ws.onerror = () => {
        if (live()) { session.fail('WebSocket 연결 오류'); ws.close(); }
      };
      ws.onclose = () => {
        if (!live()) return;
        clearTimeout(ackTimer);
        session.fail('인식 서버 연결이 종료되었습니다. 다시 연결합니다.');
        sessionRef.current = null;
        wsRef.current = null;
        reconnectTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 10000);
      };
    };
    try { connect(); }
    catch (error) {
      setState({ isConnected: false, framesSent: 0, lastError: 'WebSocket 주소 또는 연결 설정을 확인해주세요.' });
      callbacks.current.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
    return () => {
      disposed = true;
      clearTimeout(ackTimer);
      clearTimeout(reconnectTimer);
      if (current?.readyState === WebSocket.OPEN) {
        try { sessionRef.current?.end(); } catch { /* BE disconnect cleanup is the fallback. */ }
      }
      current?.close();
      if (wsRef.current === current) { wsRef.current = null; sessionRef.current = null; }
    };
  }, [enabled, serverUrl, recognitionTarget, connectionAttempt]);

  const resetSession = useCallback(() => {
    lastSentTimeRef.current = 0;
    try {
      if (wsRef.current?.readyState === WebSocket.OPEN && sessionRef.current?.reset()) return;
      // A pending reset is already in progress; do not advance revision twice.
      if (sessionRef.current?.phase === 'resetting' || sessionRef.current?.phase === 'starting') return;
    } catch { /* Retry with a fresh server-owned session. */ }
    setConnectionAttempt(value => value + 1);
  }, []);

  const sendKeypoints = useCallback((keypoints: number[][]) => {
    if (!enabled || wsRef.current?.readyState !== WebSocket.OPEN) return;
    const now = performance.now();
    if (now - lastSentTimeRef.current < 1000 / targetFps) return;
    try {
      if (sessionRef.current?.frame(keypoints)) lastSentTimeRef.current = now;
    } catch (error) {
      sessionRef.current?.fail(error instanceof Error ? error.message : '키포인트 전송 실패');
    }
  }, [enabled, targetFps]);

  return { sendKeypoints, state, resetSession };
}
