package main

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	predictionLatency = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "prediction_latency_seconds",
			Help:    "Latency of predictions.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"model"},
	)

	cpuUsage = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "cpu_usage_percent",
			Help: "Current CPU usage percentage.",
		},
	)

	memoryUsage = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "memory_usage_bytes",
			Help: "Current memory usage in bytes.",
		},
	)
)
