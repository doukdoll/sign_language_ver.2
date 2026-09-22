/** A single owner for the media stream, processor and cancellable frame loop. */
export interface VideoProcessor<T> {
  initialize(): Promise<void>;
  onResults(callback: (results: T) => void): void;
  send(input: { image: HTMLVideoElement }): Promise<void>;
  close(): Promise<void>;
}

interface CameraPipelineOptions<T> {
  video: HTMLVideoElement;
  getStream: () => Promise<MediaStream>;
  createProcessor: () => VideoProcessor<T>;
  onResults: (results: T) => void;
  onReady: () => void;
  onError: (error: Error) => void;
  schedule: (callback: FrameRequestCallback) => number;
  cancel: (id: number) => void;
}

export function startCameraPipeline<T>(options: CameraPipelineOptions<T>): () => void {
  const { video, getStream, createProcessor, onResults, onReady, onError, schedule, cancel } = options;
  let disposed = false;
  let closed = false;
  let stream: MediaStream | undefined;
  let processor: VideoProcessor<T> | undefined;
  let frameId: number | undefined;
  let lastVideoTime = -1;
  let currentOperation: Promise<void> = Promise.resolve();

  const closeProcessor = async () => {
    if (!processor || closed) return;
    closed = true;
    try { await processor.close(); }
    catch (error) { console.warn('MediaPipe 종료 실패:', error); }
  };

  const dispose = () => {
    if (disposed) return;
    disposed = true;
    if (frameId !== undefined) cancel(frameId);
    stream?.getTracks().forEach(track => {
      track.removeEventListener('ended', handleTrackEnded);
      track.stop();
    });
    if (stream && video.srcObject === stream) video.srcObject = null;
    // Do not close the WASM processor while initialize/send is still running.
    void currentOperation.then(closeProcessor, closeProcessor);
  };

  const fail = (error: unknown) => {
    if (disposed) return;
    dispose();
    onError(error instanceof Error ? error : new Error(String(error)));
  };

  const handleTrackEnded = () => fail(new Error('카메라 연결이 끊어졌습니다. 연결과 권한을 확인한 뒤 다시 시도해주세요.'));

  const processFrame = async () => {
    if (disposed || !processor) return;
    // Skip not-yet-loaded and duplicate frames, and never overlap send calls.
    if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
      lastVideoTime = video.currentTime;
      await processor.send({ image: video });
    }
    if (!disposed) frameId = schedule(tick);
  };

  const tick = () => {
    frameId = undefined;
    if (!disposed) currentOperation = processFrame().catch(fail);
  };

  const initialize = async () => {
    const acquired = await getStream();
    // getUserMedia cannot be cancelled while a permission prompt is pending.
    if (disposed) {
      acquired.getTracks().forEach(track => track.stop());
      return;
    }
    stream = acquired;
    stream.getTracks().forEach(track => track.addEventListener('ended', handleTrackEnded));
    video.srcObject = stream;
    processor = createProcessor();
    processor.onResults(results => { if (!disposed) onResults(results); });
    await processor.initialize();
    if (disposed) return;
    onReady();
    if (!disposed) frameId = schedule(tick);
  };

  currentOperation = initialize().catch(fail);
  return dispose;
}
