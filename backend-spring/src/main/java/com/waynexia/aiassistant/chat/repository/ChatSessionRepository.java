package com.waynexia.aiassistant.chat.repository;

import com.waynexia.aiassistant.chat.entity.ChatSessionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

import java.util.UUID;

public interface ChatSessionRepository extends JpaRepository<ChatSessionEntity, UUID> {

    @Modifying
    @Query(value = """
            UPDATE chat_sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = :sessionId
            """, nativeQuery = true)
    void touch(UUID sessionId);
}