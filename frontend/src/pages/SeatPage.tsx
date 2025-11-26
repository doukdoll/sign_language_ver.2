import { useMemo } from "react";
import { useNavigate } from "react-router-dom"; // 추가
import { useSeatStatus } from "../hooks/useSeatStatus";
import SeatGrid from "../components/seats/SeatGrid";
import Header from "../components/Header";

export default function KTXSeatSelector() {
  const navigate = useNavigate(); // 추가

  // 초기 좌석 상태 고정
  const initialSeats = useMemo(() => {
    const seats: any = {};
    for (let row = 1; row <= 7; row++) {
      for (let col of ["A", "B", "C", "D"]) {
        const seat = `${row}${col}`;
        seats[seat] = Math.random() > 0.75 ? "occupied" : "available";
      }
    }
    return seats;
  }, []);

  const { seats, toggleSeat, selectedSeats } = useSeatStatus(initialSeats);

  // 좌석 선택 완료 핸들러 추가
  const handleConfirm = () => {
    if (selectedSeats.length > 0) {
      // 선택된 좌석 정보를 state로 전달하면서 이동
      navigate("/summary", { 
        state: { 
          selectedSeats,
          // 필요한 다른 정보도 함께 전달 가능
          // trainInfo: { ... }
          // 나중에 추가
        } 
      });
    }
  };

  return (
    <div className="flex justify-center w-screen h-screen bg-white">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

        {/* 상단 헤더 */}
        <Header title="좌석 선택" />

        {/* 전체 컨텐츠 */}
        <div className="flex flex-col flex-1 bg-gray-100">

          

          {/* 좌석 그리드 */}
          <div className="flex-1 overflow-y-auto bg-white p-6">
            <SeatGrid seats={seats} onSelect={toggleSeat} />
          </div>

          {/* 하단 선택 좌석 정보 */}
          <div className="bg-gray-700 text-white p-6">
            <div className="text-center mb-2 text-lg font-bold">선택 좌석</div>

            <div className="bg-gray-800 rounded-lg p-4 mb-4 min-h-16 flex items-center justify-center">
              {selectedSeats.length > 0 ? (
                <div className="text-2xl font-bold">
                  {selectedSeats.join(" / ")}
                </div>
              ) : (
                <div className="text-gray-400 text-lg">좌석을 선택해주세요</div>
              )}
            </div>

            <button
              onClick={handleConfirm} // 추가
              className="w-full bg-blue-600 text-white py-5 rounded-lg text-xl font-bold disabled:bg-gray-500 disabled:cursor-not-allowed active:scale-98 transition-transform" // active 효과 추가
              disabled={selectedSeats.length === 0}
            >
              {selectedSeats.length > 0
                ? `${selectedSeats.length}석 선택 완료`
                : "좌석 선택"}
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}