import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import CameraFeed from "../components/recognition/CameraFeed";
import RecognitionResult from "../components/recognition/RecognitionResult";
import RecognitionButtons from "../components/recognition/RecognitionButton";
import { useRecognitionFlow } from "../hooks/useRecognitionFlow";

export default function ArrivalPage() {
  const navigate = useNavigate();
  
  const { videoRef, state, startRecognition, stopRecognition, resetResult } = useRecognitionFlow({
    serverUrl: import.meta.env.VITE_RECOGNITION_SERVER_URL || 'ws://localhost:8080/api/sign/stream',
    targetFps: 10,
    enableHandFilter: true,
    onRecognized: (label, prob) => {
      console.log(`도착역 인식 완료: ${label} (확률: ${prob})`);
    },
  });

  useEffect(() => {
    startRecognition();
    return () => {
      stopRecognition();
    };
  }, []);

  const handleRetry = () => {
    resetResult();
    startRecognition();
  };

  const handleConfirm = () => {
    if (state.recognizedLabel) {
      navigate("/triptype");
    }
  };

  return (
    <div className="flex items-center justify-center bg-gray-100">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-2xl flex flex-col overflow-hidden">
        <Header title="도착역 선택" />

        <main className="flex flex-col flex-1 px-8 overflow-y-auto">
          <div className="mt-6">
            <p className="text-xl text-left font-bold mb-2">
              어느 역으로 가시겠어요?
            </p>
            <p className="text-gray-600 mb-6 text-left">
              도착역 이름을 수어로 표현해주세요.
            </p>

            {/* 에러 표시 */}
            {state.error && (
              <div className="bg-red-100 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
                ⚠️ {state.error}
              </div>
            )}

            {/* 연결 상태 */}
            {!state.isReady && state.isRecognizing && (
              <div className="bg-yellow-100 text-yellow-700 px-4 py-2 rounded-lg mb-4 text-sm">
                인식 서버 연결 중...
              </div>
            )}
         
            <div className="relative flex items-center justify-center w-full">
              <CameraFeed  
                videoRef={videoRef}
                isRecognizing={state.isRecognizing}
                recognized={state.recognizedLabel !== null}
                station={state.recognizedLabel}
              />

          
              {state.recognizedLabel && (
                <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-[85%]">
                  <RecognitionResult stationName={state.recognizedLabel} />
                </div>
              )}
            </div>

            {/* 디버그 정보 */}
            {import.meta.env.DEV && (
              <div className="text-xs text-gray-500 mt-2 text-center">
                전송: {state.framesSent} | 확률: {state.recognizedProb?.toFixed(2) || 'N/A'}
              </div>
            )}
          
            {state.recognizedLabel && (
              <div className="flex gap-4 mt-3 justify-center">
                <RecognitionButtons
                  onRetry={handleRetry}
                  onConfirm={handleConfirm}
                />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
