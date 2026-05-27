package com.waynexia.aiassistant.ai.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AiChatRequest {

    @JsonProperty("session_id")
    private String sessionId;

    private String message;
}
