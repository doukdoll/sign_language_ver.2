import Header from "../components/Header";
import { useNavigate, useLocation } from "react-router-dom";

export default function PaymentPage() {
  const navigate = useNavigate();
  const { state } = useLocation(); 
  // seat, date, train info 같은 이전 페이지 state 그대로 존재

  // 결제 수단 선택 시 이동
  const handlePaymentSelect = (method: string) => {
    navigate("/payment-process", {
      state: {
        ...state,           // 기존 예매 정보 그대로 넘김
        paymentMethod: method, // 선택한 결제 방식 추가
      },
    });
  };

  return (
    <div className="flex justify-center w-screen h-screen bg-white">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

        {/* 헤더 */}
        <Header title="결제하기" />

        {/* 안내문 */}
        <div className="px-6 mt-8">
          <h2 className="text-xl font-semibold text-gray-800">
            결제 수단을 선택해주세요.
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            고객님의 정보를 안전하게 보호합니다.
          </p>
        </div>

        {/* 결제 수단 목록 */}
        <div className="flex flex-col gap-4 px-6 mt-6">

          {/* 카드 결제 */}
          <button
            onClick={() => handlePaymentSelect("card")}
            className="w-full h-24 bg-white rounded-xl shadow-md border border-gray-200 flex items-center px-4 gap-4 active:scale-95 duration-100"
          >
            <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center text-blue-600 text-3xl font-bold">
              💳
            </div>
            <div className="flex flex-col text-left">
              <span className="text-lg font-semibold text-gray-800">카드 결제</span>
              <span className="text-sm text-gray-500">신용/체크카드 사용 가능</span>
            </div>
          </button>

          {/* 간편결제 */}
          <button
            onClick={() => handlePaymentSelect("easy")}
            className="w-full h-24 bg-white rounded-xl shadow-md border border-gray-200 flex items-center px-4 gap-4 active:scale-95 duration-100"
          >
            <div className="w-14 h-14 bg-yellow-100 rounded-xl flex items-center justify-center text-yellow-600 text-3xl font-bold">
              📱
            </div>
            <div className="flex flex-col text-left">
              <span className="text-lg font-semibold text-gray-800">간편결제</span>
              <span className="text-sm text-gray-500">카카오페이 · 네이버페이 · 페이코</span>
            </div>
          </button>

          {/* 현금 결제 */}
          <button
            onClick={() => handlePaymentSelect("cash")}
            className="w-full h-24 bg-white rounded-xl shadow-md border border-gray-200 flex items-center px-4 gap-4 active:scale-95 duration-100"
          >
            <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center text-green-600 text-3xl font-bold">
              💵
            </div>
            <div className="flex flex-col text-left">
              <span className="text-lg font-semibold text-gray-800">현금 결제</span>
              <span className="text-sm text-gray-500">현금 투입구 이용</span>
            </div>
          </button>

        </div>

        {/* 하단 결제 요약 */}
        <div className="mt-auto w-full h-24 bg-white border-t shadow-inner flex items-center justify-between px-6">
          <div className="text-gray-600 text-base">총 결제 금액</div>
          <div className="text-xl font-bold text-gray-900">{state?.totalPrice ?? "107,000원"}</div>
        </div>

      </div>
    </div>
  );
}
