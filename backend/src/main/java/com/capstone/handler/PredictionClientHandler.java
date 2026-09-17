package com.capstone.handler;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

/** FE adapter; ownership, lifecycle and shared AI writes live in one relay. */
@Component
public class PredictionClientHandler extends TextWebSocketHandler {
    private final InferenceClientHandler inference;

    public PredictionClientHandler(InferenceClientHandler inference) { this.inference = inference; }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        inference.forward(session, message.getPayload());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        inference.disconnect(session);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        inference.disconnect(session);
        if (session.isOpen()) session.close(CloseStatus.SERVER_ERROR);
    }
}
