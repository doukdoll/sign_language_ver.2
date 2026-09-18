import test from 'node:test';
import assert from 'node:assert/strict';
import { RecognitionSession, normalizeKeypoints } from '../src/utils/recognitionSession.ts';

const points = () => Array.from({ length: 137 }, () => [0.1, 0.2, 1]);
function fixture(target = 'DEPARTURE', id = 'owner-a') {
  const sent = [], states = [], results = [], errors = [];
  const session = new RecognitionSession(target, m => sent.push(m), s => states.push(s),
    (label, prob) => results.push({ label, prob }), e => errors.push(e.message), () => 42);
  const ack = (type = 'SESSION_STARTED', revision = 0) => session.receive({
    protocolVersion: 1, type, sessionId: id, revision, recognitionTarget: target, timestamp: 42,
  });
  const result = (extra = {}) => session.receive({
    protocolVersion: 1, type: 'RESULT', sessionId: id, revision: session.revision,
    recognitionTarget: target, timestamp: 42, frameIndex: 0, recognizedProb: 98.7,
    departureCity: target === 'DEPARTURE' ? '서울역' : null,
    arrivalCity: target === 'ARRIVAL' ? '부산역' : null, ...extra,
  });
  return { session, ack, result, sent, states, results, errors };
}

test('START omits client ID; frames wait for matching AI ACK', () => {
  const f = fixture();
  f.session.start();
  assert.equal(f.sent[0].sessionId, undefined);
  assert.equal(f.sent[0].protocolVersion, 1);
  assert.equal(f.session.frame(points()), false);
  f.ack('SESSION_RESET');
  assert.equal(f.session.phase, 'starting');
  f.ack();
  assert.equal(f.session.frame(points()), true);
  assert.equal(f.sent[1].sessionId, 'owner-a');
  assert.equal(f.sent[1].frameIndex, 0);
});
test('RESET rejects stale results and gates index zero until ACK', () => {
  const f = fixture();
  f.ack(); f.session.frame(points()); f.result();
  assert.equal(f.results.at(-1).label, '서울역');
  assert.equal(f.session.reset(), true);
  assert.equal(f.session.reset(), false);
  assert.equal(f.sent.at(-1).revision, 1);
  const count = f.results.length;
  f.result({ revision: 0 });
  f.ack('SESSION_STARTED');
  assert.equal(f.results.length, count);
  assert.equal(f.session.frame(points()), false);
  f.ack('SESSION_RESET', 1); f.session.frame(points());
  assert.equal(f.sent.at(-1).frameIndex, 0);
});
test('owner, target, version and result ordering are checked', () => {
  const f = fixture(); f.ack(); f.session.frame(points()); f.session.frame(points());
  for (const extra of [{ sessionId: 'other' }, { recognitionTarget: 'ARRIVAL' },
    { protocolVersion: 2 }, { frameIndex: 8 }, { recognizedProb: 101 }, { arrivalCity: '부산역' }]) f.result(extra);
  assert.equal(f.results.length, 0);
  f.result({ frameIndex: 1 }); f.result({ frameIndex: 0 }); f.result({ frameIndex: 1 });
  assert.equal(f.results.length, 1);
});
test('ARRIVAL reads arrivalCity; unknown clears a previous station', () => {
  const f = fixture('ARRIVAL'); f.ack(); f.session.frame(points()); f.result();
  assert.equal(f.results.at(-1).label, '부산역');
  f.session.frame(points()); f.result({ frameIndex: 1, arrivalCity: '<unk>' });
  assert.equal(f.results.at(-1).label, null);
  assert.match(f.states.at(-1).lastError, /다시 시도/);
  f.session.frame(points());
  assert.match(f.states.at(-1).lastError, /다시 시도/);
});
test('missing landmarks serialize to null/null/0, valid zero coordinates remain', () => {
  const p = points(); p[0] = [NaN, NaN, 0]; p[1] = [0, 0, 1]; p[2] = [Infinity, 0, 1];
  const wire = normalizeKeypoints(p);
  assert.deepEqual(wire[0], [null, null, 0]);
  assert.deepEqual(wire[1], [0, 0, 1]);
  assert.deepEqual(wire[2], [null, null, 0]);
  assert.throws(() => normalizeKeypoints([[0, 0, 1]]));
  p[3] = [0, 0, 2]; assert.throws(() => normalizeKeypoints(p));
});
test('server errors clear result and stop frames; stale errors do not', () => {
  const f = fixture(); f.ack(); f.session.frame(points()); f.result();
  const error = { protocolVersion: 1, type: 'ERROR', sessionId: 'owner-a', revision: 0,
    timestamp: 42, errorCode: 'INFERENCE_FAILED', errorMessage: '추론 실패' };
  f.session.reset(); f.ack('SESSION_RESET', 1);
  f.session.receive(error); assert.equal(f.session.phase, 'active');
  f.session.receive({ ...error, revision: 1 });
  assert.equal(f.results.at(-1).label, null);
  assert.equal(f.session.frame(points()), false);
  assert.equal(f.session.reset(), true);
});
test('END and fresh reconnect never reuse ID or frame counters', () => {
  const f = fixture(); f.ack(); f.session.frame(points()); f.session.end();
  assert.equal(f.sent.at(-1).type, 'END_SESSION');
  assert.equal(f.session.frame(points()), false);
  f.result(); assert.equal(f.results.length, 0);
  const fresh = fixture('DEPARTURE', 'owner-new'); fresh.session.start(); fresh.ack();
  fresh.session.frame(points());
  assert.equal(fresh.sent.at(-1).revision, 0);
  assert.equal(fresh.sent.at(-1).frameIndex, 0);
});
test('two independent clients cannot change each other', () => {
  const a = fixture(), b = fixture('ARRIVAL', 'owner-b');
  a.ack(); b.ack(); a.session.frame(points()); b.session.frame(points()); a.session.reset();
  b.result(); assert.equal(b.results.at(-1).label, '부산역'); assert.equal(b.session.revision, 0);
});
