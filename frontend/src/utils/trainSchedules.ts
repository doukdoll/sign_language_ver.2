import { isTrainSchedule } from './reservation.ts';
import type { TrainSchedule } from './reservation.ts';

export interface ScheduleSearchParams { departure: string; destination: string; departureFrom: string }
export interface ScheduleSearchState { loading: boolean; trains: TrainSchedule[]; error: string | null }
type Request = (params: ScheduleSearchParams, signal: AbortSignal) => Promise<unknown>;

// Cancelling a search also ignores late responses from transports that cannot abort immediately.
export function startScheduleSearch(request: Request, params: ScheduleSearchParams, update: (state: ScheduleSearchState) => void) {
  const controller = new AbortController();
  update({ loading: true, trains: [], error: null });
  const completion = Promise.resolve().then(() => {
    if (controller.signal.aborted) return;
    return request(params, controller.signal);
  }).then(data => {
    if (controller.signal.aborted) return;
    if (!Array.isArray(data) || !data.every(isTrainSchedule)) throw new Error('Invalid train response');
    update({ loading: false, trains: data, error: null });
  }).catch(() => {
    if (!controller.signal.aborted) update({ loading: false, trains: [], error: '시간표를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.' });
  });
  return { cancel: () => controller.abort(), completion };
}
