import Header from "../components/Header";
import DatePicker from "react-datepicker";
import { setDateTime } from "../api/axios";
import { useLocation } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import "react-datepicker/dist/react-datepicker.css";
import { ko } from "date-fns/locale/ko";
import "../styles/calendar.css";
import { useState, useEffect } from "react";

export default function DateTimePage() {

    const location = useLocation();
    console.log("📝 DateTimePage received state:", location.state);

    // [수정 1] passengers(탑승 인원) 추가로 꺼내기
    const { departureStation, arrivalStation, tripType, passengers } = location.state || {};

    const [step, setStep] = useState<"departure" | "return">("departure");

    // 출발 날짜/시간
    const [departureDate, setDepartureDate] = useState<Date>(new Date());
    const [departureHour, setDepartureHour] = useState<number | null>(null);

    // 복귀 날짜/시간(왕복)
    const [returnDate, setReturnDate] = useState<Date | null>(null);
    const [returnHour, setReturnHour] = useState<number | null>(null);

    const hours = Array.from({ length: 24 }, (_, i) => i);

    // 로그
    useEffect(() => console.log("🚆 가는 날짜:", departureDate), [departureDate]);
    useEffect(() => console.log("⏰ 가는 시간:", departureHour), [departureHour]);
    useEffect(() => console.log("🔄 오는 날짜:", returnDate), [returnDate]);
    useEffect(() => console.log("🔂 오는 시간:", returnHour), [returnHour]);
    // 데이터 확인용 로그 추가
    useEffect(() => console.log("👥 탑승 인원:", passengers), [passengers]);

    const navigate = useNavigate();

    const formatDate = (date: Date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    };

    const handleNext = () => {
        if (tripType === "one-way") {
            console.log("편도 선택");
            handleRequestOneWay();
            return;
        }
        setStep("return");
    };

    // ✅ [수정] 편도 요청 처리
    const handleRequestOneWay = async () => {
        if (departureHour === null) return alert("출발 시간을 선택해주세요.");

        const depDate = formatDate(departureDate);
        const depTime = `${String(departureHour).padStart(2, "0")}:00`;

        const sendData = `${depDate} ${depTime}`;
        console.log("📤 편도 데이터 전송:", sendData);

        try {
            const res = await setDateTime(sendData);
            console.log("📥 datetime 응답:", res);

            navigate("/timetable", {
                state: {
                    departureStation,
                    arrivalStation,
                    tripType,
                    passengers, // [수정 2] 다음 페이지로 인원수 전달
                    departureDate,
                    departureHour,
                },
            });
        } catch (err) {
            console.error("편도 datetime 전송 실패:", err);
            alert("오류가 발생했습니다.");
        }
    };

    // ✅ [수정] 왕복 요청 처리
    const handleSearchTrain = async () => {
        if (departureHour === null || returnHour === null)
            return alert("모든 시간 정보를 선택해주세요.");

        const depDate = formatDate(departureDate);
        const depTime = `${String(departureHour).padStart(2, "0")}:00`;

        const retDate = returnDate ? formatDate(returnDate) : null;
        const retTime = `${String(returnHour).padStart(2, "0")}:00`;

        const sendData = `${depDate} ${depTime} | ${retDate} ${retTime}`;
        console.log("📤 왕복 데이터 전송:", sendData);

        try {
            const res = await setDateTime(sendData);
            console.log("📥 datetime 응답:", res);

            navigate("/timetable", {
                state: {
                    departureStation,
                    arrivalStation,
                    tripType,
                    passengers, // [수정 3] 다음 페이지로 인원수 전달
                    departureDate,
                    departureHour,
                    returnDate,
                    returnHour,
                },
            });
        } catch (err) {
            console.error("왕복 datetime 전송 실패:", err);
            alert("오류가 발생했습니다.");
        }
    };


    return (
        <div className="flex justify-center w-screen h-screen bg-white">
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
                            if (step === "departure") setDepartureDate(d!);
                            else setReturnDate(d!);
                        }}
                        filterDate={(date) => {
                            const today = new Date();
                            today.setHours(0, 0, 0, 0);
                            const target = new Date(date);
                            target.setHours(0, 0, 0, 0);

                            if (step === "departure") {
                                return target >= today;
                            } else {
                                const dep = new Date(departureDate);
                                dep.setHours(0, 0, 0, 0);
                                return target >= dep;
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