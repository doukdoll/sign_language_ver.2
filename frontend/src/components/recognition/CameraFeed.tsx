import { useRef, useEffect, forwardRef, useImperativeHandle } from "react";

interface CameraFeedProps {
  width?: string;
  height?: string;
  className?: string;
  isRecognizing?: boolean; 
  videoRef?: React.RefObject<HTMLVideoElement | null>; // 외부에서 ref 주입 가능
}

export interface CameraFeedHandle {
  getVideoElement: () => HTMLVideoElement | null;
}

const CameraFeed = forwardRef<CameraFeedHandle, CameraFeedProps>(
  ({ 
    width = "380px", 
    height = "500px", 
    className = "", 
    videoRef: externalVideoRef,
    isRecognizing
  }, ref) => {
    const internalVideoRef = useRef<HTMLVideoElement | null>(null);
    
    // 외부 ref가 있으면 그것 사용, 없으면 내부 ref 사용
    const videoRef = externalVideoRef || internalVideoRef;

    // 외부에서 video element 접근할 수 있게
    useImperativeHandle(ref, () => ({
      getVideoElement: () => videoRef.current,
    }));

    useEffect(() => {
      const video = videoRef.current;
      if (!video) return;

      let cancelled = false;
      let ownedStream: MediaStream | undefined;
      const startCamera = async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ 
            video: {
              width: { ideal: 640 },
              height: { ideal: 480 },
              facingMode: 'user'
            } 
          });
          // 권한 응답을 기다리는 동안 화면을 떠났다면 늦게 열린 스트림도 종료합니다.
          if (cancelled) {
            stream.getTracks().forEach((track) => track.stop());
            return;
          }
          ownedStream = stream;
          video.srcObject = stream;
        } catch (err) {
          if (cancelled) return;
          console.error("카메라 접근 실패:", err);
          alert("카메라 접근을 허용해주세요!");
        }
      };

      startCamera();

      return () => {
        cancelled = true;
        ownedStream?.getTracks().forEach((track) => track.stop());
        if (ownedStream && video.srcObject === ownedStream) {
          video.srcObject = null;
        }
      };
    }, [videoRef]);

    return (
      <div
        className={`relative rounded-xl overflow-hidden bg-black shadow-inner ${className}`}
        style={{ width, height }}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
        
        {/* 인식 상태 표시 (옵션) */}
        {isRecognizing && (
          <div className="absolute top-4 left-4 bg-red-500 text-white px-3 py-1 rounded-full text-sm">
            인식 중...
          </div>
        )}
        
      </div>
    );
  }
);

CameraFeed.displayName = "CameraFeed";

export default CameraFeed;
