import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import bear from "../components/icons/bear.png";
import checkIcon from "../components/icons/check.png";
// import trainticket from "../components/icons/trainticket.png"; // 이 이미지는 이제 자식 컴포넌트에서 쓰므로 여기선 필요 없어요!

// 👇 [수정 1] 새로 만든 애니메이션 컴포넌트 불러오기 (경로는 파일 위치에 맞춰주세요)
import TicketOutputAnimation from "../components/ui/TicketAnimation"; 

export default function PaymentCompletePage() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [fade, setFade] = useState("in"); // 'in' | 'out'

    useEffect(() => {
        // 10초 후 → fade-out 시작
        const t1 = setTimeout(() => setFade("out"), 10000);

        // fade-out 끝나는 시점(0.5s 후) → step2 + fade-in
        const t2 = setTimeout(() => {
            setStep(2);
            setFade("in");
        }, 10500);

        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
        };
    }, []);

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-gray-200">
            <div className="relative w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col items-center px-8 pt-16">

                <div className="flex flex-col items-center text-center mt-4">

                    {/* STEP 1 */}
                    {step === 1 && (
                        <div
                            className={`${fade === "in" ? "animate-fadeIn" : "animate-fadeOut"} 
                                    flex flex-col items-center`}
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

                            {/* 👇 [수정 2] 기존의 div와 img 태그를 지우고 아래 컴포넌트 한 줄로 교체! */}
                            <TicketOutputAnimation />
                            
                        </div>
                    )}

                    {/* STEP 2 */}
                    {step === 2 && (
                        <div
                            className={`${fade === "in" ? "animate-fadeIn" : ""} 
                                    flex flex-col items-center`}
                        >
                        <span>
                          <img
                                src={checkIcon}
                                alt="check"
                                className="absolute top-[-25px] left-1/2 -translate-x-1/2 
                                           w-16 h-16 animate-fadeIn mt-22"
                            />

                        </span>
                            <h2 className="text-[26px] font-bold text-[#434F5D] mb-5 mt-30">
                                승차권 출력이 완료되었습니다
                            </h2>

                            <p className="text-xl text-gray-700 leading-relaxed font-semibold  mb-6">
                                이용해 주셔서 감사합니다.
                                <br />즐거운 여행 되세요.
                            </p>
                        </div>
                    )}
                </div>

                {/* 곰돌이 */}
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