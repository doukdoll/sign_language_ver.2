package com.capstone.handler;

import com.capstone.dto.RecognitionMessage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

@Component
public class InferenceClientHandler extends TextWebSocketHandler {
    private static final Logger log = LoggerFactory.getLogger(InferenceClientHandler.class);
    private final ObjectMapper mapper;
    private WebSocketSession ai;
    private final Map<String, Binding> clients = new HashMap<>();

    private static final class Binding {
        final WebSocketSession socket;
        long revision;
        String target;
        String awaiting = "SESSION_STARTED";
        Binding(WebSocketSession socket, String target) { this.socket = socket; this.target = target; }
    }

    public InferenceClientHandler(ObjectMapper mapper) { this.mapper = mapper; }

    // One monitor serializes AI writes, FE writes and lifecycle mutations.
    public synchronized boolean isConnected() { return ai != null && ai.isOpen(); }

    @Override
    public synchronized void afterConnectionEstablished(WebSocketSession session) {
        if (ai != null && ai != session) unavailable(ai);
        ai = session;
    }

    public synchronized void forward(WebSocketSession fe, String payload) {
        if (!fe.isOpen()) return;
        JsonNode parsed;
        try { parsed = mapper.reader().with(DeserializationFeature.FAIL_ON_TRAILING_TOKENS).readTree(payload); }
        catch (IOException e) { error(fe, null, "INVALID_JSON"); return; }
        if (!(parsed instanceof ObjectNode request)) { error(fe, null, "INVALID_MESSAGE"); return; }
        String invalid = RecognitionMessage.validate(request);
        if (invalid != null) { error(fe, request, invalid); return; }
        String type = request.path("type").asText();
        boolean start = "START_SESSION".equals(type);
        if ((start && request.has("sessionId")) || (!start && !fe.getId().equals(request.path("sessionId").asText()))) {
            error(fe, request, "SESSION_MISMATCH"); return;
        }
        Binding binding = clients.get(fe.getId());
        if (start && binding != null) { error(fe, request, "SESSION_ALREADY_STARTED"); return; }
        if (!start && binding == null) { error(fe, request, "SESSION_NOT_FOUND"); return; }
        long revision = request.path("revision").longValue();
        String target = request.path("recognitionTarget").asText();
        if (start && revision != 0) { error(fe, request, "INVALID_REVISION"); return; }
        if (!isConnected()) {
            if (ai != null) unavailable(ai);
            error(fe, request, "AI_UNAVAILABLE"); close(fe); return;
        }
        if (start) {
            binding = new Binding(fe, target);
            clients.put(fe.getId(), binding);
        } else {
            if (revision < binding.revision) { error(fe, request, "STALE_REVISION"); return; }
            boolean reset = "RESET_SESSION".equals(type);
            boolean duplicateReset = reset && binding.revision > 0 && revision == binding.revision
                    && target.equals(binding.target) && (binding.awaiting == null || "SESSION_RESET".equals(binding.awaiting));
            if (reset && !duplicateReset) {
                if (binding.awaiting != null || revision != binding.revision + 1) {
                    error(fe, request, "INVALID_REVISION"); return;
                }
                binding.revision = revision;
                binding.target = target;
                binding.awaiting = "SESSION_RESET";
            } else if (!duplicateReset && revision != binding.revision) {
                error(fe, request, "INVALID_REVISION"); return;
            }
            if (duplicateReset) binding.awaiting = "SESSION_RESET";
            if ("KEYPOINT_FRAME".equals(type)) {
                if (binding.awaiting != null) { error(fe, request, "INVALID_MESSAGE"); return; }
                if (!target.equals(binding.target)) { error(fe, request, "TARGET_MISMATCH"); return; }
            }
            if ("END_SESSION".equals(type)) binding.awaiting = "SESSION_ENDED";
        }
        request.put("sessionId", fe.getId());
        try { ai.sendMessage(new TextMessage(mapper.writeValueAsString(request))); }
        catch (IOException | RuntimeException e) { unavailable(ai); }
    }

