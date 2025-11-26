import { seatStyles} from "../../styles/seatStyles";
import type { SeatStatus } from "../../styles/seatStyles";

interface Props {
  seatNum: string;
  status: SeatStatus;
  onClick: () => void;
}

export default function SeatIcon({ seatNum, status, onClick }: Props) {
  const style = seatStyles[status];

  return (
    <button
      onClick={onClick}
      disabled={status === "occupied"}
      className="
        relative w-20 h-24 flex items-center justify-center 
        text-lg font-bold transition-all active:scale-95
      "
      style={{
        backgroundColor: "transparent",
        border: "none",
        color: style.text,
        cursor: status === "occupied" ? "not-allowed" : "pointer"
      }}
    >
      <svg
        width="70"
        height="72"
        viewBox="0 0 109 112"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="absolute"
      >
        <path
          d="M54.5 0C84.5995 0 109 12.536 109 28C109 28.1765 108.996 
             28.3526 108.989 28.5283H109V112H0V28.5283H0.0107422C0.00441209 
             28.3526 0 28.1765 0 28C0 12.536 24.4005 0 54.5 0Z"
          fill={style.fill}
        />
      </svg>

      <span className="relative z-10 mt-2">{seatNum}</span>
    </button>
  );
}
