import Header from "../components/Header";
import { useLocation } from "react-router-dom";

export default function ReservationSummaryPage() {
  const { state } = useLocation(); 
  console.log("넘어온 state:", state);

  const dummyReservation = {
    departure: "부산",
    arrival: "서울",
    date: "2025.11.22 (금)",
    departTime: "08:30",
    arriveTime: "10:58",
    trainType: "KTX",
    trainNumber: "103",
    seatClass: "일반석",
    seats: ["6A", "6B"],   
    passengers: 2,
    totalPrice: "107,000원",
  };

  // state에 seats 상태가 넘어오면 사용
  const finalSeats = state?.seats ?? dummyReservation.seats;

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

          <div className="bg-white rounded-xl shadow p-6">
            <h3 className="text-lg font-semibold mb-3">
              출발: {dummyReservation.departure} → {dummyReservation.arrival}
            </h3>

            <div className="text-sm text-gray-700 space-y-1 mb-4">
              <p>날짜: {dummyReservation.date}</p>
              <p>출발 시각: {dummyReservation.departTime}</p>
              <p>도착 시각: {dummyReservation.arriveTime}</p>
            </div>

            <hr className="my-3 border-t border-[#D5E1F2]" />

            <div className="text-sm text-gray-700 space-y-1">
              <p>
                열차: {dummyReservation.trainType} ({dummyReservation.trainNumber})
              </p>

              <p>
                좌석: {dummyReservation.seatClass} / {finalSeats.join(", ")}
              </p>

              <p>승객: 성인 {dummyReservation.passengers}명</p>
            </div>

            <hr className="my-3 border-t border-[#D5E1F2]" />

            <div className="flex justify-between items-center">
              <span className="font-semibold text-gray-800 text-base">
                총 결제 금액
              </span>
              <span className="font-bold text-xl text-gray-900">
                {dummyReservation.totalPrice}
              </span>
            </div>
          </div>

          <div className="flex gap-3 mt-10">
            <button className="flex-1 py-3 bg-white border-[2px] border-[#3182F6] text-[#3182F6] rounded-xl font-semibold">
              다시 선택하기
            </button>
            <button className="flex-1 py-3 bg-[#3182F6] text-white rounded-xl font-semibold">
              결제하기
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}