    @Override
    public synchronized void handleTextMessage(WebSocketSession session, TextMessage message) {
        if (session != ai) return; // Ignore callbacks from a replaced AI connection.
        JsonNode response;
        try { response = mapper.readTree(message.getPayload()); }
        catch (IOException e) { log.warn("Discarding malformed AI response"); return; }
        if (response == null || !response.isObject() || !RecognitionMessage.integer(response.get("protocolVersion"))
                || response.path("protocolVersion").longValue() != 1 || !RecognitionMessage.integer(response.get("timestamp"))) return;
        Binding binding = clients.get(response.path("sessionId").asText());
        if (binding == null) return;
        if (!binding.socket.isOpen()) { disconnect(binding.socket); return; }
        String type = response.path("type").asText();
        if (!Set.of("SESSION_STARTED", "SESSION_RESET", "SESSION_ENDED", "RESULT", "ERROR").contains(type)) return;
        boolean expired = "ERROR".equals(type) && "SESSION_EXPIRED".equals(response.path("errorCode").asText());
        if (!expired && (!RecognitionMessage.integer(response.get("revision"))
                || response.path("revision").longValue() != binding.revision)) return;
        if (Set.of("SESSION_STARTED", "SESSION_RESET", "RESULT").contains(type)
                && !binding.target.equals(response.path("recognitionTarget").asText())) return;
        if ("RESULT".equals(type) && binding.awaiting != null) return;
        if (type.equals(binding.awaiting)) binding.awaiting = null;
        else if ("SESSION_STARTED".equals(type) || "SESSION_RESET".equals(type) || "SESSION_ENDED".equals(type)) return;
        send(binding.socket, response);
        boolean terminal = expired || "SESSION_ENDED".equals(type) || ("ERROR".equals(type)
                && (binding.awaiting != null || "SESSION_NOT_FOUND".equals(response.path("errorCode").asText())));
        if (terminal) {
            if (!expired && !"SESSION_ENDED".equals(type)) disconnect(binding.socket);
            else clients.remove(binding.socket.getId());
            close(binding.socket);
        }
    }

    public synchronized void disconnect(WebSocketSession fe) {
        Binding binding = clients.remove(fe.getId());
        if (binding == null || !isConnected()) return;
        ObjectNode end = mapper.createObjectNode();
        end.put("protocolVersion", 1).put("type", "END_SESSION").put("sessionId", fe.getId())
                .put("revision", binding.revision).put("timestamp", System.currentTimeMillis());
        try { ai.sendMessage(new TextMessage(mapper.writeValueAsString(end))); }
        catch (IOException | RuntimeException e) { unavailable(ai); }
    }

    private void error(WebSocketSession fe, JsonNode request, String code) {
        send(fe, RecognitionMessage.error(mapper, fe.getId(), request, code));
    }

    private void send(WebSocketSession fe, JsonNode message) {
        try { if (fe.isOpen()) fe.sendMessage(new TextMessage(mapper.writeValueAsString(message))); }
        catch (IOException | RuntimeException e) { disconnect(fe); close(fe); }
    }

    private void close(WebSocketSession socket) {
        try { if (socket.isOpen()) socket.close(CloseStatus.NORMAL); }
        catch (IOException | RuntimeException e) { log.warn("WebSocket close failed: {}", socket.getId()); }
    }

    private void unavailable(WebSocketSession failed) {
        if (failed == null || failed != ai) return;
        ai = null;
        var affected = java.util.List.copyOf(clients.values());
        clients.clear();
        for (Binding binding : affected) {
            ObjectNode request = mapper.createObjectNode().put("revision", binding.revision);
            error(binding.socket, request, "AI_UNAVAILABLE");
            close(binding.socket);
        }
        close(failed);
    }

    @Override
    public synchronized void afterConnectionClosed(WebSocketSession session, CloseStatus status) { unavailable(session); }

    @Override
    public synchronized void handleTransportError(WebSocketSession session, Throwable exception) { unavailable(session); }
}
