package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func TestMetrics(t *testing.T) {
	// Reset metrics
	predictionLatency.Reset()
	cpuUsage.Set(0)
	memoryUsage.Set(0)

	// Record some metrics
	predictionLatency.WithLabelValues("model1").Observe(0.1)
	predictionLatency.WithLabelValues("model2").Observe(0.2)
	cpuUsage.Set(50)
	memoryUsage.Set(1024)

	// Create a request to the /metrics endpoint
	req, err := http.NewRequest("GET", "/metrics", nil)
	if err != nil {
		t.Fatal(err)
	}

	// Create a ResponseRecorder to record the response
	rr := httptest.NewRecorder()
	handler := promhttp.Handler()

	// Serve the request
	handler.ServeHTTP(rr, req)

	// Check the status code
	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusOK)
	}

	// Check the body
	body := rr.Body.String()
	if !strings.Contains(body, "prediction_latency_seconds_bucket{model=\"model1\",le=\"+Inf\"} 1") {
			t.Errorf("body does not contain prediction_latency_seconds_bucket for model1")
		}
		if !strings.Contains(body, "prediction_latency_seconds_bucket{model=\"model2\",le=\"+Inf\"} 1") {
			t.Errorf("body does not contain prediction_latency_seconds_bucket for model2")
		}
	if !strings.Contains(body, "cpu_usage_percent 50") {
		t.Errorf("body does not contain cpu_usage_percent")
	}
	if !strings.Contains(body, "memory_usage_bytes 1024") {
		t.Errorf("body does not contain memory_usage_bytes")
	}
}
