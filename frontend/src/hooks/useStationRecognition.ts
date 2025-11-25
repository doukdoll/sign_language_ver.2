import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { recognizeSignLanguage } from "../api/axios";

// 출발역, 도착역 상태 관리

export type StepType = "departure" | "arrival";

export const useStationRecognition = () => {
  const [step, setStep] = useState<StepType>("departure");
  const [isRecognized, setIsRecognized] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const timer = setTimeout(() => setIsRecognized(true), 6000);
    return () => clearTimeout(timer);
  }, [step]);

  const handleConfirm = async () => {
    try {
      // 가짜 데이터 생성
      const fakeData =
        step === "departure"
          ? JSON.stringify({ gesture: "busan" }) // 출발지 테스트
          : JSON.stringify({ gesture: "seoul" }); // 도착지 테스트

      const result = await recognizeSignLanguage("city", fakeData);

      
      console.log("백엔드 응답:", result);

 
      if (step === "departure") {
        setStep("arrival");
        setIsRecognized(false);
      } else {
        navigate("/triptype");
      }
    } catch (error) {
      console.error("❌ API 호출 실패:", error);
    }
  };

  const handleBack = () => {
    if (step === "arrival") setStep("departure");
    else navigate(-1);
  };

  return {
    step,
    isRecognized,
    setIsRecognized,
    handleConfirm,
    handleBack,
    navigate,
  };
};
