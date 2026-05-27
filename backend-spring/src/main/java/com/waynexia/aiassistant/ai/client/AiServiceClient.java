package com.waynexia.aiassistant.ai.client;

import com.waynexia.aiassistant.ai.dto.AiChatRequest;
import com.waynexia.aiassistant.ai.dto.AiChatResponse;
import com.waynexia.aiassistant.common.enums.ResponseCode;
import com.waynexia.aiassistant.common.exception.BusinessException;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClient;

@Component
@RequiredArgsConstructor
public class AiServiceClient {

    private final RestClient restClient;

    @Value("${ai-service.base-url}")
    private String aiServiceBaseUrl;

    public AiChatResponse chat(AiChatRequest request) {
        try {
            AiChatResponse response = restClient.post()
                    .uri(aiServiceBaseUrl + "/internal/ai/chat")
                    .body(request)
                    .retrieve()
                    .body(AiChatResponse.class);

            if (response == null || response.getAnswer() == null) {
                throw new BusinessException(
                        ResponseCode.AI_SERVICE_ERROR,
                        "AI service returned an empty response"
                );
            }

            return response;
        } catch (RestClientException ex) {
            throw new BusinessException(
                    ResponseCode.AI_SERVICE_ERROR,
                    "Failed to call AI service"
            );
        }
    }
}
