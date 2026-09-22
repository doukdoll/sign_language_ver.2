import type { RefObject } from 'react';

interface CameraFeedProps {
  width?: string;
  height?: string;
  className?: string;
  isRecognizing?: boolean;
  videoRef: RefObject<HTMLVideoElement | null>;
}

/** Rendering only; useHolistic owns the camera and stops it on cleanup. */
export default function CameraFeed({
  width = '380px', height = '500px', className = '', isRecognizing, videoRef,
}: CameraFeedProps) {
  return (
    <div
      className={`relative rounded-xl overflow-hidden bg-black shadow-inner ${className}`}
      style={{ width, height }}
    >
      <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
      {isRecognizing && (
        <div className="absolute top-4 left-4 bg-red-500 text-white px-3 py-1 rounded-full text-sm">
          인식 중...
        </div>
      )}
    </div>
  );
}
