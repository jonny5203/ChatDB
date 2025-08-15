package main

import (
	"reflect"
	"testing"
)

func TestPredict(t *testing.T) {
	tests := []struct {
		name    string
		model   string
		data    map[string]interface{}
		want    map[string]interface{}
		wantErr bool
	}{
		{
			name:  "model1",
			model: "model1",
			data:  map[string]interface{}{"feature1": 1.0, "feature2": 2.0},
			want:  map[string]interface{}{"prediction": "predicted_value_1"},
		},
		{
			name:  "model2",
			model: "model2",
			data:  map[string]interface{}{"feature1": 3.0, "feature2": 4.0},
			want:  map[string]interface{}{"prediction": "predicted_value_2"},
		},
		{
			name:    "not found",
			model:   "unknown_model",
			data:    map[string]interface{}{"feature1": 5.0, "feature2": 6.0},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Predict(tt.model, tt.data)
			if (err != nil) != tt.wantErr {
				t.Errorf("Predict() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("Predict() = %v, want %v", got, tt.want)
			}
		})
	}
}
