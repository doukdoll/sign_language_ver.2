import SeatRow from "./SeatRow";
import type { SeatStatus } from "../../styles/seatStyles";

interface Props {
  seats: Record<string, SeatStatus>;
  onSelect: (num: string) => void;
}

export default function SeatGrid({ seats, onSelect }: Props) {
  return (
    <div className="space-y-3">
      {[...Array(7)].map((_, i) => (
        <SeatRow 
          key={i}
          row={i + 1}
          seats={seats}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
