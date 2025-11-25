import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import TrainRow from "../components/TrainCard";
import instance from "../api/axios"; // axios 인스턴스 임포트

export default function TrainTimeTablePage() {

  const navigate = useNavigate();
  const location = useLocation();

  const { departureStation, arrivalStation, tripType, departureDate, departureHour, returnDate, returnHour } = location.state || {};

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [trainSchedules, setTrainSchedules] = useState<any[]>([]); // 열차 시간표 데이터 상태
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log("📝 TrainTimeTablePage state:", {
      departureStation,
      arrivalStation,
      departureDate,
      departureHour,
    });
    const fetchTrainSchedules = async () => {
      if (!departureStation || !arrivalStation || !departureDate || departureHour === null) {
        setError("필수 열차 정보가 누락되었습니다.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // 날짜와 시간을 YYYY-MM-DD HH:MM 형식으로 포맷 (백엔드 API 형식에 맞춤)
        const formattedDate = new Date(departureDate).toISOString().split('T')[0];
        const formattedTime = `${String(departureHour).padStart(2, '0')}:00`;
        const departureFromDateTime = `${formattedDate} ${formattedTime}`;

        // GET 요청을 위한 쿼리 파라미터 구성 (백엔드 API 필드명에 맞춤)
        const params: any = {
          departure: departureStation,
          destination: arrivalStation,
          departureFrom: departureFromDateTime,
        };
        // departureTo는 특정 시간 이후의 열차를 찾는 것이므로 생략합니다.

        // GET 요청으로 변경
        const response = await instance.get("/train/search", { params });
        setTrainSchedules(response.data);
      } catch (err) {
        console.error("기차 시간표 조회 실패:", err);
        setError("기차 시간표를 불러오는 데 실패했습니다. 다시 시도해주세요.");
      } finally {
        setLoading(false);
      }
    };

    fetchTrainSchedules();
  }, [departureStation, arrivalStation, departureDate, departureHour, tripType, returnDate, returnHour]);

  const handleSelectTrain = (id: string) => {
    setSelectedId(id);
  };

  return (
    <div className="flex justify-center w-screen h-screen bg-white">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

        <Header title="기차 시간표 조회" />

        <main className="mt-6 px-6">
          <p className="text-xl font-bold">원하는 열차 시간을 선택해주세요.</p>
          {departureStation && arrivalStation && (
            <p className="text-gray-700 mt-2">출발: {departureStation}, 도착: {arrivalStation}</p>
          )}
          {departureDate && departureHour !== null && (
            <p className="text-gray-700">날짜: {new Date(departureDate).toLocaleDateString()}, 시간: {String(departureHour).padStart(2, '0')}시</p>
          )}
          {tripType === "round" && returnDate && returnHour !== null && (
            <p className="text-gray-700">돌아오는 날짜: {new Date(returnDate).toLocaleDateString()}, 시간: {String(returnHour).padStart(2, '0')}시</p>
          )}
        </main>

        {loading && <p className="text-center mt-8">시간표를 불러오는 중...</p>}
        {error && <p className="text-center mt-8 text-red-500">에러: {error}</p>}
        {!loading && !error && trainSchedules.length === 0 && (
          <p className="text-center mt-8 text-gray-500">조회된 열차 시간표가 없습니다.</p>
        )}
        
        {!loading && !error && trainSchedules.length > 0 && (
        <div className="mt-4 px-4">
          <div className="bg-white rounded-xl shadow-md overflow-y-scroll no-scrollbar h-[560px] p-2">

              {trainSchedules.map((train: any) => (
              <TrainRow
                  key={train.trainNumber + train.departureTime}
                  trainType={train.trainName}
                  trainNumber={train.trainNumber}
                  departTime={new Date(train.departureTime).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                  arriveTime={new Date(train.arrivalTime).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })}
                  duration="계산 필요" // 백엔드에서 계산하여 전달하거나 프론트엔드에서 계산
                  normalPrice={`${train.price?.toLocaleString()}원`}
                  discountText="" // 할인 정보는 백엔드에서 제공하는 경우 사용
                  specialPrice="" // 특별 할인 가격도 백엔드에서 제공하는 경우 사용
                  departureStation={train.departureStation}
                  arrivalStation={train.arrivalStation}
                  isSelected={selectedId === (train.trainNumber + train.departureTime)}
                  onSelect={() => handleSelectTrain(train.trainNumber + train.departureTime)}
              />
            ))}

          </div>
        </div>
        )}

        {/* 예매 페이지 이동 */}
        <button
          disabled={!selectedId || loading || !!error}
          onClick={() =>
            navigate("/payment", { state: { selectedTrainId: selectedId } })
          }
          className={`mt-4 mx-auto w-[90%] py-3 rounded-xl text-white font-bold
            ${selectedId && !loading && !error ? "bg-blue-600" : "bg-gray-300"}
          `}
        >
          예매
        </button>

      </div>
    </div>
  );
}
