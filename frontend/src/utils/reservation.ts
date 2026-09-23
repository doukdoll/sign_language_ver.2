export interface TrainSchedule {
  trainName: string;
  trainNumber: string;
  departureTime: string;
  arrivalTime: string;
  departureStation: string;
  arrivalStation: string;
  price: number | null;
}

export interface ReservationState {
  departureStation: string;
  arrivalStation: string;
  passengers?: number;
  tripType?: 'one-way' | 'round' | 'round2';
  departureDate?: Date | string;
  departureHour?: number;
  returnDate?: Date | string;
  returnHour?: number;
  selectedTrain1?: TrainSchedule;
  selectedTrain2?: TrainSchedule;
  seats1?: string[];
  seats2?: string[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;
const isText = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const isDate = (value: unknown): value is Date | string =>
  (value instanceof Date || isText(value)) && Number.isFinite(new Date(value).getTime());
const isHour = (value: unknown): value is number => Number.isInteger(value) && Number(value) >= 0 && Number(value) <= 23;
const isPassengerCount = (value: unknown): value is number => Number.isInteger(value) && Number(value) >= 1 && Number(value) <= 5;
const isSeats = (value: unknown): value is string[] => Array.isArray(value) &&
  value.every(seat => typeof seat === 'string' && /^[1-7][A-D]$/.test(seat)) && new Set(value).size === value.length;

export function isTrainSchedule(value: unknown): value is TrainSchedule {
  if (!isRecord(value)) return false;
  return ['trainName', 'trainNumber', 'departureStation', 'arrivalStation'].every(key => isText(value[key])) &&
    typeof value.departureTime === 'string' && isDate(value.departureTime) &&
    typeof value.arrivalTime === 'string' && isDate(value.arrivalTime) &&
    new Date(value.arrivalTime).getTime() >= new Date(value.departureTime).getTime() &&
    (value.price === null || (typeof value.price === 'number' && Number.isFinite(value.price) && value.price > 0));
}

// Router state is external input too: direct links and old history entries may have incomplete data.
export function readReservationState(value: unknown): ReservationState | null {
  if (!isRecord(value) || !isText(value.departureStation) || !isText(value.arrivalStation)) return null;
  if (value.passengers !== undefined && !isPassengerCount(value.passengers)) return null;
  if (value.tripType !== undefined && (typeof value.tripType !== 'string' || !['one-way', 'round', 'round2'].includes(value.tripType))) return null;
  for (const key of ['departureDate', 'returnDate']) {
    if (value[key] !== undefined && !isDate(value[key])) return null;
  }
  for (const key of ['departureHour', 'returnHour']) {
    if (value[key] !== undefined && !isHour(value[key])) return null;
  }
  for (const key of ['selectedTrain1', 'selectedTrain2']) {
    if (value[key] !== undefined && !isTrainSchedule(value[key])) return null;
  }
  for (const key of ['seats1', 'seats2']) {
    if (value[key] !== undefined && !isSeats(value[key])) return null;
  }
  return value as unknown as ReservationState;
}

export function hasTravelSelection(state: ReservationState | null): state is ReservationState & {
  passengers: number; tripType: NonNullable<ReservationState['tripType']>;
} {
  return !!state && isPassengerCount(state.passengers) && !!state.tripType;
}

export function hasScheduleSelection(state: ReservationState | null): state is ReservationState & {
  passengers: number; tripType: NonNullable<ReservationState['tripType']>; departureDate: Date | string; departureHour: number;
} {
  return hasTravelSelection(state) && isDate(state.departureDate) && isHour(state.departureHour) &&
    (state.tripType === 'one-way' || (isDate(state.returnDate) && isHour(state.returnHour))) &&
    (state.tripType !== 'round2' || (!!state.selectedTrain1 && state.seats1?.length === state.passengers));
}

export function formatSearchDate(date: Date | string, hour: number): string {
  const value = new Date(date);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')} ${String(hour).padStart(2, '0')}:00`;
}

function matchesStationQuery(query: string, station: string): boolean {
  const trimmed = query.trim();
  // KorailService expands the city query '대구' to these two physical stations.
  return trimmed === station || (trimmed === '대구' && (station === '동대구' || station === '서대구'));
}

export function selectTrain(state: ReservationState, train: TrainSchedule): ReservationState {
  if (!hasScheduleSelection(state) || train.price === null || !isTrainSchedule(train)) throw new Error('열차 선택 정보가 올바르지 않습니다.');
  if (!matchesStationQuery(state.departureStation, train.departureStation) ||
      !matchesStationQuery(state.arrivalStation, train.arrivalStation)) throw new Error('조회한 경로와 열차 경로가 다릅니다.');
  if (state.tripType === 'round2' && state.selectedTrain1 &&
      new Date(train.departureTime) < new Date(state.selectedTrain1.arrivalTime)) throw new Error('가는 편 도착 이후의 돌아오는 열차를 선택해주세요.');
  // Once selected, seat displays and return searches use the actual train endpoints, not a city alias.
  const selected = { ...state, departureStation: train.departureStation, arrivalStation: train.arrivalStation };
  return state.tripType === 'round2'
    ? { ...selected, selectedTrain2: train, seats2: undefined }
    : { ...selected, selectedTrain1: train, seats1: undefined, selectedTrain2: undefined, seats2: undefined };
}

export function selectSeats(state: ReservationState, seats: string[]): { path: string; state: ReservationState } {
  if (!hasScheduleSelection(state) || !isSeats(seats) || seats.length !== state.passengers ||
      !state.selectedTrain1 || (state.tripType === 'round2' && !state.selectedTrain2)) {
    throw new Error('탑승 인원에 맞는 열차와 좌석을 선택해주세요.');
  }
  if (state.tripType === 'round') {
    return { path: '/timetable', state: {
      ...state, departureStation: state.arrivalStation, arrivalStation: state.departureStation,
      tripType: 'round2', departureDate: state.returnDate, departureHour: state.returnHour, seats1: [...seats],
      selectedTrain2: undefined, seats2: undefined,
    } };
  }
  return { path: '/summary', state: state.tripType === 'round2'
    ? { ...state, seats2: [...seats] } : { ...state, seats1: [...seats] } };
}

export interface ReservationLeg { title: string; train: TrainSchedule; seats: string[] }
export function getReservationLegs(state: ReservationState | null): ReservationLeg[] {
  if (!hasScheduleSelection(state) || state.tripType === 'round' || !state.selectedTrain1 ||
      state.selectedTrain1.price === null || state.seats1?.length !== state.passengers) return [];
  const legs = [{ title: '가는 편', train: state.selectedTrain1, seats: state.seats1 }];
  if (state.tripType === 'round2') {
    if (!state.selectedTrain2 || state.selectedTrain2.price === null || state.seats2?.length !== state.passengers) return [];
    legs.push({ title: '오는 편', train: state.selectedTrain2, seats: state.seats2 });
  }
  return legs;
}

export function getReservationTotal(state: ReservationState | null): number | null {
  const legs = getReservationLegs(state);
  if (!state?.passengers || !legs.length) return null;
  return legs.reduce((total, leg) => total + (leg.train.price ?? 0), 0) * state.passengers;
}
