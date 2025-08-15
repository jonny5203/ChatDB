package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

const (
	modelRegistryURL = "http://model-registry:8080"
)

type Model struct {
	Name    string `json:"name"`
	Version string `json:"version"`
	Path    string `json:"path"`
}

var getModelFromRegistry = func(modelName string) (*Model, error) {
	resp, err := http.Get(fmt.Sprintf("%s/models/%s", modelRegistryURL, modelName))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("model not found: %s", modelName)
	}

	var model Model
	if err := json.NewDecoder(resp.Body).Decode(&model); err != nil {
		return nil, err
	}

	return &model, nil
}