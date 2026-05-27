package com.waynexia.aiassistant.chat.service;

import com.waynexia.aiassistant.ai.client.AiServiceClient;
import com.waynexia.aiassistant.ai.dto.AiChatMessage;
import com.waynexia.aiassistant.ai.dto.AiChatRequest;
import com.waynexia.aiassistant.ai.dto.AiChatResponse;
import com.waynexia.aiassistant.chat.dto.ChatRequest;
import com.waynexia.aiassistant.chat.dto.ChatResponse;
import com.waynexia.aiassistant.chat.entity.ChatMessageEntity;
import com.waynexia.aiassistant.chat.entity.ChatSessionEntity;
import com.waynexia.aiassistant.chat.repository.ChatMessageRepository;
import com.waynexia.aiassistant.chat.repository.ChatSessionRepository;
import com.waynexia.aiassistant.common.enums.ResponseCode;
import com.waynexia.aiassistant.common.exception.BusinessException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final AiServiceClient aiServiceClient;
    private final ChatSessionRepository chatSessionRepository;
    private final ChatMessageRepository chatMessageRepository;

    @Transactional
    public ChatResponse chat(ChatRequest request) {
        UUID sessionId = resolveSessionId(request.getSessionId());
        String sessionIdText = sessionId.toString();

        // 1. 查询最近N条历史消息
        List<ChatMessageEntity> historyMessages = chatMessageRepository.findRecentMessagesDesc(sessionId, 20);
        Collections.reverse(historyMessages);

        // 2. 转成ai-service 需要的history
        List<AiChatMessage> history = historyMessages.stream()
                .map(msg -> new AiChatMessage(msg.getRole(), msg.getContent()))
                .toList();

        // 3. 保存当前的user message
        chatMessageRepository.save(ChatMessageEntity.user(sessionId, request.getMessage()));

        // 4. 调 ai-service
        AiChatRequest aiRequest = new AiChatRequest(
                sessionIdText,
                request.getMessage(),
                history
        );

        AiChatResponse aiResponse = aiServiceClient.chat(aiRequest);

        // 5. 保存assistant answer
        chatMessageRepository.save(ChatMessageEntity.assistant(sessionId, aiResponse.getAnswer()));

        // 6. 更新session updated_at
        chatSessionRepository.touch(sessionId);

        return new ChatResponse(
                sessionIdText,
                aiResponse.getAnswer()
        );
    }

    private UUID resolveSessionId(String sessionIdText) {
        if (isNewSessionMarker(sessionIdText)) {
            return createSession();
        }

        try {
            UUID sessionId = UUID.fromString(sessionIdText);

            if (chatSessionRepository.existsById(sessionId)) {
                return sessionId;
            }

            throw new BusinessException(
                    ResponseCode.CHAT_SESSION_NOT_FOUND,
                    "Chat session not found"
            );
        } catch (IllegalArgumentException ex) {
            throw new BusinessException(
                    ResponseCode.BAD_REQUEST,
                    "Invalid sessionId"
            );
        }
    }

    private boolean isNewSessionMarker(String sessionIdText) {
        return sessionIdText == null
                || sessionIdText.isBlank()
                || "default".equalsIgnoreCase(sessionIdText);
    }

    private UUID createSession() {
        ChatSessionEntity newSession = ChatSessionEntity.newSession();
        ChatSessionEntity savedSession = chatSessionRepository.save(newSession);

        return savedSession.getId();
    }
}
