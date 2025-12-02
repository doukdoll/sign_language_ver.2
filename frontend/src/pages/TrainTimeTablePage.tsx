import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import TrainRow from "../components/TrainCard";
import instance from "../api/axios";

export default function TrainTimeTablePage() {

    const navigate = useNavigate();
    const location = useLocation();

    // 1. [수정] passengers(탑승 인원) 추가
    const {
        departureStation,
        arrivalStation,
        tripType,
        departureDate,
        departureHour,
        returnDate,
        returnHour,
        passengers // 여기서 받아와야 합니다.
    } = location.state || {};

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [trainSchedules, setTrainSchedules] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 소요 시간 계산 헬퍼 함수
    const calculateDuration = (dep: string, arr: string) => {
        const start = new Date(dep).getTime();
        const end = new Date(arr).getTime();
        const diff = (end - start) / (1000 * 60); // 분 단위
        const hours = Math.floor(diff / 60);
        const minutes = diff % 60;
        return `${hours}시간 ${minutes}분`;
    };

    useEffect(() => {
        console.log("📝 TrainTimeTablePage state:", {
            departureStation,
            arrivalStation,
            departureDate,
            passengers, // 로그 확인
        });

        const fetchTrainSchedules = async () => {
            // 필수 정보 체크
            if (!departureStation || !arrivalStation || !departureDate || departureHour === null) {
                // 개발 중 테스트를 위해 임시로 넘어가게 할 수도 있지만, 원칙적으로는 에러 처리
                // setError("필수 열차 정보가 누락되었습니다.");
                // setLoading(false);
                // return;

                // (테스트용) 데이터가 없어도 로딩은 풀어줌
                console.warn("필수 정보 누락됨 (테스트 모드라면 무시)");
            }

            try {
                setLoading(true);
                setError(null);

                // Date 객체인지 확인 후 변환 (state로 넘어오면서 문자열이 될 수도 있음)
                const depDateObj = new Date(departureDate);
                const year = depDateObj.getFullYear();
                const month = String(depDateObj.getMonth() + 1).padStart(2, '0');
                const day = String(depDateObj.getDate()).padStart(2, '0');

                const formattedDate = `${year}-${month}-${day}`;
                const formattedTime = `${String(departureHour).padStart(2, '0')}:00`;
                const finalDateTime = `${formattedDate} ${formattedTime}`;

                const params: any = {
                    departure: departureStation,
                    destination: arrivalStation,
                    departureFrom: finalDateTime,
                };

                const response = await instance.get("/train/search", { params });
                setTrainSchedules(response.data);
            } catch (err) {
                console.error("기차 시간표 조회 실패:", err);
                setError("기차 시간표를 불러오는 데 실패했습니다.");
            } finally {
                setLoading(false);
            }
        };

        fetchTrainSchedules();
    }, [departureStation, arrivalStation, departureDate, departureHour, tripType, returnDate, returnHour, passengers]);

    const handleSelectTrain = (id: string) => {
        console.log(id);
        setSelectedId(id);
    };

    const handleNext = () => {
        // 2. [수정] 다음 페이지로 모든 데이터 전달
        // 선택된 기차 객체를 찾음
        const selectedTrain = trainSchedules.find(t => (t.trainNumber + t.departureTime + t.arrivalTime) === selectedId);
        console.log(selectedId);
        console.log(selectedTrain)
        if (selectedTrain) {
            navigate("/seat", {
                state: {
                    // 기존 정보 유지
                    departureStation:selectedTrain.departureStation,
                    arrivalStation: selectedTrain.arrivalStation,
                    tripType,
                    passengers, // 인원수 전달 필수!
                    departureDate,
                    departureHour,
                    returnDate,
                    returnHour,

                    // 선택한 기차 정보 추가
                    selectedTrain: selectedTrain, // 기차 번호, 시간, 가격 등 전체 정보 전달
                    trainId: selectedTrain.trainNumber // 식별자
                }
            });
        }
    };

    return (
        <div className="flex justify-center w-screen h-screen bg-white">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

                <Header title="기차 시간표 조회" />

                <main className="mt-6 px-6">
                    <div className="flex justify-between items-end">
                        <div>
                            <p className="text-xl font-bold">원하는 열차 시간을 선택해주세요.</p>
                            {departureStation && arrivalStation && (
                                <p className="text-gray-700 mt-2 text-sm">
                                    {departureStation} ➔ {arrivalStation}
                                </p>
                            )}
                        </div>
                        {/* 인원수 표시 추가 */}
                        {passengers && (
                            <span className="bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full">
                     {passengers}명
                 </span>
                        )}
                    </div>

                    <div className="mt-2 text-sm text-gray-500">
                        {departureDate && (
                            <span>{new Date(departureDate).toLocaleDateString()} {String(departureHour).padStart(2, '0')}시 출발</span>
                        )}
                    </div>
                </main>

                {loading && <p className="text-center mt-20 text-gray-500">시간표를 불러오는 중...</p>}
                {error && <p className="text-center mt-20 text-red-500">{error}</p>}

                {!loading && !error && trainSchedules.length === 0 && (
                    <p className="text-center mt-20 text-gray-500">조회된 열차 시간표가 없습니다.</p>
                )}

                {!loading && !error && trainSchedules.length > 0 && (
                    <div className="mt-4 px-4 flex-1 overflow-hidden">
                        <div className="bg-white rounded-xl shadow-inner overflow-y-scroll no-scrollbar h-full p-2 pb-20">
                            {trainSchedules.map((train: any) => {
                                const uniqueId = train.trainNumber + train.departureTime + train.arrivalTime;
                                return (
                                    <TrainRow
                                        key={uniqueId}
                                        trainType={train.trainName}
                                        trainNumber={train.trainNumber}
                                        departTime={new Date(train.departureTime).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                        arriveTime={new Date(train.arrivalTime).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                        duration={calculateDuration(train.departureTime, train.arrivalTime)} // 소요시간 계산 적용
                                        normalPrice={`${train.price?.toLocaleString()}원`}
                                        discountText=""
                                        specialPrice=""
                                        departureStation={train.departureStation}
                                        arrivalStation={train.arrivalStation}
                                        isSelected={selectedId === uniqueId}
                                        onSelect={() => handleSelectTrain(uniqueId)}
                                    />
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* 예매 페이지 이동 버튼 */}
                <div className="w-full px-6 pb-8 pt-4 bg-white z-10">
                    <button
                        disabled={!selectedId || loading || !!error}
                        onClick={handleNext}
                        className={`w-full py-4 rounded-xl text-white font-bold text-lg shadow-lg transition-colors
                ${selectedId && !loading && !error
                            ? "bg-blue-600 hover:bg-blue-700"
                            : "bg-gray-300 cursor-not-allowed"}
            `}
                    >
                        좌석 선택하기
                    </button>
                </div>
            </div>
        </div>
    );
}