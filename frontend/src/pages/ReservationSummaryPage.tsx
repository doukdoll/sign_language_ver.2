// src/pages/ReservationSummaryPage.tsx
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import PaymentPopup from "../components/PaymentPopup";
import Dimmed from "../components/Dimmed";

export default function ReservationSummaryPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { state } = location;

    console.log("📝 SummaryPage 최종 수신 데이터:", state);

    const {
        departureStation,
        arrivalStation,
        departureDate,
        passengers,
        selectedTrain1,
        selectedTrain2,
        seats1,
        seats2
    } = state || {};

    const [showPopup, setShowPopup] = useState(false);

    const formatDate = (dateInput: Date | string) => {
        if (!dateInput) return "-";
        const date = new Date(dateInput);
        const dayNames = ["일", "월", "화", "수", "목", "금", "토"];
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        const weekDay = dayNames[date.getDay()];
        return `${year}.${month}.${day} (${weekDay})`;
    };

    const formatTime = (isoString: string) => {
        if (!isoString) return "-";
        const date = new Date(isoString);
        return date.toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
        });
    };

    const unitPrice = selectedTrain1?.price || 0;
    const totalPrice = unitPrice * (passengers || 0);

    // 예매 정보 없으면 홈으로 보냄
    useEffect(() => {
        if (!state) {
            alert("예매 정보가 없습니다. 처음부터 다시 진행해주세요.");
            navigate("/");
        }
    }, [state, navigate]);

    const handleRetry = () => {
        navigate(-1);
    };

    return (
        <div className="flex justify-center w-screen h-screen bg-white">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

                <Header title="예매내역 확인" />

                <main className="flex flex-col px-6 mt-8">
                    <p className="text-center text-[17px] font-semibold mb-1">
                        선택하신 예매 정보를 확인해주세요.
                    </p>
                    <p className="text-center text-slate-600 text-sm mb-8">
                        결제를 진행하기 전 마지막 단계입니다.
                    </p>

                    <div className="bg-white rounded-xl shadow p-6 border border-blue-50">

                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                            <span className="text-blue-600">출발</span>
                            {departureStation || "출발역"}
                            <span className="text-gray-400">→</span>
                            <span className="text-red-500">도착</span>
                            {arrivalStation || "도착역"}
                        </h3>

                        <div className="text-sm text-gray-700 space-y-1 mb-4">
                            <p><span className="font-bold mr-2">날짜:</span>{formatDate(departureDate)}</p>
                            <p><span className="font-bold mr-2">출발:</span>{formatTime(selectedTrain1?.departureTime)}</p>
                            <p><span className="font-bold mr-2">도착:</span>{formatTime(selectedTrain1?.arrivalTime)}</p>
                        </div>

                        <hr className="my-3 border-t border-[#D5E1F2]" />

                        <div className="text-sm text-gray-700 space-y-2">
                            <p>
                                <span className="font-bold mr-2">열차:</span>
                                {selectedTrain1?.trainName || "정보 없음"}
                                <span className="text-xs text-gray-500 ml-1">
                                    ({selectedTrain1?.trainNumber})
                                </span>
                            </p>

                            <p className="flex items-start">
                                <span className="font-bold mr-2 shrink-0">좌석:</span>
                                <span className="text-blue-600 font-semibold break-words">
                                    일반실 / {seats1 ? seats1.join(", ") : "선택 없음"}
                                </span>
                            </p>

                            <p><span className="font-bold mr-2">승객:</span>성인 {passengers}명</p>
                        </div>

                        <hr className="my-3 border-t border-[#D5E1F2]" />

                        <div className="flex justify-between items-center mt-2">
                            <span className="font-semibold text-gray-800 text-base">총 결제 금액</span>
                            <span className="font-bold text-2xl text-[#3182F6]">
                                {totalPrice.toLocaleString()}원
                            </span>
                        </div>
                    </div>

                    {/* 버튼 영역 */}
                    <div className="flex gap-3 mt-10">
                        <button
                            onClick={handleRetry}
                            className="flex-1 py-4 bg-white border-[2px] border-[#3182F6] text-[#3182F6] rounded-xl font-bold hover:bg-blue-50 transition-colors"
                        >
                            다시 선택하기
                        </button>

                        <button
                            onClick={() => setShowPopup(true)}
                            className="flex-1 py-4 bg-[#3182F6] text-white rounded-xl font-bold hover:bg-blue-600 shadow-lg transition-colors"
                        >
                            결제하기
                        </button>
                    </div>
                </main>
            </div>

            {/* 결제 팝업 */}
            {showPopup && (
                <>
                    <Dimmed onClick={() => setShowPopup(false)} />

                    <PaymentPopup
                        totalPrice={totalPrice}
                        onSelect={(method) => {
                            setShowPopup(false);

                           
                            navigate("/payment", {
                                state: {
                                    ...state,
                                    paymentMethod: method,
                                    totalPrice
                                }
                            });
                        }}
                        onClose={() => setShowPopup(false)}
                    />
                </>
            )}
        </div>
    );
}
