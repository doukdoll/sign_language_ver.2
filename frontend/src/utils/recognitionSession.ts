export type RecognitionTarget = 'DEPARTURE' | 'ARRIVAL';
export type Keypoint = [number | null, number | null, number];
export interface StreamingState {
  isConnected: boolean;
  framesSent: number;
  lastError: string | null;
}
type Message = Record<string, unknown>;
const integer = (value: unknown): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;

export function normalizeKeypoints(points: number[][]): Keypoint[] {
  if (points.length !== 137) throw new Error('키포인트는 137개여야 합니다.');
  return points.map(point => {
    if (point.length !== 3) throw new Error('키포인트는 [x, y, confidence] 형식이어야 합니다.');
    const [x, y, confidence] = point;
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1)
      throw new Error('키포인트 confidence가 올바르지 않습니다.');
    if (confidence === 0 || !Number.isFinite(x) || !Number.isFinite(y)) return [null, null, 0];
    return [x, y, confidence];
  });
}

/** Transport-independent v1 state machine; tested without a camera or React. */
export class RecognitionSession {
  sessionId: string | null = null;
  revision = 0;
  phase: 'starting' | 'active' | 'resetting' | 'failed' | 'ended' = 'starting';
  frameIndex = 0;
  lastResultIndex = -1;
  target: RecognitionTarget;
  private send: (message: Message) => void;
  private changed: (state: StreamingState) => void;
  private recognized: (label: string | null, probability: number) => void;
  private failed: (error: Error) => void;
  private now: () => number;
  private lastError: string | null = null;

  constructor(target: RecognitionTarget, send: (message: Message) => void,
    changed: (state: StreamingState) => void,
    recognized: (label: string | null, probability: number) => void,
    failed: (error: Error) => void, now = Date.now) {
    this.target = target;
    this.send = send;
    this.changed = changed;
    this.recognized = recognized;
    this.failed = failed;
    this.now = now;
  }

  private message(type: string): Message {
    return { protocolVersion: 1, type, revision: this.revision, timestamp: this.now(),
      ...(this.sessionId ? { sessionId: this.sessionId } : {}) };
  }

  private publish(lastError: string | null = this.lastError) {
    this.lastError = lastError;
    this.changed({ isConnected: this.phase === 'active', framesSent: this.frameIndex, lastError });
  }

  start() {
    this.publish();
    this.send({ ...this.message('START_SESSION'), recognitionTarget: this.target });
  }

  fail(message: string) {
    this.phase = 'failed';
    this.recognized(null, 0);
    this.publish(message);
    this.failed(new Error(message));
  }

  receive(value: unknown) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return;
    const message = value as Message;
    if (message.protocolVersion !== 1 || !integer(message.timestamp)) return;
    if (this.phase === 'ended') return;
    if (this.sessionId && message.sessionId !== this.sessionId) return;
    if (message.type === 'ERROR') {
      const terminal = ['AI_UNAVAILABLE', 'SESSION_EXPIRED', 'SESSION_NOT_FOUND'].includes(String(message.errorCode));
      if (!terminal && message.revision !== this.revision) return;
      this.fail(String(message.errorMessage || message.errorCode || '인식 서버 오류'));
      return;
    }
    if (message.revision !== this.revision || message.recognitionTarget !== this.target) return;
    if ((message.type === 'SESSION_STARTED' && this.phase === 'starting') ||
        (message.type === 'SESSION_RESET' && this.phase === 'resetting')) {
      if (typeof message.sessionId !== 'string' || !message.sessionId) return;
      this.sessionId = message.sessionId;
      this.phase = 'active';
      this.frameIndex = 0;
      this.lastResultIndex = -1;
      this.publish(null);
      return;
    }
    if (message.type !== 'RESULT' || this.phase !== 'active' || !this.sessionId) return;
    if (!integer(message.frameIndex) || message.frameIndex <= this.lastResultIndex ||
        message.frameIndex >= this.frameIndex) return;
    const label = this.target === 'DEPARTURE' ? message.departureCity : message.arrivalCity;
    const other = this.target === 'DEPARTURE' ? message.arrivalCity : message.departureCity;
    const probability = message.recognizedProb;
    if (typeof label !== 'string' || !label || other !== null || typeof probability !== 'number' ||
        !Number.isFinite(probability) || probability < 0 || probability > 100) return;
    this.lastResultIndex = message.frameIndex;
    this.recognized(label === '<unk>' ? null : label, probability);
    this.publish(label === '<unk>' ? '역을 인식하지 못했습니다. 다시 시도해주세요.' : null);
  }

  frame(points: number[][]): boolean {
    if (this.phase !== 'active') return false;
    const keypoints = normalizeKeypoints(points);
    this.send({ ...this.message('KEYPOINT_FRAME'), recognitionTarget: this.target,
      frameIndex: this.frameIndex, keypoints });
    this.frameIndex += 1;
    this.publish();
    return true;
  }

  reset(): boolean {
    if (!this.sessionId || !['active', 'failed'].includes(this.phase)) return false;
    this.revision += 1;
    this.phase = 'resetting'; // Invalidate old results immediately, before sending.
    this.frameIndex = 0;
    this.lastResultIndex = -1;
    this.recognized(null, 0);
    this.publish(null);
    this.send({ ...this.message('RESET_SESSION'), recognitionTarget: this.target });
    return true;
  }

  end() {
    if (this.sessionId && this.phase !== 'ended') this.send(this.message('END_SESSION'));
    this.phase = 'ended';
  }
}
