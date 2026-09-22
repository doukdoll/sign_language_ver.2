import { useState } from "react";
import { Navigate, useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import { readReservationState } from "../utils/reservation";

export default function PassengerPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const reservation = readReservationState(location.state);

    const [count, setCount] = useState<number | null>(null);
    if (!reservation) return <Navigate to="/" replace />;

    const handleNext = () => {
        if (count === null) return alert("탑승 인원을 선택해주세요.");
        navigate("/triptype", { state: { ...reservation, passengers: count } });
    };

    const passengerOptions = [1, 2, 3, 4, 5];

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
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
                                className={`w-24 h-24 rounded-2xl flex items-center justify-center text-3xl font-bold border 
                  ${
                                    count === num
                                        ? "bg-blue-600 text-white border-blue-700"
                                        : "bg-white text-slate-700 border-slate-300"
                                }
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
                        disabled={count === null}
                        className="mt-10 px-8 py-4 bg-blue-600 text-white text-lg font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        다음
                    </button>
                </main>
            </div>
        </div>
    );
}
