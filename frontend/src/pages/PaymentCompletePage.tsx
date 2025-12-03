import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import bear from "../components/icons/bear.png";
import checkIcon from "../components/icons/check.png";
import TicketOutputAnimation from "../components/ui/TicketAnimation";

export default function PaymentCompletePage() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [fade, setFade] = useState("in"); // 'in' | 'out'

    // step1 -> step2 전환
    useEffect(() => {
        const t1 = setTimeout(() => setFade("out"), 7000);

        
        const t2 = setTimeout(() => {
            setStep(2);
            setFade("in");
        }, 7500); 
        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
        };
    }, []);

    
    // step2 -> 메인(/) 전환
    useEffect(() => {
        if (step === 2) {
            const fadeTimer = setTimeout(() => {
                setFade("out");
            }, 5500);

            
            const navigateTimer = setTimeout(() => {
                navigate("/");
            }, 6000);

            return () => {
                clearTimeout(fadeTimer);
                clearTimeout(navigateTimer);
            };
        }
    }, [step, navigate]);

    return (
        <div
            className={`
                flex items-center justify-center 
                w-screen h-screen bg-gray-200
                ${fade === "in" ? "animate-fadeIn" : "animate-fadeOut"}
            `}
        >
            <div className="relative w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col items-center px-8 pt-16">

                <div className="flex flex-col items-center text-center mt-4">

                    {/* STEP 1 */}
                    {step === 1 && (
                        <div
                            className={`
                                ${fade === "in" ? "animate-fadeIn" : "animate-fadeOut"} 
                                flex flex-col items-center
                            `}
                        >
                            <h2 className="text-[24px] text-[#434F5D] font-bold mb-5 mt-17">
                                결제가 정상적으로 완료되었습니다
                            </h2>

                            <p className="text-[19px] text-gray-700 leading-relaxed mb-0">
                                신용카드를 제거해 주세요
                            </p>
                            <p className="text-[19px] text-gray-700 leading-relaxed mb-10">
                                기차표는 아래 출력구에서 발행됩니다
                            </p>

                            <TicketOutputAnimation />
                        </div>
                    )}

                    {/* STEP 2 */}
                    {step === 2 && (
                        <div
                            className={`
                                ${fade === "in" ? "animate-fadeIn" : ""} 
                                flex flex-col items-center relative
                            `}
                        >
                            {/* 체크 아이콘 */}
                            <img
                                src={checkIcon}
                                alt="check"
                                className="
                                    absolute top-[-25px] left-1/2 -translate-x-1/2 
                                    w-16 h-16 animate-fadeIn mt-20
                                "
                            />

                            <h2 className="text-[26px] font-bold text-[#434F5D] mb-5 mt-32">
                                승차권 출력이 완료되었습니다
                            </h2>

                            <p className="text-xl text-gray-700 leading-relaxed font-semibold mb-6">
                                이용해 주셔서 감사합니다.
                                <br />즐거운 여행 되세요.
                            </p>
                        </div>
                    )}
                </div>

                
                <div className="flex-1 flex items-end justify-center pb-4">
                    {step === 2 && (
                        <div className="relative w-80 h-auto pb-0">
                            <img
                                src={bear}
                                alt="bear"
                                className="w-95 h-100 mt-11 animate-fadeIn"
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
