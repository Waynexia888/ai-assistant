package com.waynexia.aiassistant.common.exception;

import com.waynexia.aiassistant.common.enums.ResponseCode;

public class BusinessException extends RuntimeException {

    private final ResponseCode code;

    public BusinessException(ResponseCode code, String message) {
        super(message);
        this.code = code;
    }

    public ResponseCode getCode() {
        return code;
    }
}