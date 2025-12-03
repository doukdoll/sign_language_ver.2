import { useMemo, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom"; // 1. useLocation 추가
import { useSeatStatus } from "../hooks/useSeatStatus";
import SeatGrid from "../components/seats/SeatGrid";
import Header from "../components/Header";

export default function KTXSeatSelector() {
    const navigate = useNavigate();
    const location = useLocation(); // 2. location 훅 사용

    // 3. 이전 페이지에서 보낸 모든 데이터 받기 (구조 분해 할당)
    const {
        departureStation,
        arrivalStation,
        tripType,
        departureDate,
        departureHour,
        returnDate,
        returnHour,
        passengers,      // 가장 중요: 탑승 인원 수
        selectedTrain1,    // 가장 중요: 기차 정보
        selectedTrain2,
        seats1
    } = location.state || {};

    // 초기 좌석 상태 고정 (기존 코드 유지)
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

    // 4. useSeatStatus에 '최대 선택 가능 인원(passengers)'을 전달할 수 있다면 좋습니다.
    // (만약 커스텀 훅이 기능을 지원하지 않는다면 아래 handleConfirm에서 검사해야 합니다.)
    const { seats, toggleSeat, selectedSeats } = useSeatStatus(initialSeats);

    // 데이터 잘 들어왔는지 확인용 로그
    useEffect(() => {
        console.log("📝 SeatPage 수신 데이터:", { passengers, selectedTrain1 });
        if (!passengers) {
            console.warn("⚠️ 인원수 정보가 없습니다. (테스트가 아니라면 오류 상황)");
        }
    }, [passengers, selectedTrain1]);


    // 좌석 선택 완료 핸들러
    const handleConfirm = () => {
        console.log("[버튼 클릭] 선택된 좌석:", selectedSeats);

        // 5. [유효성 검사] 탑승 인원수와 선택한 좌석 수가 일치하는지 확인
        if (passengers && selectedSeats.length !== passengers) {
            alert(`탑승 인원은 ${passengers}명입니다. 좌석 ${passengers}개를 선택해주세요.`);
            return;
        }

        if (selectedSeats.length > 0) {
            // 6. [데이터 전달] 기존 정보 + 좌석 정보를 모두 담아서 다음 페이지로 이동
            if (tripType=='round'){
                navigate("/timetable", {
                    state: {
                        // 기존 여행 정보 유지
                        departureStation:arrivalStation,
                        arrivalStation:departureStation,
                        tripType:'round2',
                        departureDate:returnDate,
                        departureHour:returnHour,
                        returnDate,
                        returnHour,
                        passengers,
                        selectedTrain1,

                        // 새로 선택한 좌석 정보
                        seats1: selectedSeats
                    }
                });
            }

            else if (tripType=='round2'){  //왕복 2번째
                console.log("첫 번째 열차:", selectedTrain1)
                console.log("두 번째 열차:", selectedTrain2);
                navigate("/summary", {
                    state: {
                        // 기존 여행 정보 유지
                        departureStation,
                        arrivalStation,
                        tripType,
                        departureDate,
                        departureHour,
                        returnDate,
                        returnHour,
                        passengers,
                        selectedTrain1,
                        selectedTrain2,
                        seats1,

                        // 새로 선택한 좌석 정보
                        seats2: selectedSeats,

                        // (선택 사항) 총 결제 금액 계산해서 넘기기
                        totalPrice: ((selectedTrain1?.price + selectedTrain2?.price) || 0) * passengers
                    }
                });
            }

            else{
                navigate("/summary", { //편도
                state: {
                    // 기존 여행 정보 유지
                    departureStation,
                    arrivalStation,
                    tripType,
                    departureDate,
                    departureHour,
                    returnDate,
                    returnHour,
                    passengers,
                    selectedTrain1,

                    // 새로 선택한 좌석 정보
                    seats1: selectedSeats,

                    // (선택 사항) 총 결제 금액 계산해서 넘기기
                    totalPrice: (selectedTrain1?.price || 0) * passengers
                }
            });
          }
        }
    };

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

                {/* 상단 헤더 */}
                <Header title="좌석 선택" />

                {/* 전체 컨텐츠 */}
                <div className="flex flex-col flex-1 bg-gray-100">

                    {/* (선택 사항) 상단에 현재 상태 표시 */}
                    <div className="bg-white p-4 pb-2 border-b">
                        <p className="text-gray-700 font-bold">
                            {departureStation} ➔ {arrivalStation}
                        </p>
                        <p className="text-sm text-blue-600 font-bold mt-1">
                            {passengers ? `${passengers}명 탑승` : "인원 정보 없음"}
                        </p>
                    </div>

                    {/* 좌석 그리드 */}
                    <div className="flex-1 overflow-y-auto bg-white p-6">
                        {/* 주의: useSeatStatus 훅 내부에서 'passengers' 수만큼만
               선택되도록 제한하는 로직이 없다면, 여기서 UI적으로 막거나
               handleConfirm에서 경고를 띄워야 합니다.
            */}
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
                            onClick={handleConfirm}
                            // 7. 인원수와 선택 좌석 수가 다르면 버튼 스타일 변경 (선택 사항)
                            className={`w-full py-5 rounded-lg text-xl font-bold transition-transform active:scale-98
                ${selectedSeats.length > 0
                                ? "bg-blue-600 text-white"
                                : "bg-gray-500 text-gray-300 cursor-not-allowed"}
              `}
                            disabled={selectedSeats.length === 0}
                        >
                            {passengers
                                ? `${selectedSeats.length}/${passengers}석 선택 완료` // 인원수 표시
                                : "선택 완료"}
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
}