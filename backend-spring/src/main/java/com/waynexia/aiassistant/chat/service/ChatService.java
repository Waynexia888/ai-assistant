package com.waynexia.aiassistant.chat.service;

import com.waynexia.aiassistant.ai.client.AiServiceClient;
import com.waynexia.aiassistant.ai.dto.AiChatRequest;
import com.waynexia.aiassistant.ai.dto.AiChatResponse;
import com.waynexia.aiassistant.chat.dto.ChatRequest;
import com.waynexia.aiassistant.chat.dto.ChatResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final AiServiceClient aiServiceClient;

    public ChatResponse chat(ChatRequest request) {
        AiChatRequest aiRequest = new AiChatRequest(
                request.getSessionId(),
                request.getMessage()
        );

        AiChatResponse aiResponse = aiServiceClient.chat(aiRequest);

        return new ChatResponse(
                aiResponse.getSessionId(),
                aiResponse.getAnswer()
        );
    }
}
