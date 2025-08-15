package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthHandler(t *testing.T) {
	req, err := http.NewRequest("GET", "/health", nil)
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	handler := http.HandlerFunc(healthHandler)

	handler.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusOK)
	}

	expected := `{"status": "ok"}`
	if rr.Body.String() != expected {
		t.Errorf("handler returned unexpected body: got %v want %v",
			rr.Body.String(), expected)
	}
}

func TestPredictHandler(t *testing.T) {
	// Mock getModelFromRegistry
	originalGetModelFromRegistry := getModelFromRegistry
	getModelFromRegistry = func(modelName string) (*Model, error) {
		return &Model{Name: "model1", Version: "1.0", Path: "/models/model1"}, nil
	}
	defer func() { getModelFromRegistry = originalGetModelFromRegistry }()

	requestBody := PredictionRequest{
		ModelName: "model1",
		Data:      map[string]interface{}{"feature1": 1.0},
	}
	body, _ := json.Marshal(requestBody)

	req, err := http.NewRequest("POST", "/predict", bytes.NewBuffer(body))
	if err != nil {
		t.Fatal(err)
	}

	rr := httptest.NewRecorder()
	handler := http.HandlerFunc(predictHandler)

	handler.ServeHTTP(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v",
			status, http.StatusOK)
	}

	var response map[string]interface{}
	if err := json.NewDecoder(rr.Body).Decode(&response); err != nil {
		t.Fatal(err)
	}

	if response["prediction"] != "predicted_value_1" {
		t.Errorf("handler returned unexpected prediction: got %v want %v",
			response["prediction"], "predicted_value_1")
	}
}
