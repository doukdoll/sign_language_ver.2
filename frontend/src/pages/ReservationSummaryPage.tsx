import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import PaymentPopup from "../components/PaymentPopup";
import Dimmed from "../components/Dimmed";
import { getReservationLegs, getReservationTotal, readReservationState } from "../utils/reservation";

const formatDate = (value: string) => new Date(value).toLocaleDateString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit", weekday: "short",
});
const formatTime = (value: string) => new Date(value).toLocaleTimeString("ko-KR", {
    hour: "2-digit", minute: "2-digit", hour12: false,
});

export default function ReservationSummaryPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const reservation = readReservationState(location.state);
    const legs = getReservationLegs(reservation);
    const totalPrice = getReservationTotal(reservation);
    const [showPopup, setShowPopup] = useState(false);
    if (!reservation || totalPrice === null) return <Navigate to="/" replace />;

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">
                <Header title="예매내역 확인" />
                <main className="flex flex-col px-6 mt-8 overflow-y-auto pb-8">
                    <p className="text-center text-[17px] font-semibold mb-1">선택하신 예매 정보를 확인해주세요.</p>
                    <p className="text-center text-slate-600 text-sm mb-8">결제를 진행하기 전 마지막 단계입니다.</p>
                    <div className="space-y-4">
                        {legs.map(({ title, train, seats }) => (
                            <div key={title} className="bg-white rounded-xl shadow p-6 border border-blue-50">
                                {legs.length > 1 && <p className="text-sm text-blue-600 font-bold mb-2">{title}</p>}
                                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                                    <span className="text-blue-600">출발</span>{train.departureStation}
                                    <span className="text-gray-400">→</span>
                                    <span className="text-red-500">도착</span>{train.arrivalStation}
                                </h3>
                                <div className="text-sm text-gray-700 space-y-1 mb-4">
                                    <p><span className="font-bold mr-2">날짜:</span>{formatDate(train.departureTime)}</p>
                                    <p><span className="font-bold mr-2">출발:</span>{formatTime(train.departureTime)}</p>
                                    <p><span className="font-bold mr-2">도착:</span>{formatTime(train.arrivalTime)}</p>
                                </div>
                                <hr className="my-3 border-t border-[#D5E1F2]" />
                                <div className="text-sm text-gray-700 space-y-2">
                                    <p><span className="font-bold mr-2">열차:</span>{train.trainName}<span className="text-xs text-gray-500 ml-1">({train.trainNumber})</span></p>
                                    <p className="flex items-start">
                                        <span className="font-bold mr-2 shrink-0">좌석:</span>
                                        <span className="text-blue-600 font-semibold break-words">일반실 / {seats.join(", ")}</span>
                                    </p>
                                    <p><span className="font-bold mr-2">승객:</span>성인 {reservation.passengers}명</p>
                                    <p><span className="font-bold mr-2">1인 운임:</span>{train.price?.toLocaleString()}원</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between items-center mt-6">
                        <span className="font-semibold text-gray-800 text-base">총 결제 금액</span>
                        <span className="font-bold text-2xl text-[#3182F6]">{totalPrice.toLocaleString()}원</span>
                    </div>
                    <div className="flex gap-3 mt-10">
                        <button onClick={() => navigate(-1)} className="flex-1 py-4 bg-white border-[2px] border-[#3182F6] text-[#3182F6] rounded-xl font-bold hover:bg-blue-50 transition-colors">다시 선택하기</button>
                        <button onClick={() => setShowPopup(true)} className="flex-1 py-4 bg-[#3182F6] text-white rounded-xl font-bold hover:bg-blue-600 shadow-lg transition-colors">결제하기</button>
                    </div>
                </main>
            </div>
            {showPopup && (
                <>
                    <Dimmed onClick={() => setShowPopup(false)} />
                    <PaymentPopup totalPrice={totalPrice} onSelect={method => {
                        setShowPopup(false);
                        navigate("/payment", { state: {
                            ...reservation,
                            departureStation: legs[0].train.departureStation,
                            arrivalStation: legs[0].train.arrivalStation,
                            paymentMethod: method, totalPrice,
                        } });
                    }} onClose={() => setShowPopup(false)} />
                </>
            )}
        </div>
    );
}
