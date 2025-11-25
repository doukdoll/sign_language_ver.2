import { useState } from "react";
<<<<<<< HEAD
import { useNavigate } from "react-router-dom";
=======
import { useNavigate, useLocation } from "react-router-dom"; // useLocation 추가
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
import { setPassengers } from "../api/axios";
import Header from "../components/Header";

export default function PassengerPage() {
  const navigate = useNavigate();
<<<<<<< HEAD
=======
  const location = useLocation(); // location 훅 사용
  
  // 이전 페이지(ArrivalPage)에서 넘겨준 역 정보 받기
  const { departureStation, arrivalStation } = location.state || {}; 

>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
  const [count, setCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const handleNext = async () => {
    if (count === null) return alert("탑승 인원을 선택해주세요.");
    
    try {
      setLoading(true);
      
<<<<<<< HEAD
      
    const res = await setPassengers(count);
    console.log("서버 응답:", res); 
      
      // 성공 시 다음 페이지로 이동
      navigate("/triptype", { 
        state: { passengers: count } 
=======
      const res = await setPassengers(count);
      console.log("서버 응답:", res); 
      
      // 수정된 부분: 다음 페이지로 모든 정보(출발, 도착, 인원) 전달
      navigate("/triptype", { 
        state: { 
          departureStation: departureStation, // 전달받은 출발역 토스
          arrivalStation: arrivalStation,     // 전달받은 도착역 토스
          passengers: count                   // 선택한 인원 추가
        } 
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
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
<<<<<<< HEAD
=======
          
          {/* (디버깅용 - 개발 완료 후 삭제 가능) 현재 데이터 흐름 확인 */}
          {import.meta.env.DEV && (
            <div className="text-xs text-gray-400 mb-2">
               경로: {departureStation} → {arrivalStation}
            </div>
          )}
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe

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
<<<<<<< HEAD

=======
>>>>>>> 16050c606410d1b1d9b375acfda5d3cba57bcafe
         
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