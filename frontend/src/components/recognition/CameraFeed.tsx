import { useRef, useEffect, forwardRef, useImperativeHandle } from "react";

interface CameraFeedProps {
  width?: string;
  height?: string;
  className?: string;
  isRecognizing?: boolean; 
  recognized?: boolean;    
  station?: string | null;
  videoRef?: React.RefObject<HTMLVideoElement | null>; // 외부에서 ref 주입 가능
}

export interface CameraFeedHandle {
  getVideoElement: () => HTMLVideoElement | null;
}

const CameraFeed = forwardRef<CameraFeedHandle, CameraFeedProps>(
  ({ 
    width = "310px", 
    height = "380px", 
    className = "", 
    videoRef: externalVideoRef,
    isRecognizing,
    recognized,
    station
  }, ref) => {
    const internalVideoRef = useRef<HTMLVideoElement | null>(null);
    
    // 외부 ref가 있으면 그것 사용, 없으면 내부 ref 사용
    const videoRef = externalVideoRef || internalVideoRef;

    // 외부에서 video element 접근할 수 있게
    useImperativeHandle(ref, () => ({
      getVideoElement: () => videoRef.current,
    }));

    useEffect(() => {
      const startCamera = async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ 
            video: {
              width: { ideal: 640 },
              height: { ideal: 480 },
              facingMode: 'user'
            } 
          });
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        } catch (err) {
          console.error("카메라 접근 실패:", err);
          alert("카메라 접근을 허용해주세요!");
        }
      };

      startCamera();

      return () => {
        if (videoRef.current?.srcObject) {
          const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
          tracks.forEach((track) => track.stop());
        }
      };
    }, []);

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
        
        {/* 인식 완료 표시 (옵션) */}
        {recognized && station && (
          <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm">
            ✓ {station}
          </div>
        )}
      </div>
    );
  }
);

CameraFeed.displayName = "CameraFeed";

export default CameraFeed;
