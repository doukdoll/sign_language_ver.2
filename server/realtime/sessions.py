"""Connection-owned recognition sessions; no model or web framework dependency.

One manager is owned by one WebSocket receive loop. Calls are synchronous and
must not be shared across threads. The predictor receives a buffer snapshot.
"""

import json
import logging
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable


logger = logging.getLogger(__name__)
MAX_SAFE_INTEGER = 9007199254740991
REQUEST_TYPES = {"START_SESSION", "KEYPOINT_FRAME", "RESET_SESSION", "END_SESSION"}
TARGETS = {"DEPARTURE", "ARRIVAL"}


def valid_integer(value):
    return type(value) is int and 0 <= value <= MAX_SAFE_INTEGER


def finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


class ProtocolError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate_keypoints(points):
    if not isinstance(points, list) or len(points) != 137:
        raise ProtocolError("INVALID_KEYPOINTS", "keypoints must have shape (137, 3)")
    for point in points:
        if not isinstance(point, list) or len(point) != 3:
            raise ProtocolError("INVALID_KEYPOINTS", "keypoints must have shape (137, 3)")
        x, y, confidence = point
        if not finite_number(confidence) or not 0 <= confidence <= 1:
            raise ProtocolError("INVALID_KEYPOINTS", "confidence must be between 0 and 1")
        if x is None or y is None:
            if x is not None or y is not None or confidence != 0:
                raise ProtocolError("INVALID_KEYPOINTS", "missing points must be [null, null, 0]")
        elif not finite_number(x) or not finite_number(y):
            raise ProtocolError("INVALID_KEYPOINTS", "coordinates must be finite numbers")


@dataclass
class Session:
    target: str
    revision: int
    frames: deque
    last_activity: float
    last_frame_index: int = -1
    frames_since_inference: int = 0


