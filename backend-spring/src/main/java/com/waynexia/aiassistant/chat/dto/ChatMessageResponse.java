package com.waynexia.aiassistant.chat.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class ChatMessageResponse {

    private UUID id;

    private String role;

    private String content;

    private LocalDateTime createdAt;
}
