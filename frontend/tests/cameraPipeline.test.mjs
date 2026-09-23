import test from 'node:test';
import assert from 'node:assert/strict';
import { startCameraPipeline } from '../src/utils/cameraPipeline.ts';

const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const flush = () => new Promise(resolve => setImmediate(resolve));

function fixture(overrides = {}) {
  const frames = new Map();
  const calls = { opened: 0, created: 0, stopped: 0, closed: 0, sent: 0, ready: 0, errors: [], results: [] };
  const track = new EventTarget();
  track.stop = () => calls.stopped++;
  const stream = { getTracks: () => [track] };
  const video = { srcObject: null, readyState: 2, currentTime: 0 };
  let frameId = 0, receive;
  const processor = {
    initialize: async () => {},
    onResults: callback => { receive = callback; },
    send: async () => { calls.sent++; },
    close: async () => { calls.closed++; },
    ...overrides.processor,
  };
  const stop = startCameraPipeline({
    video,
    getStream: async () => { calls.opened++; return stream; },
    createProcessor: () => { calls.created++; return processor; },
    onReady: () => calls.ready++,
    onResults: result => calls.results.push(result),
    onError: error => calls.errors.push(error.message),
    schedule: callback => { frames.set(++frameId, callback); return frameId; },
    cancel: id => frames.delete(id),
    ...overrides.options,
  });
  const tick = () => {
    assert.equal(frames.size, 1, 'exactly one scheduled frame');
    const [id, callback] = frames.entries().next().value;
    frames.delete(id);
    callback(0);
  };
  return { calls, stream, track, video, stop, frames, tick, receive: value => receive(value) };
}

test('one stream owner; stop cancels frame loop and releases resources exactly once', async () => {
  const f = fixture();
  await flush();
  assert.equal(f.calls.opened, 1);
  assert.equal(f.calls.created, 1);
  assert.equal(f.calls.ready, 1);
  assert.equal(f.video.srcObject, f.stream);
  f.tick();
  await flush();
  assert.equal(f.calls.sent, 1);
  f.stop();
  f.stop();
  await flush();
  assert.equal(f.frames.size, 0);
  assert.equal(f.calls.stopped, 1);
  assert.equal(f.calls.closed, 1);
  assert.equal(f.video.srcObject, null);
  f.receive('late result');
  assert.deepEqual(f.calls.results, []);
});

test('permission granted after cleanup stops its stream without starting MediaPipe', async () => {
  const permission = deferred();
  let stopped = 0;
  const f = fixture({ options: { getStream: () => permission.promise } });
  f.stop();
  permission.resolve({ getTracks: () => [{ stop: () => stopped++ }] });
  await flush();
  assert.equal(stopped, 1);
  assert.equal(f.calls.created, 0);
  assert.equal(f.calls.ready, 0);
  assert.equal(f.frames.size, 0);
  assert.equal(f.video.srcObject, null);
});

test('cleanup during initialization stops camera immediately and closes processor only after initialization', async () => {
  const init = deferred();
  const f = fixture({ processor: { initialize: () => init.promise } });
  await flush();
  f.stop();
  assert.equal(f.calls.stopped, 1);
  assert.equal(f.calls.closed, 0);
  init.resolve();
  await flush();
  assert.equal(f.calls.closed, 1);
  assert.equal(f.calls.ready, 0);
  assert.equal(f.frames.size, 0);
});

test('frames are sequential and duplicate/not-loaded video frames are skipped', async () => {
  const send = deferred();
  let sent = 0;
  const f = fixture({ processor: { send: () => { sent++; return send.promise; } } });
  await flush();
  f.video.readyState = 1;
  f.tick();
  await flush();
  assert.equal(sent, 0);
  f.video.readyState = 2;
  f.tick();
  assert.equal(sent, 1);
  assert.equal(f.frames.size, 0, 'no next frame before send completes');
  send.resolve();
  await flush();
  f.tick();
  await flush();
  assert.equal(sent, 1, 'same video timestamp is not processed twice');
  f.video.currentTime = 1;
  f.tick();
  await flush();
  assert.equal(sent, 2);
  f.stop();
});

test('cleanup during send waits to close and does not schedule or deliver late results', async () => {
  const send = deferred();
  const f = fixture({ processor: { send: () => send.promise } });
  await flush();
  f.tick();
  f.stop();
  assert.equal(f.calls.closed, 0);
  assert.equal(f.calls.stopped, 1);
  f.receive('late');
  send.resolve();
  await flush();
  assert.equal(f.calls.closed, 1);
  assert.equal(f.frames.size, 0);
  assert.deepEqual(f.calls.results, []);
});

test('old cleanup does not detach a stream installed by a new owner', async () => {
  const f = fixture();
  await flush();
  const newStream = { getTracks: () => [] };
  f.video.srcObject = newStream;
  f.stop();
  await flush();
  assert.equal(f.video.srcObject, newStream);
  assert.equal(f.calls.stopped, 1);
});

test('permission rejection reports one error without starting a processor', async () => {
  const f = fixture({ options: { getStream: async () => { throw new Error('permission denied'); } } });
  await flush();
  assert.deepEqual(f.calls.errors, ['permission denied']);
  assert.equal(f.calls.created, 0);
  assert.equal(f.frames.size, 0);
});

test('initialization failure releases the camera and processor', async () => {
  const f = fixture({ processor: { initialize: async () => { throw new Error('model load failed'); } } });
  await flush();
  assert.deepEqual(f.calls.errors, ['model load failed']);
  assert.equal(f.calls.stopped, 1);
  assert.equal(f.calls.closed, 1);
  assert.equal(f.calls.ready, 0);
  assert.equal(f.frames.size, 0);
});

test('frame processing failure stops the loop and frees the camera', async () => {
  const f = fixture({ processor: { send: async () => { throw new Error('send failed'); } } });
  await flush();
  f.tick();
  await flush();
  assert.deepEqual(f.calls.errors, ['send failed']);
  assert.equal(f.calls.stopped, 1);
  assert.equal(f.calls.closed, 1);
  assert.equal(f.frames.size, 0);
});

test('late rejected initialization after disposal cannot report errors to an unmounted owner', async () => {
  const init = deferred();
  const f = fixture({ processor: { initialize: () => init.promise } });
  await flush();
  f.stop();
  init.reject(new Error('late failure'));
  await flush();
  assert.deepEqual(f.calls.errors, []);
  assert.equal(f.calls.closed, 1);
});

test('external camera disconnection reports an error and releases resources', async () => {
  const f = fixture();
  await flush();
  f.track.dispatchEvent(new Event('ended'));
  await flush();
  assert.equal(f.calls.errors.length, 1);
  assert.match(f.calls.errors[0], /카메라 연결/);
  assert.equal(f.calls.stopped, 1);
  assert.equal(f.calls.closed, 1);
  assert.equal(f.video.srcObject, null);
  assert.equal(f.frames.size, 0);
  f.track.dispatchEvent(new Event('ended'));
  assert.equal(f.calls.errors.length, 1);
});
