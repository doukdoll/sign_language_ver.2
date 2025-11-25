import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import { setTripType } from "../api/axios";  

export default function TripTypePage() {

  const navigate = useNavigate();

  const handleStart = async (type: "one-way" | "round") => {
    try {
     
      const res = await setTripType(type);
      console.log("triptype 응답:", res);

      
      navigate("/datetime", {
        state: { tripType: type },
      });

    } catch (error) {
      console.error("triptype 전송 실패:", error);
      alert("오류가 발생했습니다. 다시 시도해주세요.");
    }
  };

  return (
    <div className="flex justify-center w-screen h-screen bg-white to-gray-100">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl shadow-2xl flex flex-col">

        <Header title="여행 종류 선택" />

        <main className="mt-8 px-6">
          <p className="text-xl font-bold">어떤 방식으로 여행하시나요?</p>
          <p>편도 또는 왕복 중에서 선택해주세요.</p>
        </main>

        <div className="flex flex-row items-center gap-6 mt-6 mx-auto">

          {/* 편도 */}
          <button
            onClick={() => handleStart("one-way")}
            className="w-[180px] h-[200px] bg-blue-300 text-white hover:bg-blue-400 rounded-2xl shadow-md"
          >
            편도로 갈래요.
          </button>

          {/* 왕복 */}
          <button
            onClick={() => handleStart("round")}
            className="w-[180px] h-[200px] bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300 rounded-2xl shadow-md"
          >
            왕복으로 갈래요.
          </button>

        </div>

        <div className="w-[80%] bg-white border border-gray-200 px-4 py-3 mb-5 shadow-sm mt-6 mx-auto">
          <p className="text-sm text-gray-700">
            <span className="font-semibold text-gray-900">출발역:</span> 부산역
          </p>
          <p className="text-sm text-gray-700 mt-1">
            <span className="font-semibold text-gray-900">도착역:</span> 서울역
          </p>
        </div>

      </div>
    </div>
  );
}
