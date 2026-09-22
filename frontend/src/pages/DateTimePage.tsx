import Header from "../components/Header";
import DatePicker from "react-datepicker";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import "react-datepicker/dist/react-datepicker.css";
import { ko } from "date-fns/locale/ko";
import "../styles/calendar.css";
import { useState } from "react";
import { hasTravelSelection, readReservationState } from "../utils/reservation";

export default function DateTimePage() {

    const location = useLocation();
    const reservation = readReservationState(location.state);

    const [step, setStep] = useState<"departure" | "return">("departure");

    // 출발 날짜/시간
    const [departureDate, setDepartureDate] = useState<Date>(new Date());
    const [departureHour, setDepartureHour] = useState<number | null>(null);

    // 복귀 날짜/시간(왕복)
    const [returnDate, setReturnDate] = useState<Date | null>(null);
    const [returnHour, setReturnHour] = useState<number | null>(null);

    const hours = Array.from({ length: 24 }, (_, i) => i);

    const navigate = useNavigate();
    if (!hasTravelSelection(reservation) || reservation.tripType === 'round2') return <Navigate to="/" replace />;

    const handleNext = () => {
        if (departureHour === null) return alert("출발 시간을 선택해주세요.");
        if (reservation.tripType === "one-way") {
            navigate("/timetable", { state: { ...reservation, departureDate, departureHour } });
            return;
        }
        setReturnDate(current => current ?? departureDate);
        setStep("return");
    };

    const handleSearchTrain = () => {
        if (departureHour === null || returnDate === null || returnHour === null)
            return alert("모든 시간 정보를 선택해주세요.");
        const departure = new Date(departureDate);
        departure.setHours(departureHour, 0, 0, 0);
        const returning = new Date(returnDate);
        returning.setHours(returnHour, 0, 0, 0);
        if (returning < departure) {
            alert("돌아오는 시간은 출발 시간 이후로 선택해주세요.");
            return;
        }
        navigate("/timetable", { state: { ...reservation, departureDate, departureHour, returnDate, returnHour } });
    };


    return (
        <div className="flex items-center justify-center w-screen h-screen bg-white to-gray-100">
            <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

                <Header title="날짜/시간 선택" />

                <main className="mt-7 px-6 flex flex-col items-center">

                    <p className="text-xl font-bold mb-4">
                        {step === "departure"
                            ? "출발할 날짜와 시간을 선택해주세요."
                            : "돌아오는 날짜와 시간을 선택해주세요."}
                    </p>

                   
                    {/* 캘린더 UI */}
                    <DatePicker
                        locale={ko}
                        dateFormat="yyyy.MM.dd"
                        selected={step === "departure" ? departureDate : returnDate}
                        onChange={(d) => {
                            if (!d) return;
                            if (step === "departure") setDepartureDate(d);
                            else setReturnDate(d);
                        }}
                        filterDate={(date) => {
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);

                            //다음 달까지만 표시하기위한 변수
                            const nextMonth = new Date(today);
                            nextMonth.setMonth(nextMonth.getMonth() + 1);

                            const target = new Date(date);
                            target.setHours(0, 0, 0, 0);

                            if (step === "departure") {
                                return target >= today && target <= nextMonth;
                            } else {
                                const dep = new Date(departureDate);
                                dep.setHours(0, 0, 0, 0);
                                return target >= dep && target <= nextMonth;
                            }
                        }}
                        inline
                        calendarClassName="custom-calendar"
                        wrapperClassName="custom-calendar-wrapper"
                        showTimeSelect={false}
                    />

                    {/* 시간 선택 */}
                    <div className="w-full flex overflow-x-auto gap-3 py-3 no-scrollbar">
                        {hours.map((h) => {
                            const selected = step === "departure" ? departureHour : returnHour;
                            return (
                                <button
                                    key={h}
                                    onClick={() => {
                                        if (step === "departure") setDepartureHour(h);
                                        else setReturnHour(h);
                                    }}
                                    className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm border font-semibold
                    ${selected === h
                                            ? "bg-blue-600 text-white border-blue-600"
                                            : "bg-white text-slate-700 border-slate-300"
                                        }
                  `}
                                >
                                    {String(h).padStart(2, "0")}시
                                </button>
                            );
                        })}
                    </div>

                    {/* 버튼 */}
                    <div className="mt-6">
                        {step === "departure" ? (
                            <button
                                className="bg-blue-600 text-white px-6 py-3 rounded-xl text-lg font-bold"
                                onClick={handleNext}
                            >
                                다음
                            </button>
                        ) : (
                            <button
                                className="bg-green-600 text-white px-6 py-3 rounded-xl text-lg font-bold"
                                onClick={handleSearchTrain}
                            >
                                기차 조회하기
                            </button>
                        )}
                    </div>

                </main>
            </div>
        </div>
    );
}
