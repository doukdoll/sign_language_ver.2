import test from 'node:test';
import assert from 'node:assert/strict';
import { startScheduleSearch } from '../src/utils/trainSchedules.ts';

const params = { departure: '서울', destination: '대전', departureFrom: '2026-09-22 09:00' };
const train = { trainName: 'KTX', trainNumber: '101', departureStation: '서울', arrivalStation: '대전',
  departureTime: '2026-09-22T09:00:00', arrivalTime: '2026-09-22T10:00:00', price: 24000 };

test('a new search clears previous results and sends the exact query and abort signal', async () => {
  const updates = [];
  const request = startScheduleSearch(async (query, signal) => {
    assert.deepEqual(query, params);
    assert.equal(signal.aborted, false);
    return [train];
  }, params, state => updates.push(state));
  assert.deepEqual(updates[0], { loading: true, trains: [], error: null });
  await request.completion;
  assert.deepEqual(updates.at(-1), { loading: false, trains: [train], error: null });
});

test('empty results stay empty instead of becoming fictional train schedules', async () => {
  const updates = [];
  await startScheduleSearch(async () => [], params, state => updates.push(state)).completion;
  assert.deepEqual(updates.at(-1), { loading: false, trains: [], error: null });
});

test('network errors and invalid response bodies produce errors, never fake schedules', async () => {
  for (const response of [null, {}, [{ ...train, price: '24000' }], [{ ...train, arrivalTime: 'invalid' }]]) {
    const updates = [];
    await startScheduleSearch(async () => response, params, state => updates.push(state)).completion;
    assert.equal(updates.at(-1).loading, false);
    assert.deepEqual(updates.at(-1).trains, []);
    assert.ok(updates.at(-1).error);
  }
  const updates = [];
  await startScheduleSearch(async () => { throw new Error('offline'); }, params, state => updates.push(state)).completion;
  assert.ok(updates.at(-1).error);
  assert.deepEqual(updates.at(-1).trains, []);
});

test('cancelled searches abort the transport and ignore a late response', async () => {
  let resolveResponse;
  let signal;
  const updates = [];
  const request = startScheduleSearch((_, requestSignal) => {
    signal = requestSignal;
    return new Promise(resolve => { resolveResponse = resolve; });
  }, params, state => updates.push(state));
  await Promise.resolve();
  request.cancel();
  assert.equal(signal.aborted, true);
  resolveResponse([train]);
  await request.completion;
  assert.equal(updates.length, 1);
});

test('cancelling before the request starts performs no HTTP request', async () => {
  let called = false;
  const request = startScheduleSearch(async () => { called = true; return [train]; }, params, () => {});
  request.cancel();
  await request.completion;
  assert.equal(called, false);
});

test('a retry can succeed and a superseded failure cannot overwrite new results', async () => {
  let rejectFirst;
  const updates = [];
  const first = startScheduleSearch(() => new Promise((_, reject) => { rejectFirst = reject; }), params, state => updates.push(state));
  await Promise.resolve();
  first.cancel();
  await startScheduleSearch(async () => [train], params, state => updates.push(state)).completion;
  rejectFirst(new Error('late failure'));
  await first.completion;
  assert.deepEqual(updates.at(-1), { loading: false, trains: [train], error: null });
});
