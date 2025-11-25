// 임시 출발역 입력
import { useState } from "react";

export function useRecognition() {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const startRecognition = async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000)); // 시뮬레이션
    setResult("부산"); // 임시 결과
    setLoading(false);
  };

  const resetRecognition = () => setResult(null);

  return { result, loading, startRecognition, resetRecognition };
}