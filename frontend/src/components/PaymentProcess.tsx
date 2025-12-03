import { useEffect } from "react";
import qrIcon from "../components/icons/qr-code.png";
import cardIcon from "../components/icons/creditcard.png";

interface PaymentProcessProps {
  type: "card" | "pay"; 
  totalPrice: number;
  onClose: () => void;
}

export default function PaymentProcess({
  type,
  totalPrice,
  onClose,
}: PaymentProcessProps) {

  useEffect(() => {
    console.log(`결제 진행 화면 열림. 선택된 결제 수단: ${type}`);
    return () => {
      console.log("결제 진행 화면 닫힘.");
    };
  }, [type]);

  return (
    <div className="w-screen h-screen flex justify-center items-center bg-gradient-to-b from-blue-50 to-white pb-27">

      {/* 메인 컨테이너 */}
      <div className="w-[400px] h-[780px] py-10 px-6 flex flex-col items-center text-center relative bg-white shadow-2xl rounded-2xl overflow-hidden pt-6 pb-5">

        {/* 콘텐츠 영역 */}
        <div className="flex-1 w-full flex flex-col items-center pt-8">

          {/* ------------------------------ */}
          {/* 1. 신용카드 결제 화면 */}
          {/* ------------------------------ */}
          {type === "card" && (
            <>
              <h2 className="text-[28px] font-bold text-[#222222] leading-tight mb-6">
                신용카드를<br />투입구에 넣어주세요
              </h2>

              <p className="text-[18px] text-[#666666] mb-12 leading-relaxed font-medium">
                IC칩이 위로 향하게 넣으시면 됩니다.<br />
                <span className="text-[#FF6B00] font-bold">
                  결제 실패 시 마그네틱을<br />오른쪽 방향으로 긁어주세요
                </span>
              </p>

              {/* 카드 애니메이션 */}
              <div className="relative w-full h-52 flex justify-center items-center mb-10">

                {/* 투입구 슬롯 */}
                <div className="absolute top-2 w-56 h-3 bg-[#333333] z-20 shadow-inner"></div>

                {/* 카드 이미지 */}
                <div className="absolute top-0 animate-insertCard z-10">
                  <img
                    src={cardIcon}
                    alt="credit-card"
                    className="w-45 h-auto object-contain drop-shadow-xl"
                  />
                </div>
              </div>
            </>
          )}

          {/* ------------------------------ */}
          {/* 2. 네이버페이 QR 결제 화면 */}
          {/* ------------------------------ */}
          {type === "pay" && (
            <>
              <h2 className="text-[28px] font-bold text-[#222222] leading-tight mb-6">
                네이버페이 결제<br />QR 코드를 찍어주세요
              </h2>

              <p className="text-[18px] text-[#666666] mb-12 leading-relaxed font-medium">
                네이버페이 앱을 실행한 뒤,<br />
                <span className="text-[#03C75A] font-bold inline-flex items-center">
                  QR 결제
                </span> 버튼을 눌러 스캔해주세요.
              </p>

              <div className="flex flex-col items-center mb-12">
                {/* QR 코드 박스 */}
                <div className="w-55 h-55 bg-white border-[5px] border-[#03C75A] rounded-3xl flex items-center justify-center shadow-[0_10px_25px_-5px_rgba(3,199,90,0.3)] p-4 relative overflow-hidden">

                  <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#03C75A]/20 to-transparent animate-scan"></div>

                  <img src={qrIcon} alt="QR code" className="w-full h-full object-contain opacity-95 relative z-10" />
                </div>

                <p className="text-sm text-[#888888] mt-5 font-medium flex items-center">
                  결제가 자동으로 확인됩니다. 잠시만 기다려주세요.
                </p>
              </div>
            </>
          )}

        </div>

        {/* ------------------------------ */}
        {/* 하단 고정 영역 (결제 금액 + 버튼) */}
        {/* ------------------------------ */}
        <div className="w-full mt-4 pt-6 border-t border-gray-100">

          {/* 결제 금액 */}
          <div className="w-full bg-[#F8F9FA] rounded-2xl py-5 px-8 flex justify-between items-center mb-6 shadow-sm">
            <span className="text-[#444444] font-bold text-lg">총 결제금액</span>
            <span className="text-[#0052A4] text-[26px] font-extrabold tracking-tight">
              {totalPrice.toLocaleString()}원
            </span>
          </div>

          {/* 결제 취소 버튼 */}
          <div className="w-full flex flex-col gap-3">
            <button
              onClick={onClose}
              className="w-full py-4 bg-[#E0E0E0] hover:bg-[#D0D0D0] rounded-xl text-[#555555] font-bold text-[18px] transition-all duration-200 transform hover:scale-[0.99] active:scale-[0.97]"
            >
              결제 취소
            </button>
          </div>
        </div>

      </div>

      {/* 애니메이션 정의 */}
      <style>{`
        @keyframes insertCard {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-25px); }
        }
        .animate-insertCard {
          animation: insertCard 2.5s ease-in-out infinite;
        }

        @keyframes scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
        .animate-scan {
          animation: scan 2s linear infinite;
        }
      `}</style>

    </div>
  );
}
