package com.waynexia.aiassistant.chat.repository;

import com.waynexia.aiassistant.chat.entity.ChatMessageEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.UUID;

public interface ChatMessageRepository extends JpaRepository<ChatMessageEntity, UUID> {

    @Query(value = """
            SELECT *
            FROM chat_messages
            WHERE session_id = :sessionId
            ORDER BY created_at DESC
            LIMIT :limit
            """, nativeQuery = true)
    List<ChatMessageEntity> findRecentMessagesDesc(UUID sessionId, int limit);
}