package com.waynexia.aiassistant.common;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.waynexia.aiassistant.common.enums.ResponseCode;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;



@JsonInclude(JsonInclude.Include.NON_NULL)
@Data
@NoArgsConstructor
@AllArgsConstructor(access = AccessLevel.PRIVATE)
public class ApiResponse<T> {

    private boolean success;
    private String code;
    private String message;
    private T data;
    private List<FieldErrorResponse> errors;
    private String requestId;
    private Instant timestamp;

    // --------------------- Success Response ---------------------

    public static <T> ApiResponse<T> success(T data) {
        return success(data, "Success");
    }

    public static <T> ApiResponse<T> success(T data, String message) {
        return new ApiResponse<>(
                true,
                ResponseCode.OK.name(),
                message,
                data,
                null,
                getRequestId(),
                Instant.now()
        );
    }

    // --------------------- Error Response ---------------------

    public static <T> ApiResponse<T> error(ResponseCode code, String message) {
        return new ApiResponse<>(
                false,
                code.name(),
                message,
                null,
                null,
                getRequestId(),
                Instant.now()
        );
    }

    public static <T> ApiResponse<T> error(
            ResponseCode code,
            String message,
            List<FieldErrorResponse> errors
    ) {
        return new ApiResponse<>(
                false,
                code.name(),
                message,
                null,
                errors,
                getRequestId(),
                Instant.now()
        );
    }

    public static <T> ApiResponse<T> validationError(
            String message,
            List<FieldErrorResponse> errors
    ) {
        return new ApiResponse<>(
                false,
                ResponseCode.VALIDATION_ERROR.name(),
                message,
                null,
                errors,
                getRequestId(),
                Instant.now()
        );
    }

    private static String getRequestId() {
        return RequestContext.getRequestId();
    }
}
