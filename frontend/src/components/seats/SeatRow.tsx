import SeatIcon from "./SeatIcon";
import type { SeatStatus } from "../../styles/seatStyles";

interface Props {
  row: number;
  seats: Record<string, SeatStatus>;
  onSelect: (num: string) => void;
}

export default function SeatRow({ row, seats, onSelect }: Props) {
  const A = `${row}A`;
  const B = `${row}B`;
  const C = `${row}C`;
  const D = `${row}D`;

  return (
    <div className="flex justify-between items-center">
      <div className="flex gap-4">
        <SeatIcon seatNum={A} status={seats[A]} onClick={() => onSelect(A)} />
        <SeatIcon seatNum={B} status={seats[B]} onClick={() => onSelect(B)} />
      </div>

      {/* 통로 */}
      <div className="flex items-center justify-center w-8">
        <div className="text-2xl text-gray-400">▲</div>
      </div>

      <div className="flex gap-4">
        <SeatIcon seatNum={C} status={seats[C]} onClick={() => onSelect(C)} />
        <SeatIcon seatNum={D} status={seats[D]} onClick={() => onSelect(D)} />
      </div>
    </div>
  );
}
