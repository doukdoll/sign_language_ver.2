"""Model-free protocol regression tests: python -m unittest tests.test_sessions -v."""

import copy
import json
import unittest

from realtime.sessions import SessionManager, serve_connection


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.windows = []

        def predict(frames):
            self.windows.append(frames)
            return str(frames[-1]), 95.0

        self.manager = SessionManager(
            lambda points: points[0][0], predict, window_size=2, stride=1,
            clock=lambda: self.now, wall_clock=lambda: 1000.0)

    def request(self, kind, sid='A', revision=0, target='DEPARTURE', **extra):
        return dict(dict(protocolVersion=1, type=kind, sessionId=sid,
                         revision=revision, recognitionTarget=target, timestamp=0), **extra)

    def send(self, kind, sid='A', revision=0, target='DEPARTURE', **extra):
        return self.manager.handle(json.dumps(self.request(kind, sid, revision, target, **extra)))

    def frame(self, sid, index, value, revision=0, target='DEPARTURE'):
        return self.send('KEYPOINT_FRAME', sid, revision, target, frameIndex=index,
                         keypoints=[[value, 0, 1] for _ in range(137)])

    def snapshot(self, sid='A'):
        return copy.deepcopy(vars(self.manager.sessions[sid]))

    def test_interleaved_users_keep_separate_windows_and_result_targets(self):
        self.send('START_SESSION')
        self.frame('A', 0, 10)
        self.send('START_SESSION', 'B', target='ARRIVAL')
        self.frame('B', 0, 20, target='ARRIVAL')
        a = self.frame('A', 1, 11)[0]
        b = self.frame('B', 1, 21, target='ARRIVAL')[0]
        self.assertEqual(self.windows, [(10, 11), (20, 21)])
        self.assertEqual((a['sessionId'], a['departureCity'], a['arrivalCity']), ('A', '11', None))
        self.assertEqual((b['sessionId'], b['departureCity'], b['arrivalCity']), ('B', None, '21'))
        self.assertEqual(a['recognizedProb'], 95.0)

    def test_reset_is_local_and_repeated_reset_does_not_erase_new_frames(self):
        self.send('START_SESSION')
        self.send('START_SESSION', 'B')
        self.frame('A', 0, 10)
        self.frame('B', 0, 20)
        before_b = self.snapshot('B')
        self.assertEqual(self.send('RESET_SESSION', revision=1, target='ARRIVAL')[0]['type'], 'SESSION_RESET')
        self.frame('A', 0, 30, revision=1, target='ARRIVAL')
        before_a = self.snapshot()
        self.send('RESET_SESSION', revision=1, target='ARRIVAL')
        self.assertEqual(before_a, self.snapshot())
        self.assertEqual(before_b, self.snapshot('B'))
        result = self.frame('A', 1, 31, revision=1, target='ARRIVAL')[0]
        self.assertEqual(self.windows, [(30, 31)])
        self.assertEqual(result['revision'], 1)

    def test_bad_requests_do_not_mutate_state(self):
        self.send('START_SESSION')
        self.send('RESET_SESSION', revision=1)
        self.frame('A', 0, 10, revision=1)
        before = self.snapshot()
        cases = [
            (self.request('START_SESSION'), 'SESSION_ALREADY_STARTED'),
            (self.request('RESET_SESSION', revision=0), 'STALE_REVISION'),
            (self.request('RESET_SESSION', revision=3), 'INVALID_REVISION'),
            (self.request('RESET_SESSION', revision=1, target='ARRIVAL'), 'INVALID_REVISION'),
            (self.request('END_SESSION', revision=0), 'STALE_REVISION'),
            (self.request('END_SESSION', revision=2), 'INVALID_REVISION'),
            (self.request('KEYPOINT_FRAME', revision=0), 'STALE_REVISION'),
            (self.request('KEYPOINT_FRAME', revision=2), 'INVALID_REVISION'),
            (self.request('KEYPOINT_FRAME', revision=1, target='ARRIVAL'), 'TARGET_MISMATCH'),
            (self.request('KEYPOINT_FRAME', revision=1, frameIndex=0), 'OUT_OF_ORDER_FRAME'),
            (self.request('KEYPOINT_FRAME', revision=1, frameIndex=1, keypoints=[]), 'INVALID_KEYPOINTS'),
        ]
        for request, code in cases:
            with self.subTest(code=code, request=request):
                self.now = 5
                response = self.manager.handle(json.dumps(request))[0]
                self.assertEqual(response['errorCode'], code)
                self.assertEqual(response['sessionId'], 'A')
                self.assertEqual(self.snapshot(), before)

    def test_frame_sequence_starts_at_zero_but_allows_later_gaps(self):
        self.send('START_SESSION')
        self.assertEqual(self.frame('A', 4, 10)[0]['errorCode'], 'OUT_OF_ORDER_FRAME')
        self.frame('A', 0, 10)
        self.assertEqual(self.frame('A', 4, 11)[0]['frameIndex'], 4)

    def test_strict_keypoints_and_missing_points(self):
        self.send('START_SESSION')
        self.manager.preprocess = lambda points: tuple(points[0])
        invalid_points = [[0, 0], [None, 0, 0], [None, None, 1], [0, 0, 2],
                          [True, 0, 1], ['0', 0, 1], [0, 0, False]]
        for point in invalid_points:
            with self.subTest(point=point):
                result = self.send('KEYPOINT_FRAME', frameIndex=0, keypoints=[point] * 137)
                self.assertEqual(result[0]['errorCode'], 'INVALID_KEYPOINTS')
                self.assertEqual(len(self.manager.sessions['A'].frames), 0)
        self.send('KEYPOINT_FRAME', frameIndex=0, keypoints=[[0.5, 0.5, 0]] * 137)
        self.assertEqual(list(self.manager.sessions['A'].frames), [(None, None, 0)])
        self.send('KEYPOINT_FRAME', frameIndex=1, keypoints=[[None, None, 0]] * 137)
        self.assertEqual(self.windows[-1], ((None, None, 0), (None, None, 0)))

    def test_invalid_envelope_and_json_do_not_close_other_sessions(self):
        self.send('START_SESSION')
        cases = [('{', 'INVALID_JSON'), ('NaN', 'INVALID_JSON'), ('[]', 'INVALID_MESSAGE'),
                 (json.dumps(self.request('START_SESSION', protocolVersion=2)), 'UNSUPPORTED_VERSION'),
                 (json.dumps(self.request('START_SESSION', protocolVersion=True)), 'INVALID_MESSAGE'),
                 (json.dumps(self.request('UNKNOWN')), 'UNKNOWN_MESSAGE_TYPE'),
                 (json.dumps(self.request('END_SESSION', revision=True)), 'INVALID_MESSAGE'),
                 (json.dumps(self.request('END_SESSION', revision=9007199254740992)), 'INVALID_MESSAGE'),
                 (json.dumps(self.request('END_SESSION', sid='')), 'INVALID_MESSAGE'),
                 (json.dumps(self.request('START_SESSION', target=[])), 'INVALID_MESSAGE')]
        for raw, code in cases:
            with self.subTest(raw=raw):
                self.assertEqual(self.manager.handle(raw)[0]['errorCode'], code)
                self.assertIn('A', self.manager.sessions)
        self.assertEqual(self.frame('B', 0, 0)[0]['errorCode'], 'SESSION_NOT_FOUND')

    def test_end_only_removes_its_owner(self):
        self.send('START_SESSION')
        self.send('START_SESSION', 'B')
        self.assertEqual(self.send('END_SESSION')[0]['type'], 'SESSION_ENDED')
        self.assertEqual(set(self.manager.sessions), {'B'})
        self.assertEqual(self.frame('A', 0, 10)[0]['errorCode'], 'SESSION_NOT_FOUND')

    def test_same_id_on_different_backend_connections_is_isolated(self):
        other = SessionManager(lambda points: 99, lambda frames: ('other', 80), window_size=1, stride=1)
        other.handle(json.dumps(self.request('START_SESSION')))
        self.send('START_SESSION')
        self.frame('A', 0, 10)
        self.assertEqual(len(other.sessions['A'].frames), 0)
        self.manager.clear()
        self.assertIn('A', other.sessions)

    def test_idle_expiry_uses_server_clock_and_is_per_session(self):
        self.send('START_SESSION')
        self.now = 30
        self.send('START_SESSION', 'B')
        self.now = 119
        self.assertEqual(self.manager.expire(), [])
        self.now = 120
        expired = self.manager.expire()
        self.assertEqual([(r['sessionId'], r['errorCode']) for r in expired], [('A', 'SESSION_EXPIRED')])
        self.assertEqual(set(self.manager.sessions), {'B'})

    def test_unready_model_does_not_create_session(self):
        self.manager.ready = lambda: False
        self.assertEqual(self.send('START_SESSION')[0]['errorCode'], 'MODEL_NOT_READY')
        self.assertEqual(self.manager.sessions, {})

    def test_preprocessing_failure_keeps_buffer_unchanged(self):
        self.send('START_SESSION')
        before = self.snapshot()
        self.manager.preprocess = lambda points: None
        with self.assertLogs('realtime.sessions', level='ERROR'):
            result = self.frame('A', 0, 10)[0]
        self.assertEqual(result['errorCode'], 'INVALID_KEYPOINTS')
        self.assertEqual(self.snapshot(), before)

    def test_model_failure_is_error_and_next_session_can_still_predict(self):
        self.send('START_SESSION')
        self.frame('A', 0, 10)
        original = self.manager.predict
        def fail(frames):
            raise RuntimeError('private model path')
        self.manager.predict = fail
        with self.assertLogs('realtime.sessions', level='ERROR'):
            result = self.frame('A', 1, 11)[0]
        self.assertEqual(result['errorCode'], 'INFERENCE_FAILED')
        self.assertNotIn('private model path', json.dumps(result))
        self.manager.predict = original
        self.send('START_SESSION', 'B')
        self.frame('B', 0, 20)
        self.assertEqual(self.frame('B', 1, 21)[0]['sessionId'], 'B')

    def test_window_is_bounded_and_stride_is_per_session(self):
        self.manager.stride = 2
        self.send('START_SESSION')
        self.send('START_SESSION', 'B')
        for index in range(5):
            self.frame('A', index, index)
        self.assertEqual(self.windows, [(0, 1), (2, 3)])
        self.assertEqual(list(self.manager.sessions['A'].frames), [3, 4])
        self.assertEqual(self.manager.sessions['B'].frames_since_inference, 0)

    def test_receive_loop_expires_idle_sessions_and_cleans_up_on_disconnect(self):
        self.send('START_SESSION')
        owner = self
        class Disconnected(Exception):
            pass
        class Socket:
            def __init__(self):
                self.count = 0
                self.sent = []
            def receive(self, timeout):
                self.count += 1
                if self.count == 1:
                    owner.now = 121
                    return None  # simple-websocket receive timeout
                if self.count == 2:
                    return json.dumps(owner.request('START_SESSION', sid='B'))
                raise Disconnected()
            def send(self, raw):
                self.sent.append(json.loads(raw))
        socket = Socket()
        with self.assertRaises(Disconnected):
            serve_connection(socket, self.manager)
        self.assertEqual([r['type'] for r in socket.sent], ['ERROR', 'SESSION_STARTED'])
        self.assertEqual(socket.sent[0]['errorCode'], 'SESSION_EXPIRED')
        self.assertEqual(self.manager.sessions, {})

    def test_send_failure_also_releases_connection_sessions(self):
        owner = self
        class Socket:
            def receive(self, timeout):
                return json.dumps(owner.request('START_SESSION'))
            def send(self, raw):
                raise OSError('connection lost')
        with self.assertRaises(OSError):
            serve_connection(Socket(), self.manager)
        self.assertEqual(self.manager.sessions, {})


if __name__ == '__main__':
    unittest.main()
