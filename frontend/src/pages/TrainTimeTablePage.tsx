import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import TrainRow from "../components/TrainCard";
import instance from "../api/axios";

export default function TrainTimeTablePage() {

    const navigate = useNavigate();
    const location = useLocation();

    const {
        departureStation,
        arrivalStation,
        tripType,
        departureDate,
        departureHour,
        returnDate,
        returnHour,
        passengers
    } = location.state || {};

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [trainSchedules, setTrainSchedules] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 🔹 공통 mock 데이터
    const mockTrainData = [
        {
            trainName: "KTX",
            trainNumber: "101",
            departureTime: "2025-12-18T09:00:00",
            arrivalTime: "2025-12-18T11:20:00",
            departureStation,
            arrivalStation,
            price: 39800,
        },
        {
            trainName: "KTX",
            trainNumber: "303",
            departureTime: "2025-12-18T12:30:00",
            arrivalTime: "2025-12-18T14:55:00",
            departureStation,
            arrivalStation,
            price: 42000,
        },
    ];

    const calculateDuration = (dep: string, arr: string) => {
        const start = new Date(dep).getTime();
        const end = new Date(arr).getTime();
        const diff = (end - start) / (1000 * 60);
        const hours = Math.floor(diff / 60);
        const minutes = diff % 60;
        return `${hours}시간 ${minutes}분`;
    };

    useEffect(() => {
        const fetchTrainSchedules = async () => {

            try {
                setLoading(true);
                setError(null);

                // 🔹 필수 값 없으면 mock 데이터로 바로 UI 띄우기
                if (!departureStation || !arrivalStation || !departureDate || departureHour === null) {
                    console.warn("⚠ 필수 값 부족 → mock 데이터 사용");
                    setTrainSchedules(mockTrainData);
                    return;
                }

                // 날짜/시간 포맷 변환
                const depDateObj = new Date(departureDate);
                const year = depDateObj.getFullYear();
                const month = String(depDateObj.getMonth() + 1).padStart(2, "0");
                const day = String(depDateObj.getDate()).padStart(2, "0");
                const formattedDate = `${year}-${month}-${day}`;
                const formattedTime = `${String(departureHour).padStart(2, "0")}:00`;
                const finalDateTime = `${formattedDate} ${formattedTime}`;

                const params = {
                    departure: departureStation,
                    destination: arrivalStation,
                    departureFrom: finalDateTime,
                };

                const response = await instance.get("/train/search", { params });

                // 🔹 서버가 빈 리스트 보내면 mock 사용
                if (!response.data || response.data.length === 0) {
                    console.warn("⚠ 서버 데이터 없음 → mock 데이터 사용");
                    setTrainSchedules(mockTrainData);
                    return;
                }

                // 정상 데이터
                setTrainSchedules(response.data);
            } catch (err) {
                console.error("❌ 기차 시간표 조회 실패:", err);

                // 🔹 오류 발생 → mock 데이터 사용
                setTrainSchedules(mockTrainData);
                setError(null); // 에러 메시지 숨김
            } finally {
                setLoading(false);
            }
        };

        fetchTrainSchedules();
    }, [
        departureStation,
        arrivalStation,
        departureDate,
        departureHour,
        tripType,
        returnDate,
        returnHour,
        passengers,
    ]);

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
                    passengers,
                    departureDate,
                    departureHour,
                    returnDate,
                    returnHour,
                    selectedTrain,
                    trainId: selectedTrain.trainNumber,
                },
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
                                <p className="text-gray-700 mt-2 text-m font-bold">
                                    {departureStation} ➔ {arrivalStation}
                                </p>
                            )}
                        </div>

                        {passengers && (
                            <span className="bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full">
                                {passengers}명
                            </span>
                        )}
                    </div>

                    <div className="mt-2 text-s text-gray-500">
                        {departureDate && (
                            <span>
                                {new Date(departureDate).toLocaleDateString()}{" "}
                                {String(departureHour).padStart(2, "0")}시 이후 열차
                            </span>
                        )}
                    </div>
                </main>

                {loading && (
                    <p className="text-center mt-20 text-gray-500">시간표를 불러오는 중...</p>
                )}

                {!loading && trainSchedules.length > 0 && (
                    <div className="mt-4 px-4 flex-1 overflow-hidden">
                        <div className="bg-white rounded-xl shadow-inner overflow-y-scroll no-scrollbar h-full p-2 pb-20">

                            {trainSchedules.map((train: any) => {
                                const uniqueId = train.trainNumber + train.departureTime + train.arrivalTime;
                                return (
                                    <div key={uniqueId} className="mb-1">  
                                        <TrainRow
                                            id={uniqueId}
                                            trainType={train.trainName}
                                            trainNumber={train.trainNumber}
                                            departTime={new Date(train.departureTime).toLocaleTimeString("ko-KR", {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                                hour12: false,
                                            })}
                                            arriveTime={new Date(train.arrivalTime).toLocaleTimeString("ko-KR", {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                                hour12: false,
                                            })}
                                            duration={calculateDuration(train.departureTime, train.arrivalTime)}
                                            normalPrice={`${train.price?.toLocaleString()}원`}
                                            discountText=""
                                            specialPrice=""
                                            departureStation={train.departureStation}
                                            arrivalStation={train.arrivalStation}
                                            isSelected={selectedId === uniqueId}
                                            onSelect={() => handleSelectTrain(uniqueId)}
                                        />
                                    </div>
                                );
                            })}

                        </div>
                    </div>
                )}

                <div className="w-full px-6 pb-8 pt-4 bg-white z-10">
                    <button
                        disabled={!selectedId || loading}
                        onClick={handleNext}
                        className={`w-full py-4 rounded-xl text-white font-bold text-lg shadow-lg transition-colors ${
                            selectedId && !loading
                                ? "bg-blue-600 hover:bg-blue-700"
                                : "bg-gray-300 cursor-not-allowed"
                        }`}
                    >
                        좌석 선택하기
                    </button>
                </div>
            </div>
        </div>
    );
}
