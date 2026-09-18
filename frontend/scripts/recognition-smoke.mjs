// Real FE session code -> running Spring backend -> running Python/ONNX server.
// Synthetic landmarks verify transport/inference execution, NEVER recognition accuracy.
import assert from 'node:assert/strict';
import { RecognitionSession } from '../src/utils/recognitionSession.ts';

const url = process.argv.slice(2).find(value => !value.startsWith('--')) || 'ws://127.0.0.1:8080/api/sign/stream';
const timeoutMs = 30000;
const clients = [];

function connect(target) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const packets = [];
    const waiters = new Set();
    const session = new RecognitionSession(target, message => socket.send(JSON.stringify(message)),
      () => {}, () => {}, () => {});
    const client = {
      socket, session, packets,
      send: message => socket.send(JSON.stringify(message)),
      wait(predicate, description, after = 0) {
        return new Promise((done, fail) => {
          const timer = setTimeout(() => {
            waiters.delete(check);
            fail(new Error('Timeout: ' + description));
          }, timeoutMs);
          function check() {
            const packet = packets.slice(after).find(predicate);
            if (packet) { clearTimeout(timer); waiters.delete(check); done(packet); }
          }
          waiters.add(check);
          check();
        });
      },
    };
    clients.push(client);
    const timer = setTimeout(() => reject(new Error('Connection/START timeout')), timeoutMs);
    socket.addEventListener('open', () => session.start());
    socket.addEventListener('error', () => {
      clearTimeout(timer);
      reject(new Error('WebSocket connection failed: ' + url));
    });
    socket.addEventListener('message', event => {
      try {
        const packet = JSON.parse(event.data);
        packets.push(packet);
        session.receive(packet);
        for (const notify of [...waiters]) notify();
        if (session.phase === 'active') { clearTimeout(timer); resolve(client); }
        if (packet.type === 'ERROR' && !session.sessionId) {
          clearTimeout(timer);
          reject(new Error('START failed: ' + packet.errorCode));
        }
      } catch (error) { clearTimeout(timer); reject(error); }
    });
    socket.addEventListener('close', () => {
      clearTimeout(timer);
      if (!session.sessionId) reject(new Error('Closed before SESSION_STARTED'));
    });
  });
}

function points(frame, offset = 0) {
  return Array.from({ length: 137 }, (_, index) => [
    Number((0.2 + (index % 13) * 0.02 + Math.sin(frame / 10 + offset) * 0.01).toFixed(5)),
    Number((0.2 + Math.floor(index / 13) * 0.03).toFixed(5)), 1,
  ]);
}

function result(client, revision, after = 0) {
  return client.wait(packet => packet.type === 'RESULT' && packet.revision === revision,
    'RESULT revision ' + revision, after);
}

function checkResult(packet, client, target) {
  assert.equal(packet.protocolVersion, 1);
  assert.equal(packet.sessionId, client.session.sessionId);
  assert.equal(packet.recognitionTarget, target);
  assert.ok(Number.isSafeInteger(packet.frameIndex) && packet.frameIndex >= 127);
  assert.ok(Number.isFinite(packet.recognizedProb) && packet.recognizedProb >= 0 && packet.recognizedProb <= 100);
  assert.equal(typeof packet[target === 'DEPARTURE' ? 'departureCity' : 'arrivalCity'], 'string');
  assert.equal(packet[target === 'DEPARTURE' ? 'arrivalCity' : 'departureCity'], null);
}

try {
  const [a, b] = await Promise.all([connect('DEPARTURE'), connect('ARRIVAL')]);
  assert.notEqual(a.session.sessionId, b.session.sessionId);
  console.log('PASS: two server-owned sessions acknowledged');
  for (let frame = 0; frame < 128; frame++) {
    assert.equal(a.session.frame(points(frame)), true);
    assert.equal(b.session.frame(points(frame, 1)), true);
  }
  const [firstA, firstB] = await Promise.all([result(a, 0), result(b, 0)]);
  checkResult(firstA, a, 'DEPARTURE'); checkResult(firstB, b, 'ARRIVAL');
  console.log('PASS: interleaved users received actual model results with correct owner/target');

  const bBeforeReset = b.packets.length;
  a.session.reset();
  assert.equal(a.session.frame(points(0)), false);
  await a.wait(packet => packet.type === 'SESSION_RESET' && packet.revision === 1, 'RESET ACK');
  assert.equal(a.session.frameIndex, 0);
  for (let frame = 0; frame < 5; frame++) b.session.frame(points(frame));
  const continuedB = await result(b, 0, bBeforeReset);
  checkResult(continuedB, b, 'ARRIVAL');
  assert.equal(continuedB.frameIndex, 132);
  for (let frame = 0; frame < 128; frame++) a.session.frame(points(frame));
  checkResult(await result(a, 1), a, 'DEPARTURE');
  console.log('PASS: A reset starts at frame zero; B buffer and revision stay intact');

  a.send({ protocolVersion: 1, type: 'KEYPOINT_FRAME', sessionId: a.session.sessionId,
    revision: 0, recognitionTarget: 'DEPARTURE', timestamp: Date.now(), frameIndex: 0, keypoints: points(0) });
  await a.wait(packet => packet.errorCode === 'STALE_REVISION', 'stale frame rejection');
  assert.equal(a.session.phase, 'active'); // FE ignores the old-revision error.
  a.send({ protocolVersion: 1, type: 'RESET_SESSION', sessionId: b.session.sessionId,
    revision: 1, recognitionTarget: 'ARRIVAL', timestamp: Date.now() });
  await a.wait(packet => packet.errorCode === 'SESSION_MISMATCH', 'spoof rejection');
  assert.equal(b.session.phase, 'active');
  console.log('PASS: stale frames and forged session IDs rejected');

  a.session.end();
  await a.wait(packet => packet.type === 'SESSION_ENDED', 'END ACK');
  const bBeforeEnd = b.packets.length;
  for (let frame = 0; frame < 5; frame++) b.session.frame(points(frame));
  checkResult(await result(b, 0, bBeforeEnd), b, 'ARRIVAL');
  b.session.end();
  await b.wait(packet => packet.type === 'SESSION_ENDED', 'B END ACK');
  console.log('PASS: ending A does not interrupt B');
  if (process.argv.includes('--expect-disconnect') || process.argv.includes('--expect-expiry')) {
    const [c, d] = await Promise.all([connect('DEPARTURE'), connect('ARRIVAL')]);
    const code = process.argv.includes('--expect-disconnect') ? 'AI_UNAVAILABLE' : 'SESSION_EXPIRED';
    console.log(code === 'AI_UNAVAILABLE' ? 'READY: stop the test AI server now' : 'READY: waiting for configured idle expiry');
    await Promise.all([c.wait(packet => packet.errorCode === code, code),
      d.wait(packet => packet.errorCode === code, code)]);
    assert.equal(c.session.phase, 'failed');
    assert.equal(d.session.phase, 'failed');
    assert.equal(c.session.frame(points(0)), false);
    assert.equal(d.session.frame(points(0)), false);
    console.log('PASS: both owners received ' + code + ' and stopped streaming');
  }
  console.log('SUCCESS: live protocol smoke test (synthetic data; no accuracy claim)');
} finally {
  for (const { socket } of clients) {
    if (socket.readyState < WebSocket.CLOSING) socket.close();
  }
}
