"""Model-free HTTP tests: python -m unittest tests.test_http_api -v."""

import copy
import unittest

from realtime.http_api import create_app


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        self.preprocessed = []
        self.predicted = []
        self.ready = True

        def preprocess(points):
            self.preprocessed.append(copy.deepcopy(points))
            return ('feature',)

        def predict(feature):
            self.predicted.append(feature)
            return '서울', 91.5

        self.preprocess = preprocess
        self.predict = predict
        self.app = create_app(lambda points: self.preprocess(points),
                              lambda feature: self.predict(feature),
                              ready=lambda: self.ready)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.points = [[0.1, 0.2, 1.0] for _ in range(137)]

    def payload(self, target='DEPARTURE'):
        return {'recognitionTarget': target, 'keypointData': {'keypoints': self.points}}

    def post(self, payload=None):
        return self.client.post('/predict_keypoints', json=self.payload() if payload is None else payload)

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        data = response.get_json()
        self.assertEqual(set(data), {'errorCode', 'errorMessage'})
        self.assertEqual(data['errorCode'], code)
        self.assertTrue(data['errorMessage'])
        self.assertNotIn('private model path', response.get_data(as_text=True))

    def test_departure_result(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'departureCity': '서울', 'arrivalCity': None,
                                               'recognizedProb': 91.5})
        self.assertEqual(self.preprocessed, [self.points])
        self.assertEqual(self.predicted, [('feature',)])

    def test_arrival_result(self):
        response = self.post(self.payload('ARRIVAL'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'departureCity': None, 'arrivalCity': '서울',
                                               'recognizedProb': 91.5})

    def test_missing_target_preserves_legacy_departure_default(self):
        response = self.post({'keypointData': {'keypoints': self.points}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['departureCity'], '서울')
        self.assertIsNone(response.get_json()['arrivalCity'])

    def test_existing_input_formats_preserve_values_and_order(self):
        points = [[index / 137, 0.2, 1.0] for index in range(137)]
        formats = [points, {'keypoints': points},
                   {'body': points[:25], 'face': points[25:95],
                    'leftHand': points[95:116], 'rightHand': points[116:]}]
        for value in formats:
            with self.subTest(value_type=type(value).__name__):
                response = self.post({'keypointData': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.preprocessed[-1], points)

    def test_legacy_xy_and_missing_xyz_are_passed_to_preprocessing_unchanged(self):
        for point in ([0.1, 0.2], [None, None, 0], [0.1, 0.2, 0]):
            with self.subTest(point=point):
                points = [point[:] for _ in range(137)]
                self.assertEqual(self.post({'keypointData': points}).status_code, 200)
                self.assertEqual(self.preprocessed[-1], points)

    def test_invalid_json_and_non_objects_are_client_errors(self):
        for raw in ('', '{', 'null', '[]', '"text"', '0', 'true'):
            with self.subTest(raw=raw):
                response = self.client.post('/predict_keypoints', data=raw,
                                            content_type='application/json')
                self.assert_error(response, 400, 'INVALID_REQUEST')
        self.assert_error(self.client.post('/predict_keypoints', data='plain text'),
                          400, 'INVALID_REQUEST')
        self.assertEqual(self.preprocessed, [])
        self.assertEqual(self.predicted, [])

    def test_invalid_targets_do_not_reach_model(self):
        for target in (None, [], {}, True, 0, '', 'arrival', 'UNKNOWN'):
            with self.subTest(target=target):
                self.assert_error(self.post(self.payload(target)), 400, 'INVALID_REQUEST')
        self.assertEqual(self.preprocessed, [])

    def test_invalid_keypoint_wrappers_are_client_errors(self):
        for value in (None, [], 'points', 123, {}, {'keypoints': None}, {'keypoints': {}},
                      {'body': 'wrong', 'face': [], 'leftHand': [], 'rightHand': []}):
            with self.subTest(value=value):
                self.assert_error(self.post({'keypointData': value}), 400, 'INVALID_KEYPOINTS')
        self.assert_error(self.post({}), 400, 'INVALID_KEYPOINTS')
        self.assertEqual(self.preprocessed, [])

    def test_wrong_point_counts_or_mixed_shapes_are_rejected(self):
        invalid = [self.points[:136], self.points + [[0, 0, 1]],
                   [[0, 0, 1, 0]] * 137, [[0, 0]] + self.points[1:]]
        for points in invalid:
            with self.subTest(first_point=points[0], count=len(points)):
                self.assert_error(self.post({'keypointData': points}), 400, 'INVALID_KEYPOINTS')
        parts = {'body': self.points[:24], 'face': self.points[:71],
                 'leftHand': self.points[:21], 'rightHand': self.points[:21]}
        self.assert_error(self.post({'keypointData': parts}), 400, 'INVALID_KEYPOINTS')
        self.assertEqual(self.preprocessed, [])

    def test_invalid_coordinate_values_are_rejected(self):
        invalid = [[True, 0, 1], ['0', 0, 1], [0, 0, False], [0, 0, 2],
                   [0, 0, -1], [None, 0, 0], [None, None, 1],
                   [float('nan'), 0, 1], [0, float('inf'), 1], [0, 0, float('inf')],
                   [True, 0], [None, None], [float('nan'), 0]]
        for point in invalid:
            with self.subTest(point=point):
                self.assert_error(self.post({'keypointData': [point] * 137}),
                                  400, 'INVALID_KEYPOINTS')
        self.assertEqual(self.preprocessed, [])

    def test_unready_model_returns_service_unavailable(self):
        self.ready = False
        self.assert_error(self.post(), 503, 'MODEL_NOT_READY')
        self.assertEqual(self.preprocessed, [])
        self.assertEqual(self.predicted, [])

    def test_empty_preprocessing_result_is_client_error(self):
        self.preprocess = lambda points: None
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assert_error(self.post(), 400, 'INVALID_KEYPOINTS')
        self.assertEqual(self.predicted, [])

    def test_preprocessing_exception_does_not_expose_details(self):
        def fail(points):
            raise ValueError('private model path')
        self.preprocess = fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assert_error(self.post(), 400, 'INVALID_KEYPOINTS')
        self.assertEqual(self.predicted, [])

    def test_inference_exception_is_not_a_success_or_detail_leak(self):
        def fail(feature):
            raise RuntimeError('private model path')
        original = self.predict
        self.predict = fail
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assert_error(self.post(), 500, 'INFERENCE_FAILED')
        self.predict = original
        self.assertEqual(self.post().status_code, 200)

    def test_invalid_model_results_are_server_errors(self):
        invalid = [None, ('', 80), (None, 80), ('서울', True), ('서울', -1),
                   ('서울', 101), ('서울', float('nan')), ('서울', float('inf'))]
        for result in invalid:
            with self.subTest(result=result):
                self.predict = lambda feature: result
                with self.assertLogs(self.app.logger, level='ERROR'):
                    self.assert_error(self.post(), 500, 'INFERENCE_FAILED')


if __name__ == '__main__':
    unittest.main()
