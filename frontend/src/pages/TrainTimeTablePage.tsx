import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import TrainRow from "../components/TrainCard";

export default function TrainTimeTablePage() {

  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const handleSelectTrain = (id: string) => {
    setSelectedId(id);
  };

  const timetableData = [
    {
      id: "1",
      trainType: "KTX",
      trainNumber: "001",
      departTime: "05:13",
      arriveTime: "07:50",
      duration: "2시간 37분",
      normalPrice: "50,800원",
      discountText: "일반 15% 할인",
      specialPrice: "74,700원",
    },
    {
      id: "2",
      trainType: "KTX",
      trainNumber: "003",
      departTime: "05:27",
      arriveTime: "08:16",
      duration: "2시간 49분",
      normalPrice: "50,800원",
      discountText: "일반 15% 할인",
      specialPrice: "74,700원",
    },
    {
      id: "3",
      trainType: "무궁화",
      trainNumber: "1301",
      departTime: "05:54",
      arriveTime: "11:39",
      duration: "5시간 45분",
      normalPrice: "28,600원",
    },
    {
      id: "4",
      trainType: "KTX",
      trainNumber: "005",
      departTime: "05:58",
      arriveTime: "08:43",
      duration: "2시간 45분",
      normalPrice: "59,800원",
      discountText: "일반 10% 할인",
      specialPrice: "77,300원",
    },
    {
      id: "5",
      trainType: "KTX-산천",
      trainNumber: "075",
      departTime: "06:03",
      arriveTime: "08:49",
      duration: "2시간 46분",
      normalPrice: "59,800원",
      specialPrice: "83,700원",
    },
    {
      id: "6",
      trainType: "ITX-새마을",
      trainNumber: "1001",
      departTime: "06:13",
      arriveTime: "11:06",
      duration: "4시간 53분",
      normalPrice: "42,600원",
    },
    {
      id: "7",
      trainType: "KTX",
      trainNumber: "007",
      departTime: "06:33",
      arriveTime: "09:22",
      duration: "2시간 49분",
      normalPrice: "59,800원",
      specialPrice: "83,700원",
    },
    {
      id: "8",
      trainType: "무궁화",
      trainNumber: "1303",
      departTime: "06:37",
      arriveTime: "12:11",
      duration: "5시간 34분",
      normalPrice: "28,600원",
    },
    {
      id: "9",
      trainType: "KTX",
      trainNumber: "011",
      departTime: "06:50",
      arriveTime: "09:30",
      duration: "2시간 40분",
      normalPrice: "59,800원",
      discountText: "일반 10% 할인",
      specialPrice: "77,300원",
    },
    {
      id: "10",
      trainType: "KTX",
      trainNumber: "013",
      departTime: "07:05",
      arriveTime: "09:45",
      duration: "2시간 40분",
      normalPrice: "50,800원",
      discountText: "일반 15% 할인",
      specialPrice: "74,700원",
    },
    {
      id: "11",
      trainType: "ITX-새마을",
      trainNumber: "1003",
      departTime: "07:18",
      arriveTime: "12:10",
      duration: "4시간 52분",
      normalPrice: "42,600원",
    },
    {
      id: "12",
      trainType: "무궁화",
      trainNumber: "1305",
      departTime: "07:33",
      arriveTime: "13:20",
      duration: "5시간 47분",
      normalPrice: "28,600원",
    },
    {
      id: "13",
      trainType: "KTX-산천",
      trainNumber: "079",
      departTime: "07:45",
      arriveTime: "10:32",
      duration: "2시간 47분",
      normalPrice: "59,800원",
      specialPrice: "83,700원",
    }
  ];

  return (
    <div className="flex justify-center w-screen h-screen bg-white">
      <div className="w-[450px] h-[900px] bg-gradient-to-b from-blue-50 to-white shadow-xl flex flex-col">

        <Header title="기차 시간표 조회" />

        <main className="mt-6 px-6">
          <p className="text-xl font-bold">원하는 열차 시간을 선택해주세요.</p>
        </main>
        
        <div className="mt-4 px-4">
          <div className="bg-white rounded-xl shadow-md overflow-y-scroll no-scrollbar h-[560px] p-2">

            {timetableData.map((train) => (
              <TrainRow
                key={train.id}
                {...train}
                isSelected={selectedId === train.id}
                onSelect={handleSelectTrain}
              />
            ))}

          </div>
        </div>

        {/* 예매 페이지 이동 */}
        <button
          disabled={!selectedId}
          onClick={() =>
            navigate("/seat", { state: { trainId: selectedId } })
          }
          className={`mt-4 mx-auto w-[90%] py-3 rounded-xl text-white font-bold
            ${selectedId ? "bg-blue-600" : "bg-gray-300"}
          `}
        >
          예매
        </button>
      </div>
    </div>
  );
} 