package com.waynexia.aiassistant.chat.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Entity
@Table(name = "chat_messages")
public class ChatMessageEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(nullable = false, length = 30)
    private String role;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    public static ChatMessageEntity user(UUID sessionId, String content) {
        return ChatMessageEntity.builder()
                .sessionId(sessionId)
                .role("user")
                .content(content)
                .createdAt(LocalDateTime.now())
                .build();
    }

    public static ChatMessageEntity assistant(UUID sessionId, String content) {
        return ChatMessageEntity.builder()
                .sessionId(sessionId)
                .role("assistant")
                .content(content)
                .createdAt(LocalDateTime.now())
                .build();
    }
}