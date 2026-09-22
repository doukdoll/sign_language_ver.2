import test from 'node:test';
import assert from 'node:assert/strict';
import { formatSearchDate, getReservationLegs, getReservationTotal, hasScheduleSelection,
  readReservationState, selectSeats, selectTrain } from '../src/utils/reservation.ts';

const outbound = {
  trainName: 'KTX', trainNumber: '101', departureStation: '서울', arrivalStation: '대전',
  departureTime: '2026-09-22T09:00:00', arrivalTime: '2026-09-22T10:00:00', price: 24000,
};
const inbound = {
  trainName: 'KTX', trainNumber: '102', departureStation: '대전', arrivalStation: '서울',
  departureTime: '2026-09-23T14:00:00', arrivalTime: '2026-09-23T15:00:00', price: 26000,
};
const trip = (tripType = 'one-way') => ({
  departureStation: '서울', arrivalStation: '대전', passengers: 2, tripType,
  departureDate: '2026-09-22', departureHour: 9,
  ...(tripType === 'round' ? { returnDate: '2026-09-23', returnHour: 14 } : {}),
});

test('one-way booking preserves route, train and seats and calculates the passenger total', () => {
  const next = selectSeats(selectTrain(trip(), outbound), ['1A', '1B']);
  assert.equal(next.path, '/summary');
  assert.equal(next.state.departureStation, '서울');
  assert.deepEqual(getReservationLegs(next.state), [{ title: '가는 편', train: outbound, seats: ['1A', '1B'] }]);
  assert.equal(getReservationTotal(next.state), 48000);
});

test('round-trip selection keeps outbound seats through both timetable and seat pages', () => {
  const selectedOutbound = selectTrain(trip('round'), outbound);
  const returnSearch = selectSeats(selectedOutbound, ['1A', '1B']);
  assert.equal(returnSearch.path, '/timetable');
  assert.equal(returnSearch.state.tripType, 'round2');
  assert.equal(returnSearch.state.departureStation, '대전');
  assert.equal(returnSearch.state.arrivalStation, '서울');
  assert.equal(returnSearch.state.departureDate, '2026-09-23');
  assert.equal(returnSearch.state.departureHour, 14);
  const selectedInbound = selectTrain(returnSearch.state, inbound);
  assert.deepEqual(selectedInbound.seats1, ['1A', '1B']);
  assert.equal(selectedInbound.selectedTrain1, outbound);
  const summary = selectSeats(selectedInbound, ['2C', '2D']);
  assert.equal(summary.path, '/summary');
  assert.deepEqual(getReservationLegs(summary.state).map(leg => [leg.title, leg.train.trainNumber, leg.seats]),
    [['가는 편', '101', ['1A', '1B']], ['오는 편', '102', ['2C', '2D']]]);
  assert.equal(getReservationTotal(summary.state), 100000);
  assert.deepEqual(readReservationState(summary.state), summary.state);
});

test('direct access and malformed history state cannot produce a valid booking', () => {
  for (const state of [null, undefined, {}, { departureStation: '', arrivalStation: '대전' },
    { ...trip(), passengers: '2' }, { ...trip(), passengers: 0 }, { ...trip(), passengers: 6 },
    { ...trip(), departureDate: 'not-a-date' }, { ...trip(), departureHour: 24 },
    { ...trip(), tripType: 'invalid' }, { ...trip(), seats1: ['1A', '1A'] },
    { ...trip(), seats1: ['99A'] }, { ...trip(), selectedTrain1: { ...outbound, price: -1 } }]) {
    assert.equal(readReservationState(state), null);
  }
  assert.equal(hasScheduleSelection({ departureStation: '서울', arrivalStation: '대전' }), false);
  assert.equal(hasScheduleSelection({ ...trip('round'), returnHour: undefined }), false);
  assert.equal(getReservationTotal(null), null);
  assert.equal(getReservationTotal(trip()), null);
});

