package com.capstone.handler;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class InferenceClientHandlerTest {
    final ObjectMapper mapper = new ObjectMapper();
    InferenceClientHandler relay;
    WebSocketSession ai, a, b;

    WebSocketSession socket(String id) {
        WebSocketSession session = mock(WebSocketSession.class);
        when(session.getId()).thenReturn(id);
        when(session.isOpen()).thenReturn(true);
        return session;
    }

    @BeforeEach void setup() {
        relay = new InferenceClientHandler(mapper);
        ai = socket("ai"); a = socket("a"); b = socket("b");
        relay.afterConnectionEstablished(ai);
    }

    ObjectNode request(String type, String id, long revision, String target) {
        ObjectNode node = mapper.createObjectNode().put("protocolVersion", 1).put("type", type)
                .put("revision", revision).put("recognitionTarget", target).put("timestamp", 1);
        if (id != null) node.put("sessionId", id);
        if ("KEYPOINT_FRAME".equals(type)) node.put("frameIndex", 0).putArray("keypoints");
        return node;
    }

    void forward(WebSocketSession fe, ObjectNode node) { relay.forward(fe, node.toString()); }
    void response(ObjectNode node) { relay.handleTextMessage(ai, new TextMessage(node.toString())); }
    void start(WebSocketSession fe, String target) {
        forward(fe, request("START_SESSION", null, 0, target));
        response(request("SESSION_STARTED", fe.getId(), 0, target));
    }
    List<JsonNode> messages(WebSocketSession socket) throws Exception {
        var captor = org.mockito.ArgumentCaptor.forClass(TextMessage.class);
        verify(socket, atLeastOnce()).sendMessage(captor.capture());
        List<JsonNode> result = new ArrayList<>();
        for (TextMessage message : captor.getAllValues()) result.add(mapper.readTree(message.getPayload()));
        return result;
    }

    @Test void assignsServerIdAndWaitsForAiAck() throws Exception {
        forward(a, request("START_SESSION", null, 0, "DEPARTURE"));
        assertEquals("a", messages(ai).get(0).path("sessionId").asText());
        verify(a, never()).sendMessage(any());
        response(request("SESSION_STARTED", "a", 0, "DEPARTURE"));
        assertEquals("SESSION_STARTED", messages(a).get(0).path("type").asText());
    }

    @Test void rejectsSpoofingWithoutForwardingOrChangingOwner() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL"); clearInvocations(ai, a, b);
        forward(a, request("RESET_SESSION", "b", 1, "ARRIVAL"));
        assertEquals("SESSION_MISMATCH", messages(a).get(0).path("errorCode").asText());
        verify(ai, never()).sendMessage(any()); verify(b, never()).sendMessage(any());
    }

    @Test void routesResultOnlyToOwnerAndPreservesFields() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL"); clearInvocations(a, b);
        ObjectNode result = request("RESULT", "b", 0, "ARRIVAL").put("frameIndex", 127)
                .put("arrivalCity", "부산역").putNull("departureCity").put("recognizedProb", 98.7);
        response(result);
        assertEquals(mapper.readTree(result.toString()), messages(b).get(0));
        verify(a, never()).sendMessage(any());
    }

    @Test void resetBlocksOldResultsAndDoesNotAffectOtherUsers() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL"); clearInvocations(a, b);
        forward(a, request("RESET_SESSION", "a", 1, "ARRIVAL"));
        response(request("RESULT", "a", 0, "DEPARTURE"));
        response(request("RESULT", "b", 0, "ARRIVAL"));
        verify(a, never()).sendMessage(any());
        assertEquals("RESULT", messages(b).get(0).path("type").asText());
        response(request("SESSION_RESET", "a", 1, "ARRIVAL"));
        assertEquals(1, messages(a).get(0).path("revision").asInt());
    }

    @Test void duplicateResetStillRelaysAcknowledgment() throws Exception {
        start(a, "DEPARTURE");
        forward(a, request("RESET_SESSION", "a", 1, "ARRIVAL"));
        response(request("SESSION_RESET", "a", 1, "ARRIVAL"));
        clearInvocations(a);
        forward(a, request("RESET_SESSION", "a", 1, "ARRIVAL"));
        response(request("SESSION_RESET", "a", 1, "ARRIVAL"));
        assertEquals("SESSION_RESET", messages(a).get(0).path("type").asText());
    }

    @Test void malformedInputReturnsErrorWithoutMutatingSession() throws Exception {
        start(a, "DEPARTURE"); clearInvocations(ai, a);
        relay.forward(a, "not json");
        forward(a, request("KEYPOINT_FRAME", "a", 0, "DEPARTURE").put("revision", "0"));
        assertEquals("INVALID_JSON", messages(a).get(0).path("errorCode").asText());
        assertEquals("INVALID_MESSAGE", messages(a).get(1).path("errorCode").asText());
        verify(ai, never()).sendMessage(any());
        forward(a, request("KEYPOINT_FRAME", "a", 0, "DEPARTURE"));
        assertEquals("KEYPOINT_FRAME", messages(ai).get(0).path("type").asText());
    }

    @Test void disconnectSendsOnlyOwnedEndIncludingPendingResetRevision() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL");
        forward(a, request("RESET_SESSION", "a", 1, "ARRIVAL")); clearInvocations(ai, a, b);
        relay.disconnect(a);
        JsonNode end = messages(ai).get(0);
        assertEquals("END_SESSION", end.path("type").asText());
        assertEquals("a", end.path("sessionId").asText());
        assertEquals(1, end.path("revision").asInt());
        response(request("RESULT", "a", 1, "ARRIVAL"));
        verify(a, never()).sendMessage(any());
        verify(ai, never()).close(any()); verify(b, never()).close(any());
    }

    @Test void aiLossNotifiesAllOwnersClearsMappingsAndIgnoresOldCallbacks() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL"); clearInvocations(a, b);
        relay.afterConnectionClosed(ai, CloseStatus.SERVER_ERROR);
        assertEquals("AI_UNAVAILABLE", messages(a).get(0).path("errorCode").asText());
        assertEquals("AI_UNAVAILABLE", messages(b).get(0).path("errorCode").asText());
        verify(a).close(any()); verify(b).close(any());
        WebSocketSession replacement = socket("new-ai"); relay.afterConnectionEstablished(replacement);
        relay.afterConnectionClosed(ai, CloseStatus.NORMAL);
        assertTrue(relay.isConnected());
        clearInvocations(a);
        response(request("RESULT", "a", 0, "DEPARTURE"));
        verify(a, never()).sendMessage(any());
    }

    @Test void expirationOnlyClosesItsOwnerEvenDuringReset() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL");
        forward(a, request("RESET_SESSION", "a", 1, "ARRIVAL")); clearInvocations(a, b);
        response(request("ERROR", "a", 0, "DEPARTURE").put("errorCode", "SESSION_EXPIRED"));
        assertEquals("SESSION_EXPIRED", messages(a).get(0).path("errorCode").asText());
        verify(a).close(any()); verify(b, never()).close(any());
    }

    @Test void endAckIsDeliveredBeforeOwnerIsRemoved() throws Exception {
        start(a, "DEPARTURE"); clearInvocations(a);
        forward(a, request("END_SESSION", "a", 0, "DEPARTURE"));
        response(request("SESSION_ENDED", "a", 0, "DEPARTURE"));
        assertEquals("SESSION_ENDED", messages(a).get(0).path("type").asText());
        verify(a).close(any()); clearInvocations(a);
        response(request("RESULT", "a", 0, "DEPARTURE"));
        verify(a, never()).sendMessage(any());
    }

    @Test void aiSendFailureIsExplicitAndDoesNotLeaveMappings() throws Exception {
        doThrow(new IOException("private detail")).when(ai).sendMessage(any());
        forward(a, request("START_SESSION", null, 0, "DEPARTURE"));
        JsonNode error = messages(a).get(0);
        assertEquals("AI_UNAVAILABLE", error.path("errorCode").asText());
        assertFalse(error.toString().contains("private detail"));
        assertFalse(relay.isConnected());
    }

    @Test void concurrentUsersNeverWriteSharedAiSocketConcurrently() throws Exception {
        start(a, "DEPARTURE"); start(b, "ARRIVAL");
        AtomicInteger writing = new AtomicInteger(), maximum = new AtomicInteger();
        doAnswer(call -> {
            maximum.accumulateAndGet(writing.incrementAndGet(), Math::max);
            try { Thread.sleep(5); } finally { writing.decrementAndGet(); }
            return null;
        }).when(ai).sendMessage(any());
        var pool = Executors.newFixedThreadPool(4);
        try {
            var tasks = new ArrayList<java.util.concurrent.Future<?>>();
            for (int index = 0; index < 20; index++) {
                final WebSocketSession fe = index % 2 == 0 ? a : b;
                tasks.add(pool.submit(() -> forward(fe, request("KEYPOINT_FRAME", fe.getId(), 0,
                        fe == a ? "DEPARTURE" : "ARRIVAL"))));
            }
            for (var task : tasks) task.get(5, TimeUnit.SECONDS);
        } finally { pool.shutdownNow(); }
        assertEquals(1, maximum.get());
    }
}
