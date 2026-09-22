import { useMemo } from "react";
import { Navigate, useNavigate, useLocation } from "react-router-dom";
import { useSeatStatus } from "../hooks/useSeatStatus";
import SeatGrid from "../components/seats/SeatGrid";
import Header from "../components/Header";
import type { SeatStatus } from "../styles/seatStyles";
import { hasScheduleSelection, readReservationState, selectSeats } from "../utils/reservation";

export default function KTXSeatSelector() {
    const navigate = useNavigate();
    const location = useLocation();
    const reservation = readReservationState(location.state);

    // 좌석 재고 API가 없는 데모 화면입니다. 실제 예약 가능 여부를 나타내지 않습니다.
    const initialSeats = useMemo(() => {
        const seats: Record<string, SeatStatus> = {};
        for (let row = 1; row <= 7; row++) {
            for (const col of ["A", "B", "C", "D"]) {
                seats[`${row}${col}`] = Math.random() > 0.75 ? "occupied" : "available";
            }
        }
        return seats;
    }, []);
    const { seats, toggleSeat, selectedSeats } = useSeatStatus(initialSeats);
    if (!hasScheduleSelection(reservation) || !reservation.selectedTrain1 ||
        (reservation.tripType === 'round2' && !reservation.selectedTrain2)) return <Navigate to="/" replace />;

    const { departureStation, arrivalStation, passengers } = reservation;
    const handleConfirm = () => {
        try {
            const next = selectSeats(reservation, selectedSeats);
            navigate(next.path, { state: next.state });
        } catch (error) {
            alert(error instanceof Error ? error.message : "좌석 정보를 다시 확인해주세요.");
        }
    };

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">
                <Header title="좌석 선택" />
                <div className="flex flex-col flex-1 bg-gray-100">
                    <div className="bg-white p-4 pb-2 border-b">
                        <p className="text-gray-700 font-bold">{departureStation} ➔ {arrivalStation}</p>
                        <p className="text-sm text-blue-600 font-bold mt-1">{passengers}명 탑승</p>
                        <p className="text-xs text-gray-500 mt-1">데모 좌석 배치이며 실제 예약은 진행되지 않습니다.</p>
                    </div>
                    <div className="flex-1 overflow-y-auto bg-white p-6"><SeatGrid seats={seats} onSelect={toggleSeat} /></div>
                    <div className="bg-gray-700 text-white p-6">
                        <div className="text-center mb-2 text-lg font-bold">선택 좌석</div>
                        <div className="bg-gray-800 rounded-lg p-4 mb-4 min-h-16 flex items-center justify-center">
                            {selectedSeats.length > 0
                                ? <div className="text-2xl font-bold">{selectedSeats.join(" / ")}</div>
                                : <div className="text-gray-400 text-lg">좌석을 선택해주세요</div>}
                        </div>
                        <button onClick={handleConfirm} disabled={selectedSeats.length !== passengers}
                            className={`w-full py-5 rounded-lg text-xl font-bold transition-transform active:scale-98 ${selectedSeats.length === passengers ? "bg-blue-600 text-white" : "bg-gray-500 text-gray-300 cursor-not-allowed"}`}>
                            {selectedSeats.length}/{passengers}석 선택 완료
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
