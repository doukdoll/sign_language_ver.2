package com.capstone.dto;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

/** WebSocket-only envelope; tree validation avoids DTO scalar coercion. */
public final class RecognitionMessage {
    private RecognitionMessage() {}

    public static boolean integer(JsonNode value) {
        return value != null && value.isIntegralNumber() && value.canConvertToLong()
                && value.longValue() >= 0 && value.longValue() <= 9007199254740991L;
    }

    public static String validate(ObjectNode message) {
        if (!integer(message.get("protocolVersion")) || message.path("protocolVersion").longValue() != 1)
            return "UNSUPPORTED_VERSION";
        if (!integer(message.get("revision")) || !integer(message.get("timestamp"))) return "INVALID_MESSAGE";
        String type = message.path("type").asText();
        if (!java.util.Set.of("START_SESSION", "RESET_SESSION", "END_SESSION", "KEYPOINT_FRAME").contains(type))
            return "UNKNOWN_MESSAGE_TYPE";
        if (!"END_SESSION".equals(type) && !java.util.Set.of("DEPARTURE", "ARRIVAL")
                .contains(message.path("recognitionTarget").asText())) return "INVALID_MESSAGE";
        if ("KEYPOINT_FRAME".equals(type) && !integer(message.get("frameIndex"))) return "INVALID_MESSAGE";
        return null;
    }

    public static ObjectNode error(ObjectMapper mapper, String id, JsonNode request, String code) {
        ObjectNode error = mapper.createObjectNode();
        error.put("protocolVersion", 1).put("type", "ERROR").put("sessionId", id)
                .put("timestamp", System.currentTimeMillis()).put("errorCode", code).put("errorMessage", code);
        if (request != null && integer(request.get("revision"))) error.set("revision", request.get("revision"));
        else error.putNull("revision");
        if (request != null && request.path("type").isTextual()) error.set("requestType", request.get("type"));
        else error.putNull("requestType");
        return error;
    }
}