test('missing fares, wrong routes, incorrect seat count and duplicate seats are rejected', () => {
  assert.throws(() => selectTrain(trip(), { ...outbound, price: null }));
  assert.throws(() => selectTrain(trip(), inbound));
  const selected = selectTrain(trip(), outbound);
  assert.throws(() => selectSeats(selected, ['1A']));
  assert.throws(() => selectSeats(selected, ['1A', '1A']));
  assert.throws(() => selectSeats(trip(), ['1A', '1B']));
  assert.equal(getReservationTotal({ ...selected, seats1: ['1A'] }), null);
  assert.equal(getReservationTotal({ ...selected, seats1: ['1A', '1B'], selectedTrain1: { ...outbound, price: null } }), null);
});

test('incomplete round trips never become an outbound-only payment', () => {
  const selected = selectTrain(trip('round'), outbound);
  assert.equal(getReservationTotal({ ...selected, seats1: ['1A', '1B'] }), null);
  const returning = selectSeats(selected, ['1A', '1B']).state;
  assert.equal(getReservationTotal(returning), null);
  assert.throws(() => selectSeats(returning, ['2A', '2B']));
  assert.throws(() => selectTrain(returning, { ...inbound, departureTime: '2026-09-22T09:30:00' }));
  assert.equal(getReservationTotal({ ...returning, selectedTrain2: inbound, seats2: ['2A'] }), null);
});

test('reselecting a train clears only seats that belong to that leg', () => {
  const first = selectTrain({ ...trip(), seats1: ['1A', '1B'], selectedTrain2: inbound, seats2: ['2A', '2B'] }, outbound);
  assert.equal(first.seats1, undefined);
  assert.equal(first.selectedTrain2, undefined);
  assert.equal(first.seats2, undefined);
  const returning = selectSeats(selectTrain(trip('round'), outbound), ['1A', '1B']).state;
  const second = selectTrain({ ...returning, seats2: ['2A', '2B'] }, inbound);
  assert.deepEqual(second.seats1, ['1A', '1B']);
  assert.equal(second.seats2, undefined);
});

test('search date preserves local calendar date and supports midnight', () => {
  assert.equal(formatSearchDate(new Date(2026, 8, 22, 18), 0), '2026-09-22 00:00');
  assert.equal(hasScheduleSelection({ ...trip(), departureHour: 0 }), true);
});

test('Daegu city searches accept both backend station aliases and save the actual train route', () => {
  for (const station of ['동대구', '서대구']) {
    const towardDaegu = { ...outbound, arrivalStation: station };
    const selectedArrival = selectTrain({ ...trip(), departureStation: ' 서울 ', arrivalStation: ' 대구 ' }, towardDaegu);
    assert.equal(selectedArrival.departureStation, '서울');
    assert.equal(selectedArrival.arrivalStation, station);
    const fromDaegu = { ...outbound, departureStation: station };
    const selectedDeparture = selectTrain({ ...trip(), departureStation: '대구' }, fromDaegu);
    assert.equal(selectedDeparture.departureStation, station);
    assert.equal(selectedDeparture.arrivalStation, '대전');
  }
  assert.throws(() => selectTrain({ ...trip(), arrivalStation: '대구' }, outbound));
  assert.throws(() => selectTrain({ ...trip(), arrivalStation: '동대구' }, { ...outbound, arrivalStation: '서대구' }));
});

test('round trips reverse the selected physical station without dropping outbound seats', () => {
  const trainToDaegu = { ...outbound, arrivalStation: '동대구' };
  const selected = selectTrain({ ...trip('round'), arrivalStation: '대구' }, trainToDaegu);
  const returning = selectSeats(selected, ['1A', '1B']).state;
  assert.equal(returning.departureStation, '동대구');
  assert.equal(returning.arrivalStation, '서울');
  assert.deepEqual(returning.seats1, ['1A', '1B']);
  const actualReturn = { ...inbound, departureStation: '동대구' };
  const summary = selectSeats(selectTrain(returning, actualReturn), ['2A', '2B']).state;
  assert.deepEqual(getReservationLegs(summary).map(leg => [leg.train.departureStation, leg.train.arrivalStation]),
    [['서울', '동대구'], ['동대구', '서울']]);
  assert.equal(getReservationTotal(summary), 100000);
  assert.throws(() => selectTrain(returning, { ...actualReturn, departureStation: '서대구' }));
});
