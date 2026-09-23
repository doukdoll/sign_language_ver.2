"""HTTP request boundary, independently testable without a model or camera."""

import time

from flask import Flask, jsonify, request

from realtime.sessions import ProtocolError, TARGETS, finite_number, validate_keypoints


BODY_PART_LENGTHS = {'body': 25, 'face': 70, 'leftHand': 21, 'rightHand': 21}


def extract_keypoints(data):
    """Accept existing flat/wrapped/split inputs, without changing preprocessing."""
    points = data.get('keypointData')
    if isinstance(points, dict):
        if 'keypoints' in points:
            points = points['keypoints']
        else:
            combined = []
            for part, length in BODY_PART_LENGTHS.items():
                values = points.get(part)
                if not isinstance(values, list) or len(values) != length:
                    raise ProtocolError('INVALID_KEYPOINTS', f'{part} must contain {length} points')
                combined.extend(values)
            points = combined

    if not isinstance(points, list) or len(points) != 137:
        raise ProtocolError('INVALID_KEYPOINTS', 'keypoints must have shape (137, 2) or (137, 3)')
    if all(isinstance(point, list) and len(point) == 2 for point in points):
        if not all(finite_number(value) for point in points for value in point):
            raise ProtocolError('INVALID_KEYPOINTS', 'coordinates must be finite numbers')
    else:
        validate_keypoints(points)
    return points


def create_app(preprocess, predict_frame, *, ready=lambda: True):
    """Build the HTTP adapter with production preprocessing/inference callbacks."""
    app = Flask(__name__)
    app.json.ensure_ascii = False

    def error(code, message, status):
        return jsonify(errorCode=code, errorMessage=message), status

    @app.post('/predict_keypoints')
    def http_predict_keypoints():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error('INVALID_REQUEST', 'request body must be a JSON object', 400)
        # Old clients omitted this field; preserve their departure default.
        target = data.get('recognitionTarget', 'DEPARTURE')
        if not isinstance(target, str) or target not in TARGETS:
            return error('INVALID_REQUEST', 'invalid recognitionTarget', 400)
        try:
            points = extract_keypoints(data)
        except ProtocolError as exc:
            return error(exc.code, str(exc), 400)

        if not ready():
            return error('MODEL_NOT_READY', 'model is not ready', 503)
        try:
            feature = preprocess(points)
            if feature is None:
                raise ValueError('no feature')
        except Exception:
            app.logger.exception('HTTP keypoint preprocessing failed')
            return error('INVALID_KEYPOINTS', 'frame preprocessing failed', 400)

        try:
            start = time.perf_counter()
            label, confidence = predict_frame(feature)
            if (not isinstance(label, str) or not label
                    or not finite_number(confidence) or not 0 <= confidence <= 100):
                raise ValueError('invalid prediction')
        except Exception:
            app.logger.exception('HTTP model inference failed')
            return error('INFERENCE_FAILED', 'model inference failed', 500)

        app.logger.info('HTTP prediction: %s (%.1f%%), %.1f ms',
                        label, confidence, (time.perf_counter() - start) * 1000)
        return jsonify(departureCity=label if target == 'DEPARTURE' else None,
                       arrivalCity=label if target == 'ARRIVAL' else None,
                       recognizedProb=float(confidence))

    return app
