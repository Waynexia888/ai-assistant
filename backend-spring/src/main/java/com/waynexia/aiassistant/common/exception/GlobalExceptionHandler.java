package com.waynexia.aiassistant.common.exception;

import com.waynexia.aiassistant.common.ApiResponse;
import com.waynexia.aiassistant.common.FieldErrorResponse;
import com.waynexia.aiassistant.common.enums.ResponseCode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.List;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * Handle custom business exceptions.
     *
     * Example:
     * throw new BusinessException(ResponseCode.KNOWLEDGE_BASE_NOT_FOUND, "Knowledge base not found");
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<Void>> handleBusinessException(BusinessException ex) {
        log.warn("Business exception: code={}, message={}", ex.getCode(), ex.getMessage());

        return ResponseEntity
                .status(toHttpStatus(ex.getCode()))
                .body(ApiResponse.error(ex.getCode(), ex.getMessage()));
    }

    /**
     * Handle request body validation errors.
     *
     * Example:
     * @NotBlank
     * @Size
     * @NotNull
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidationException(
            MethodArgumentNotValidException ex
    ) {
        List<FieldErrorResponse> errors = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(this::toFieldErrorResponse)
                .toList();

        log.warn("Validation failed: {}", errors);

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ApiResponse.validationError("Invalid request body", errors));
    }

    /**
     * Handle illegal argument errors.
     *
     * Example:
     * throw new IllegalArgumentException("Invalid knowledge base id");
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgumentException(
            IllegalArgumentException ex
    ) {
        log.warn("Illegal argument: {}", ex.getMessage());

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ApiResponse.error(ResponseCode.BAD_REQUEST, ex.getMessage()));
    }

    /**
     * Fallback handler.
     *
     * Any unexpected exception will be handled here.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneralException(Exception ex) {
        log.error("Unexpected system error", ex);

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(
                        ResponseCode.INTERNAL_ERROR,
                        "Internal server error"
                ));
    }

    private FieldErrorResponse toFieldErrorResponse(FieldError error) {
        return new FieldErrorResponse(
                error.getField(),
                error.getDefaultMessage()
        );
    }

    private HttpStatus toHttpStatus(ResponseCode code) {
        return switch (code) {
            case VALIDATION_ERROR, BAD_REQUEST -> HttpStatus.BAD_REQUEST;
            case UNAUTHORIZED -> HttpStatus.UNAUTHORIZED;
            case FORBIDDEN -> HttpStatus.FORBIDDEN;
            case NOT_FOUND, CHAT_SESSION_NOT_FOUND, KNOWLEDGE_BASE_NOT_FOUND -> HttpStatus.NOT_FOUND;
            case AI_SERVICE_ERROR, URL_PROCESSING_FAILED, INTERNAL_ERROR -> HttpStatus.INTERNAL_SERVER_ERROR;
            default -> HttpStatus.INTERNAL_SERVER_ERROR;
        };
    }
}
