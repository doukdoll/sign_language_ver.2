import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setPassengers } from "../api/axios";
import Header from "../components/Header";

export default function PassengerPage() {
  const navigate = useNavigate();
  const [count, setCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const handleNext = async () => {
    if (count === null) return alert("탑승 인원을 선택해주세요.");
    
    try {
      setLoading(true);
      
      
    const res = await setPassengers(count);
    console.log("서버 응답:", res); 
      
      // 성공 시 다음 페이지로 이동
      navigate("/triptype", { 
        state: { passengers: count } 
      });
      
    } catch (error) {
      console.error("탑승 인원 전송 실패:", error);
      alert("오류가 발생했습니다. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const passengerOptions = [1, 2, 3, 4, 5];

  return (
    <div className="flex justify-center w-screen h-screen bg-white">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

        <Header title="탑승 인원 선택" />

        <main className="flex flex-col items-center mt-10 px-6">

          <p className="text-xl font-bold mb-4">탑승 인원을 선택해주세요.</p>
          <p className="text-slate-600 mb-6">큰 버튼을 눌러 인원을 선택할 수 있어요.</p>

          {/* 숫자 선택 버튼 */}
          <div className="grid grid-cols-3 gap-4 mt-4">
            {passengerOptions.map((num) => (
              <button
                key={num}
                onClick={() => setCount(num)}
                disabled={loading}
                className={`w-24 h-24 rounded-2xl flex items-center justify-center text-3xl font-bold border 
                  ${
                    count === num
                      ? "bg-blue-600 text-white border-blue-700"
                      : "bg-white text-slate-700 border-slate-300"
                  }
                  ${loading ? "opacity-50 cursor-not-allowed" : ""}
                `}
              >
                {num}
              </button>
            ))}
          </div>

         
          {count !== null && (
            <div className="mt-6 text-center">
              <p className="text-xl font-bold text-black">
                탑승 인원: {count}명
              </p>
            </div>
          )}

          {/* 다음 버튼 */}
          <button
            onClick={handleNext}
            disabled={loading}
            className="mt-10 px-8 py-4 bg-blue-600 text-white text-lg font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "전송 중..." : "다음"}
          </button>
        </main>
      </div>
    </div>
  );
}