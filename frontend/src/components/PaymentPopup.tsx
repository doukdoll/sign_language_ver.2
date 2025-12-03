// src/components/PaymentPopup.tsx
import cardIcon from "../components/icons/card.png";
import nfcIcon from "../components/icons/naverpay.png";

interface PaymentPopupProps {
  totalPrice: number;
  onSelect: (method: string) => void;
  onClose: () => void;
}

export default function PaymentPopup({ totalPrice, onSelect, onClose }: PaymentPopupProps) {
  return (
    <div className="fixed inset-0 z-50 flex justify-center items-center pointer-events-none">

      {/* 팝업 카드 */}
      <div
        className="pointer-events-auto w-[330px] bg-white rounded-2xl shadow-2xl p-6 
                   border border-gray-200 relative z-50 animate-slideDown -mt-100"
      >
      
        <h2 className="text-center text-lg font-bold text-gray-800">
          결제방법을 선택해주세요
        </h2>

        
        <div className="flex justify-center gap-8 mt-6">

          {/* 신용카드 */}
          <button onClick={() => onSelect("card")} className="text-center">
            <div className="w-28 h-35 bg-gray-100 rounded-xl  flex items-center justify-center">
              <img src={cardIcon} className="w-20" />
            </div>
            <p className="mt-2 text-sm text-gray-700 font-semibold">신용카드</p>
          </button>

          {/* 간편결제 */}
          <button onClick={() => onSelect("pay")} className="text-center">
            <div className="w-28 h-35 bg-gray-100 rounded-xl  flex items-center justify-center">
              <img src={nfcIcon} className="w-16" />
            </div>
            <p className="mt-2 text-sm text-gray-700 font-semibold">간편결제</p>
          </button>
        </div>

        {/* 금액 */}
        <div className="mt-6 bg-[#1F3A67] rounded-full py-3 text-center">
          <span className="text-white text-m text-bold mr-2">총 결제금액</span>
          <span className="text-[#3BA9FF] text-lg font-bold">
            {totalPrice.toLocaleString()}원
          </span>
        </div>

        {/* 결제취소 버튼 */}
        <button
          onClick={onClose}
          className="mt-5 w-full py-3 bg-gray-500 rounded-lg text-sm font-semibold text-white border"
        >
          결제취소
        </button>
      </div>

      {/* 애니메이션 */}
      <style>
        {`
          @keyframes slideDown {
            from {
              opacity: 0;
              transform: translateY(-20px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
          .animate-slideDown {
            animation: slideDown 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
          }
        `}
      </style>
    </div>
  );
}
