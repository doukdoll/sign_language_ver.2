import React from "react";
import ktxLogo from "../components/icons/KTX_logo.svg.png";

export interface TrainRowProps {
  id: string;
  trainNumber: string;
  departTime: string;
  arriveTime: string;
  duration: string;
  normalPrice?: string;
  specialPrice?: string;
  onSelect: (id: string) => void;
  isSelected: boolean;
}

const TrainRow: React.FC<TrainRowProps> = ({
  id,
  trainNumber,
  departTime,
  arriveTime,
  duration,
  normalPrice,
  specialPrice,
  onSelect,
  isSelected,
}) => {
  return (
    <div
      className={`
        relative
        grid grid-cols-[auto_1fr_auto] w-full items-stretch
        rounded-xl border transition-all cursor-pointer select-none
        ${isSelected ? "border-[1.5px] border-blue-500 bg-[#E8F1FF]" : "border border-gray-300 bg-white"}
      `}
      onClick={() => onSelect(id)}
    >
      
      <div className="absolute left-0 top-0 h-full w-2 bg-[#1E3A8A] rounded-l-xl"></div>

      {/* 로고 + 기차 번호*/}
      <div className="flex flex-col items-start pl-5 py-4">
        <img src={ktxLogo} alt="KTX" className="w-8 h-auto mb-1" />
        <span className="text-sm font-semibold">{trainNumber}</span>
      </div>

      {/* 경로 + 시간대 */}
      <div className="flex flex-col justify-center py-4 pl-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[16px] text-gray-700 whitespace-nowrap">
            서울 → 부산
          </span>

          <span className="font-bold text-[15px] text-gray-800 whitespace-nowrap">
            ({departTime} ~ {arriveTime})
          </span>
        </div>

        <span className="text-sm text-gray-500 mt-[2px] whitespace-nowrap">
          소요시간: {duration}
        </span>
      </div>

      {/* 가격 */}
      <div className="flex flex-col items-start pr-8 border-l border-gray-300 py-4 pl-4">
        <span className="text-sm text-gray-500">일반실</span>
        <span className="font-bold text-[15px] text-gray-800 whitespace-nowrap">
          {normalPrice}
        </span>

        {specialPrice && (
          <>
            <span className="text-sm text-gray-500 mt-2">특실</span>
            <span className="font-bold text-[15px] text-gray-800 whitespace-nowrap">
              {specialPrice}
            </span>
          </>
        )}
      </div>
    </div>
  );
};

export default TrainRow;
