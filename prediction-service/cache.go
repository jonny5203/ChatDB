package main

import "sync"

type ModelCache struct {
	cache map[string]*Model
	mutex sync.RWMutex
}

func NewModelCache() *ModelCache {
	return &ModelCache{
		cache: make(map[string]*Model),
	}
}

func (mc *ModelCache) Get(modelName string) (*Model, bool) {
	mc.mutex.RLock()
	defer mc.mutex.RUnlock()
	model, found := mc.cache[modelName]
	return model, found
}

func (mc *ModelCache) Set(modelName string, model *Model) {
	mc.mutex.Lock()
	defer mc.mutex.Unlock()
	mc.cache[modelName] = model
}
