// 좌석 상태 별 색상
export const seatStyles = {
  available: {
    fill: '#F0F6FF',
    text: '#6B7280'
  },
  selected: {
    fill: '#3B82F6',
    text: '#FFFFFF'
  },
  occupied: {
    fill: '#E5E7EB',
    text: '#9CA3AF'
  }
};

export type SeatStatus = keyof typeof seatStyles;
