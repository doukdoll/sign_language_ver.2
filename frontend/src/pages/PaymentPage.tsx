import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import PaymentProcess from "../components/PaymentProcess";

export default function PaymentPage() {
    const navigate = useNavigate();
    const location = useLocation();

    const {
        paymentMethod,
        totalPrice,
        departureStation,
        arrivalStation,
        passengers,
        ...otherInfo
    } = location.state || {};

   
    const [fade, setFade] = useState("opacity-0");

    // 페이지 로드 시 페이드 인
    useEffect(() => {
        setTimeout(() => setFade("opacity-100"), 10);
    }, []);

    // 잘못된 접근 방지
    useEffect(() => {
        if (!paymentMethod || !totalPrice) {
            alert("잘못된 접근입니다. 메인으로 이동합니다.");
            navigate("/");
        }
    }, [paymentMethod, totalPrice, navigate]);

    
    const fadeOutAndNavigate = (callback: Function) => {
        setFade("opacity-0");
        setTimeout(() => callback(), 300); // 300ms 후 이동
    };

    // 결제 완료 → 완료 페이지 이동
    const handleComplete = () => {
        fadeOutAndNavigate(() => {
            navigate("/paymentcomplete", {
                state: {
                    ...otherInfo,
                    departureStation,
                    arrivalStation,
                    passengers,
                    totalPrice,
                    paymentMethod,
                    paymentDate: new Date().toISOString(),
                }
            });
        });
    };

    // 6초 후 자동 이동 타이머
    useEffect(() => {
        if (!paymentMethod) return;

        const timer = setTimeout(() => {
            console.log("6초 경과 → 결제 완료 페이지로 이동");
            handleComplete();
        }, 6000);

        return () => clearTimeout(timer);
    }, [paymentMethod]);

    // 결제 취소 → 뒤로가기
    const handleClose = () => {
        fadeOutAndNavigate(() => navigate(-1));
    };

    if (!paymentMethod) return null;

    return (
        <div
            className={`flex justify-center w-screen h-screen bg-white transition-opacity duration-300 ${fade}`}
        >
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col relative overflow-hidden">

                <Header title="결제 진행" />

                <main className="flex-1 flex flex-col items-center mt-4 px-4">
                    <PaymentProcess
                        type={paymentMethod}
                        totalPrice={totalPrice}
                        onClose={handleClose}
                    />
                </main>

                <div className="w-[85%] bg-white border border-gray-200 px-4 py-4 mb-6 shadow-sm mx-auto rounded-lg">

                    <div className="flex justify-between items-center mb-2 border-b border-gray-100 pb-2">
                        <span className="font-semibold text-gray-900">결제 수단</span>
                        <span className="text-sm font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                            {paymentMethod === "card" ? "신용카드" : "네이버페이"}
                        </span>
                    </div>

                    <p className="text-sm text-gray-700 flex justify-between mt-1">
                        <span className="font-semibold text-gray-900">출발역</span>
                        <span>{departureStation || "-"}</span>
                    </p>

                    <p className="text-sm text-gray-700 flex justify-between mt-1">
                        <span className="font-semibold text-gray-900">도착역</span>
                        <span>{arrivalStation || "-"}</span>
                    </p>

                    <p className="text-sm text-gray-700 flex justify-between mt-1">
                        <span className="font-semibold text-gray-900">탑승 인원</span>
                        <span>{passengers ? `${passengers}명` : "-"}</span>
                    </p>

                    <div className="flex justify-between items-center mt-3 pt-2 border-t border-dashed border-gray-300">
                        <span className="font-bold text-gray-900">총 결제금액</span>
                        <span className="font-extrabold text-lg text-[#FF5F00]">
                            {totalPrice?.toLocaleString()}원
                        </span>
                    </div>
                </div>

            </div>
        </div>
    );
}
