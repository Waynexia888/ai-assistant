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
@Table(name = "chat_sessions")
public class ChatSessionEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id")
    private UUID userId;

    @Column(length = 255)
    private String title;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public static ChatSessionEntity newSession() {
        LocalDateTime now = LocalDateTime.now();

        return ChatSessionEntity.builder()
                .title("New Chat")
                .createdAt(now)
                .updatedAt(now)
                .build();
    }
}