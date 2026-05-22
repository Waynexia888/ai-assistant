package com.waynexia.aiassistant.common;

import org.slf4j.MDC;

public class RequestContext {

    private static final String REQUEST_ID_KEY = "requestId";

    private RequestContext() {
        // Prevent creating object
    }

    public static String getRequestId() {
        return MDC.get(REQUEST_ID_KEY);
    }

    public static void setRequestId(String requestId) {
        MDC.put(REQUEST_ID_KEY, requestId);
    }

    public static void clear() {
        MDC.clear();
    }
}