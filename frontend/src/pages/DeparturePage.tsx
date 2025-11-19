import { useEffect, useMemo } from "react"; // ★ useMemo 추가 필수!
import { useNavigate } from "react-router-dom";
import CameraFeed from "../components/recognition/CameraFeed";
import RecognitionResult from "../components/recognition/RecognitionResult";
import RecognitionButtons from "../components/recognition/RecognitionButton";
import { useRecognitionFlow } from "../hooks/useRecognitionFlow";

export default function DeparturePage() {
    const navigate = useNavigate();

    // ★★★ [핵심 수정] 옵션 객체를 useMemo로 감싸서 기억시킵니다.
    // 이렇게 해야 페이지가 다시 그려져도 웹소켓이 끊기지 않습니다.
    const recognitionOptions = useMemo(() => ({
        serverUrl: import.meta.env.VITE_RECOGNITION_SERVER_URL || 'ws://localhost:8080/api/sign/stream',
        targetFps: 10,
        enableHandFilter: true,
        recognitionTarget: "DEPARTURE", // ★ 자바 서버를 위해 추가! (출발지 페이지니까)
        onRecognized: (label: string, prob: number) => {
            console.log(`출발역 인식 완료: ${label} (확률: ${prob})`);
            // 필요 시 자동 이동 로직
        },
    }), [navigate]); // navigate가 바뀔 때만 새로 생성

    // 위에서 만든 옵션을 여기에 넣어줍니다.
    const { videoRef, state, startRecognition, stopRecognition, resetResult } = useRecognitionFlow(recognitionOptions);

    // 페이지 진입 시 인식 자동 시작
    useEffect(() => {
        startRecognition();

        return () => {
            stopRecognition();
        };
    }, []); // 의존성 배열 비워둠 (한 번만 실행)

    const handleRetry = () => {
        resetResult();
        startRecognition();
    };

    const handleConfirm = () => {
        if (state.recognizedLabel) {
            // 전역 상태 저장 로직이 있다면 여기에 추가
            navigate('/arrival');
        }
    };

    return (
        <div className="flex flex-col items-center bg-gradient-to-b from-blue-50 to-white justify-start mt-8">
            <h1 className="text-xl font-bold mb-2">어느 역에서 출발하시겠어요?</h1>
            <p className="text-gray-600 mb-6">출발역 이름을 수어로 표현해주세요.</p>

            {/* 에러 표시 */}
            {state.error && (
                <div className="bg-red-100 text-red-700 px-4 py-2 rounded-lg mb-4">
                    ⚠️ {state.error}
                </div>
            )}

            {/* 연결 상태 표시 */}
            {!state.isReady && state.isRecognizing && (
                <div className="bg-yellow-100 text-yellow-700 px-4 py-2 rounded-lg mb-4">
                    인식 서버 연결 중...
                </div>
            )}

            {/* 카메라 피드 영역 */}
            <div className="relative flex items-center justify-center w-full mb-4">
                <CameraFeed
                    videoRef={videoRef}
                    isRecognizing={state.isRecognizing}
                    recognized={state.recognizedLabel !== null}
                    station={state.recognizedLabel}
                />

                {/* 인식 결과를 카메라 하단에 표시 */}
                {state.recognizedLabel && (
                    <div className="absolute bottom-1 left-1/2 -translate-x-1/2 w-[85%]">
                        <RecognitionResult stationName={state.recognizedLabel} />
                    </div>
                )}
            </div>

            {/* 디버그 정보 */}
            {import.meta.env.DEV && (
                <div className="text-xs text-gray-500 mb-2">
                    전송 프레임: {state.framesSent} | 확률: {state.recognizedProb?.toFixed(2) || 'N/A'}
                </div>
            )}

            {/* 재시도 및 확인 버튼 */}
            {state.recognizedLabel && (
                <div className="flex gap-4 mt-3 justify-center">
                    <RecognitionButtons
                        onRetry={handleRetry}
                        onConfirm={handleConfirm}
                    />
                </div>
            )}
        </div>
    );
}