import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useLocation } from "react-router-dom"; // useLocation import 추가
import Header from "../components/Header";
import CameraFeed from "../components/recognition/CameraFeed";
import RecognitionResult from "../components/recognition/RecognitionResult";
import RecognitionButtons from "../components/recognition/RecognitionButton";
import { useRecognitionFlow } from "../hooks/useRecognitionFlow";

export default function ArrivalPage() {
  const navigate = useNavigate();
  const location = useLocation(); // useLocation 훅 사용
  const { departureStation } = location.state || {}; // departureStation 값 가져오기
  
  const { videoRef, state, startRecognition, stopRecognition, resetResult } = useRecognitionFlow({
    serverUrl: import.meta.env.VITE_RECOGNITION_SERVER_URL || 'ws://localhost:8080/api/sign/stream',
    targetFps: 30,
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
      navigate("/passenger", {
        state: {
          departureStation: departureStation, // 출발역 전달
          arrivalStation: state.recognizedLabel, // 도착역 전달
        },
      });
    }
  };

  return (
    <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-2xl flex flex-col overflow-hidden">
        <Header title="도착역 선택" />

        
          <div className="mt-6 px-10">
            <p className="text-[23px] text-[#3B4252] text-left font-bold mb-1">
              어느 역으로 가시겠어요?
            </p>
            <p className="text-gray-600 mb-6 text-left">
              도착역 이름을 수어로 표현해주세요.
            </p>
          </div>

            {/* 에러 표시 */}
            {state.error && (
              <div className="bg-red-100 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
                ⚠️ {state.error}
              </div>
            )}

            {/* 연결 상태 -- 화면 x*/}
            {/*
            {!state.isReady && state.isRecognizing && (
              <div className="bg-yellow-100 text-yellow-700 px-4 py-2 rounded-lg mb-4 text-sm">
                인식 서버 연결 중...
              </div>
            )}
            */}
         
            <div className="relative flex items-center justify-center w-full mb-4">
              <CameraFeed  
                videoRef={videoRef}
                isRecognizing={state.isRecognizing}
                recognized={state.recognizedLabel !== null}
                station={state.recognizedLabel}
              />

              {/* 인식 결과를 카메라 하단에 표시 */}
                {state.recognizedLabel && (
                    <div className="absolute  bottom-2 left-1/2 -translate-x-1/2 w-[80%] h-[18%]">
                        <RecognitionResult stationName={state.recognizedLabel} />
                    </div>
                )}
            </div>

            {/* 디버그 정보 --화면 x */}
            {/*{import.meta.env.DEV && (
              <div className="text-xs text-gray-500 mt-2 text-center">
                전송: {state.framesSent} | 확률: {state.recognizedProb?.toFixed(2) || 'N/A'}
              </div>
            )}*/}
            {/* 재시도 및 확인 버튼 */}
            <div className="flex-none w-full h-[80px] flex flex-col justify-center items-center">
            {state.recognizedLabel && (
              <div className="w-[84%]  h-[65px]">
                <RecognitionButtons
                onRetry={handleRetry}
                onConfirm={handleConfirm}
                />
              </div>
            )} 
            </div> 
            
          </div>
        
      </div>
   
  );
}
