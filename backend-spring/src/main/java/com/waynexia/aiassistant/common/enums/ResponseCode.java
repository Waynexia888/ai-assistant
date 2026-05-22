package com.waynexia.aiassistant.common.enums;

public enum ResponseCode {
    OK,

    VALIDATION_ERROR,
    BAD_REQUEST,
    UNAUTHORIZED,
    FORBIDDEN,
    NOT_FOUND,
    INTERNAL_ERROR,

    AI_SERVICE_ERROR,
    KNOWLEDGE_BASE_NOT_FOUND,
    URL_PROCESSING_FAILED
}