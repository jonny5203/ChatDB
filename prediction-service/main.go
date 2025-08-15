package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"runtime"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var modelCache = NewModelCache()

func healthHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "{\"status\": \"ok\"}")
}

type PredictionRequest struct {
	ModelName string                 `json:"model_name"`
	Data      map[string]interface{} `json:"data"`
}

func predictHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	var req PredictionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		fmt.Fprintf(w, "Error decoding request: %v", err)
		return
	}

	// Get model from cache or registry
	model, found := modelCache.Get(req.ModelName)
	if !found {
		var err error
		model, err = getModelFromRegistry(req.ModelName)
		if err != nil {
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprintf(w, "Error getting model from registry: %v", err)
			return
		}
		modelCache.Set(req.ModelName, model)
	}

	// Make prediction
	prediction, err := Predict(model.Name, req.Data)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprintf(w, "Error making prediction: %v", err)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(prediction)
}

func recordMetrics() {
	go func() {
		for {
			var m runtime.MemStats
			runtime.ReadMemStats(&m)
			memoryUsage.Set(float64(m.Alloc))
			time.Sleep(2 * time.Second)
		}
	}()
}

func main() {
	if os.Getenv("ENABLE_PERFORMANCE_MONITORING") == "true" {
		recordMetrics()
		http.Handle("/metrics", promhttp.Handler())
	}

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/predict", predictHandler)

	fmt.Println("Server listening on port 8080")
	http.ListenAndServe(":8080", nil)
}
