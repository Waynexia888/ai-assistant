package com.waynexia.aiassistant.chat.controller;

import com.waynexia.aiassistant.chat.dto.ChatMessageResponse;
import com.waynexia.aiassistant.chat.dto.ChatRequest;
import com.waynexia.aiassistant.chat.dto.ChatResponse;
import com.waynexia.aiassistant.chat.service.ChatService;
import com.waynexia.aiassistant.common.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping
    public ApiResponse<ChatResponse> chat(@Valid @RequestBody ChatRequest request) {
        ChatResponse response = chatService.chat(request);
        return ApiResponse.success(response);
    }

    @GetMapping("/sessions/{sessionId}/messages")
    public ApiResponse<List<ChatMessageResponse>> getMessages(@PathVariable String sessionId) {
        List<ChatMessageResponse> messages = chatService.getMessages(sessionId);
        return ApiResponse.success(messages);
    }
}
