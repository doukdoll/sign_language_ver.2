import { useState } from "react";
import  type {SeatStatus } from "../styles/seatStyles";

// 좌석 선택 로직
export function useSeatStatus(initialSeats: Record<string, SeatStatus>) {
  const [seats, setSeats] = useState(initialSeats);

  const toggleSeat = (seatNum: string) => {
    if (seats[seatNum] === "occupied") return;

    setSeats(prev => ({
      ...prev,
      [seatNum]:
        prev[seatNum] === "selected" ? "available" : "selected"
    }));
  };

  const selectedSeats = Object.keys(seats)
    .filter(s => seats[s] === "selected")
    .sort();

  return { seats, toggleSeat, selectedSeats };
}
