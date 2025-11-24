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
        grid grid-cols-[auto_1fr_auto] w-full items-center
        rounded-xl border transition-all cursor-pointer select-none
        ${isSelected ? "border-2 border-blue-500 bg-blue-50" : "border border-gray-300 bg-white"}
      `}
      onClick={() => onSelect(id)}
    >

      {/* LEFT — 로고 + 번호 */}
      <div className="flex flex-col items-start pl-5 py-4">
        <img src={ktxLogo} alt="KTX" className="w-8 h-auto mb-1" />
        <span className="text-sm font-semibold">{trainNumber}</span>
      </div>

      {/* MIDDLE — 노선 + 시간 + 소요시간 */}
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

      {/* RIGHT — 가격 박스 */}
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
