import { Navigate, useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import { readReservationState } from "../utils/reservation";

export default function TripTypePage() {

    const navigate = useNavigate();
    const location = useLocation();

    const reservation = readReservationState(location.state);
    if (!reservation?.passengers) return <Navigate to="/" replace />;
    const { departureStation, arrivalStation, passengers } = reservation;

    const handleStart = (type: "one-way" | "round") => {
        navigate("/datetime", { state: { ...reservation, tripType: type } });
    };

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

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

                {/* 하단 정보 확인 창 */}
                <div className="w-[80%] bg-white border border-gray-200 px-4 py-3 mb-5 shadow-sm mt-6 mx-auto rounded-lg">
                    <p className="text-sm text-gray-700">
                        <span className="font-semibold text-gray-900">출발역:</span> {departureStation || "정보 없음"}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">
                        <span className="font-semibold text-gray-900">도착역:</span> {arrivalStation || "정보 없음"}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">
                        <span className="font-semibold text-gray-900">탑승 인원:</span> {passengers ? `${passengers}명` : "정보 없음"}
                    </p>
                </div>

            </div>
        </div>
    );
}