class SessionManager:
    def __init__(self, preprocess: Callable, predict: Callable, *, window_size=128,
                 stride=5, idle_timeout=120.0, ready=lambda: True,
                 clock=time.monotonic, wall_clock=time.time):
        if type(window_size) is not int or window_size < 1:
            raise ValueError("window_size must be a positive integer")
        if type(stride) is not int or stride < 1:
            raise ValueError("stride must be a positive integer")
        if not finite_number(idle_timeout) or idle_timeout <= 0:
            raise ValueError("idle_timeout must be positive and finite")
        self.preprocess = preprocess
        self.predict = predict
        self.window_size = window_size
        self.stride = stride
        self.idle_timeout = idle_timeout
        self.ready = ready
        self.clock = clock
        self.wall_clock = wall_clock
        self.sessions: dict[str, Session] = {}

    def message(self, kind, session_id, revision, **fields):
        return {"protocolVersion": 1, "type": kind, "sessionId": session_id,
                "revision": revision, "timestamp": int(self.wall_clock() * 1000), **fields}

    def error(self, request, code, message):
        request = request if isinstance(request, dict) else {}
        session_id = request.get("sessionId")
        if not isinstance(session_id, str) or not session_id.strip():
            session_id = None
        revision = request.get("revision")
        kind = request.get("type")
        return self.message("ERROR", session_id, revision if valid_integer(revision) else None,
                            requestType=kind if isinstance(kind, str) else None,
                            errorCode=code, errorMessage=message)

    def expire(self):
        now = self.clock()
        expired = []
        for session_id, state in list(self.sessions.items()):
            if now - state.last_activity >= self.idle_timeout:
                del self.sessions[session_id]
                expired.append(self.error(
                    {"sessionId": session_id, "revision": state.revision},
                    "SESSION_EXPIRED", "session expired; open a new connection"))
        return expired

    def clear(self):
        self.sessions.clear()

    def handle(self, raw):
        replies = self.expire()
        request: Any = None
        try:
            # JSON extensions NaN/Infinity are invalid on the wire.
            def reject_constant(value):
                raise ValueError("invalid JSON constant")
            request = json.loads(raw, parse_constant=reject_constant)
        except (ValueError, TypeError, RecursionError):
            return replies + [self.error(None, "INVALID_JSON", "invalid JSON message")]
        try:
            response = self.dispatch(request)
            if response is not None:
                replies.append(response)
        except ProtocolError as error:
            replies.append(self.error(request, error.code, str(error)))
        return replies

    def dispatch(self, request):
        if not isinstance(request, dict):
            raise ProtocolError("INVALID_MESSAGE", "message must be an object")
        if type(request.get("protocolVersion")) is not int:
            raise ProtocolError("INVALID_MESSAGE", "protocolVersion must be an integer")
        if request["protocolVersion"] != 1:
            raise ProtocolError("UNSUPPORTED_VERSION", "expected protocolVersion 1")
        kind = request.get("type")
        if not isinstance(kind, str) or kind not in REQUEST_TYPES:
            raise ProtocolError("UNKNOWN_MESSAGE_TYPE", "unsupported message type")
        session_id = request.get("sessionId")
        if not isinstance(session_id, str) or not session_id.strip():
            raise ProtocolError("INVALID_MESSAGE", "backend-assigned sessionId is required")
        revision = request.get("revision")
        if not valid_integer(revision) or not valid_integer(request.get("timestamp")):
            raise ProtocolError("INVALID_MESSAGE", "revision and timestamp must be nonnegative safe integers")
        target = request.get("recognitionTarget")
        if kind != "END_SESSION" and (not isinstance(target, str) or target not in TARGETS):
            raise ProtocolError("INVALID_MESSAGE", "invalid recognitionTarget")

        state = self.sessions.get(session_id)
        if kind == "START_SESSION":
            if state is not None:
                raise ProtocolError("SESSION_ALREADY_STARTED", "use RESET_SESSION to retry")
            if revision != 0:
                raise ProtocolError("INVALID_REVISION", "start revision must be zero")
            if not self.ready():
                raise ProtocolError("MODEL_NOT_READY", "model is not ready")
            self.sessions[session_id] = Session(target, 0, deque(maxlen=self.window_size), self.clock())
            return self.message("SESSION_STARTED", session_id, 0, recognitionTarget=target)
        if state is None:
            raise ProtocolError("SESSION_NOT_FOUND", "session not found; open a new connection")
        if revision < state.revision:
            raise ProtocolError("STALE_REVISION", "request belongs to an earlier attempt")

        if kind == "RESET_SESSION":
            if revision == state.revision and revision > 0 and target == state.target:
                state.last_activity = self.clock()
            elif revision == state.revision + 1:
                self.sessions[session_id] = Session(
                    target, revision, deque(maxlen=self.window_size), self.clock())
            else:
                raise ProtocolError("INVALID_REVISION", "reset must increment revision by one")
            return self.message("SESSION_RESET", session_id, revision, recognitionTarget=target)

        if revision != state.revision:
            raise ProtocolError("INVALID_REVISION", "reset before changing revision")
        if kind == "END_SESSION":
            del self.sessions[session_id]
            return self.message("SESSION_ENDED", session_id, revision)
        if target != state.target:
            raise ProtocolError("TARGET_MISMATCH", "use RESET_SESSION to change target")
        index = request.get("frameIndex")
        if not valid_integer(index):
            raise ProtocolError("INVALID_MESSAGE", "frameIndex must be a nonnegative safe integer")
        if index <= state.last_frame_index or (state.last_frame_index == -1 and index != 0):
            raise ProtocolError("OUT_OF_ORDER_FRAME", "start at zero and increase frameIndex")
        points = request.get("keypoints")
        validate_keypoints(points)
        # Make a fresh input; never mutate the caller's frame. Confidence zero
        # means missing even if the sender supplied finite placeholder coordinates.
        points = [[x, y, c] if c > 0 else [None, None, 0] for x, y, c in points]
        try:
            feature = self.preprocess(points)
            if feature is None:
                raise ValueError("no feature")
        except Exception:
            logger.exception("Frame preprocessing failed for session %s", session_id)
            raise ProtocolError("INVALID_KEYPOINTS", "frame preprocessing failed") from None
        state.frames.append(feature)
        state.last_frame_index = index
        state.frames_since_inference += 1
        state.last_activity = self.clock()
        if len(state.frames) < self.window_size or state.frames_since_inference < self.stride:
            return None
        state.frames_since_inference = 0
        try:
            label, confidence = self.predict(tuple(state.frames))
            if not isinstance(label, str) or not label or not finite_number(confidence) or not 0 <= confidence <= 100:
                raise ValueError("invalid prediction")
        except Exception:
            logger.exception("Inference failed for session %s", session_id)
            raise ProtocolError("INFERENCE_FAILED", "model inference failed; reset to retry") from None
        return self.message("RESULT", session_id, revision, recognitionTarget=target,
                            frameIndex=index, departureCity=label if target == "DEPARTURE" else None,
                            arrivalCity=label if target == "ARRIVAL" else None,
                            recognizedProb=float(confidence))


def serve_connection(ws, manager):
    """Poll idle sessions even when no messages arrive; always release buffers.

    ConnectionClosed is intentionally propagated to the web framework adapter.
    """
    try:
        while True:
            raw = ws.receive(timeout=1)
            responses = manager.expire() if raw is None else manager.handle(raw)
            for response in responses:
                ws.send(json.dumps(response, ensure_ascii=False, allow_nan=False))
    finally:
        manager.clear()
