package com.waynexia.aiassistant.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class AiChatResponse {

    @JsonProperty("session_id")
    private String sessionId;

    private String answer;
}
