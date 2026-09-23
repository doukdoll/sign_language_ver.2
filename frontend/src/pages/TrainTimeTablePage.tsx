import { useState, useEffect } from "react";
import { Navigate, useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import TrainRow from "../components/TrainCard";
import instance from "../api/axios";
import { formatSearchDate, hasScheduleSelection, readReservationState, selectTrain } from "../utils/reservation";
import { startScheduleSearch } from "../utils/trainSchedules";
import type { ScheduleSearchState } from "../utils/trainSchedules";

export default function TrainTimeTablePage() {
    const navigate = useNavigate();
    const location = useLocation();
    const reservation = readReservationState(location.state);
    const valid = hasScheduleSelection(reservation);
    const departureStation = reservation?.departureStation;
    const arrivalStation = reservation?.arrivalStation;
    const departureFrom = valid ? formatSearchDate(reservation.departureDate, reservation.departureHour) : null;
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [attempt, setAttempt] = useState(0);
    const [search, setSearch] = useState<ScheduleSearchState>({ loading: true, trains: [], error: null });

    useEffect(() => {
        setSelectedId(null);
        if (!valid || !departureStation || !arrivalStation || !departureFrom) return;
        const request = startScheduleSearch(
            async (params, signal) => (await instance.get<unknown>("/train/search", { params, signal })).data,
            { departure: departureStation, destination: arrivalStation, departureFrom },
            setSearch,
        );
        return request.cancel;
    }, [valid, departureStation, arrivalStation, departureFrom, attempt]);

    if (!valid) return <Navigate to="/" replace />;

    const { loading, trains, error } = search;
    const selectedTrain = trains.find(train => `${train.trainNumber}/${train.departureTime}/${train.arrivalTime}` === selectedId);
    const canContinue = !loading && !error && selectedTrain && selectedTrain.price !== null;
    const handleNext = () => {
        if (!canContinue || !selectedTrain) return;
        try {
            navigate("/seat", { state: selectTrain(reservation, selectedTrain) });
        } catch (error) {
            alert(error instanceof Error ? error.message : "열차 정보를 다시 확인해주세요.");
        }
    };

    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">
                <Header title="기차 시간표 조회" />
                <main className="mt-6 px-6">
                    <div className="flex justify-between items-end">
                        <div>
                            <p className="text-xl font-bold">원하는 열차 시간을 선택해주세요.</p>
                            <p className="text-gray-700 mt-2 text-m font-bold">{departureStation} ➔ {arrivalStation}</p>
                        </div>
                        <span className="bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full">{reservation.passengers}명</span>
                    </div>
                    <div className="mt-2 text-s text-gray-500">{departureFrom} 이후 열차</div>
                </main>

                {loading && <p className="text-center mt-20 text-gray-500" role="status">시간표를 불러오는 중...</p>}
                {!loading && (error || trains.length === 0) && (
                    <div className="text-center mt-16 px-6" role={error ? "alert" : "status"}>
                        <p className={error ? "text-red-600" : "text-gray-600"}>{error || "선택한 조건에 해당하는 열차가 없습니다. 날짜와 시간을 다시 선택해주세요."}</p>
                        <button onClick={() => setAttempt(value => value + 1)} className="mt-4 px-4 py-2 rounded-lg bg-blue-600 text-white">다시 조회하기</button>
                    </div>
                )}
                {!loading && !error && trains.length > 0 && (
                    <div className="mt-4 px-4 flex-1 overflow-hidden">
                        <div className="bg-white rounded-xl shadow-inner overflow-y-scroll no-scrollbar h-full p-2 pb-20">
                            {trains.map(train => {
                                const id = `${train.trainNumber}/${train.departureTime}/${train.arrivalTime}`;
                                const minutes = (new Date(train.arrivalTime).getTime() - new Date(train.departureTime).getTime()) / 60000;
                                const formatTime = (time: string) => new Date(time).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
                                return (
                                    <div key={id} className="mb-1">
                                        <TrainRow
                                            id={id} trainType={train.trainName} trainNumber={train.trainNumber}
                                            departTime={formatTime(train.departureTime)} arriveTime={formatTime(train.arrivalTime)}
                                            duration={`${Math.floor(minutes / 60)}시간 ${minutes % 60}분`}
                                            normalPrice={train.price === null ? "운임 정보 없음" : `${train.price.toLocaleString()}원`}
                                            departureStation={train.departureStation} arrivalStation={train.arrivalStation}
                                            isSelected={selectedId === id} onSelect={() => setSelectedId(id)}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
                <div className="w-full px-6 pb-8 pt-4 bg-white z-10 mt-auto">
                    {selectedTrain?.price === null && <p className="text-sm text-red-600 mb-2">운임 정보가 없는 열차는 선택할 수 없습니다.</p>}
                    <button disabled={!canContinue} onClick={handleNext}
                        className={`w-full py-4 rounded-xl text-white font-bold text-lg shadow-lg transition-colors ${canContinue ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-300 cursor-not-allowed"}`}>
                        좌석 선택하기
                    </button>
                </div>
            </div>
        </div>
    );
}
