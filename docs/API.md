# ChatDB API Documentation

## Base URLs

- **Training Orchestrator**: `http://localhost:8000`
- **Model Registry**: `http://localhost:8080`
- **Query Parser**: `http://localhost:8082`
- **ML Engine**: `http://localhost:8083`
- **Test Service**: `http://localhost:8001`

## Training Orchestrator Service

### Create Training Job
Creates a new ML model training job.

**Endpoint**: `POST /jobs`

**Request Body**:
```json
{
  "model_name": "string",
  "dataset_location": "string",
  "cpu_request": 1
}
```

**Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "model_name": "sentiment-classifier",
  "dataset_location": "s3://datasets/sentiment.csv",
  "status": "pending",
  "cpu_request": 2
}
```

**Status Codes**:
- `201`: Job created successfully
- `400`: Invalid request body
- `503`: Service unavailable (queue full)

---

### Get Training Job Status
Retrieves the current status of a training job.

**Endpoint**: `GET /jobs/{job_id}`

**Path Parameters**:
- `job_id` (string, required): UUID of the training job

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "model_name": "sentiment-classifier",
  "dataset_location": "s3://datasets/sentiment.csv",
  "status": "completed",
  "cpu_request": 2,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:45:00Z"
}
```

**Status Values**:
- `pending`: Job queued, waiting for resources
- `in_progress`: Job currently executing
- `completed`: Job finished successfully
- `failed`: Job failed with errors
- `cancelled`: Job cancelled by user

**Status Codes**:
- `200`: Job found
- `404`: Job not found

---

### Health Check
Service health status endpoint.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "ok",
  "service": "training-orchestrator",
  "version": "1.0.0",
  "database": "connected",
  "kafka": "connected"
}
```

## Model Registry Service

### Upload Model
Uploads a trained model to the registry.

**Endpoint**: `POST /models/upload`

**Request** (multipart/form-data):
- `model_file` (file, required): Model binary file
- `metadata` (JSON, required): Model metadata

**Metadata Structure**:
```json
{
  "name": "sentiment-classifier",
  "version": "1.0.0",
  "framework": "tensorflow",
  "description": "BERT-based sentiment analysis",
  "metrics": {
    "accuracy": 0.95,
    "f1_score": 0.93
  },
  "tags": ["nlp", "sentiment", "production"]
}
```

**Response** (201 Created):
```json
{
  "model_id": "model_550e8400",
  "name": "sentiment-classifier",
  "version": "1.0.0",
  "s3_path": "s3://models/sentiment-classifier/v1.0.0",
  "created_at": "2024-01-15T10:45:00Z"
}
```

---

### Download Model
Downloads a model from the registry.

**Endpoint**: `GET /models/{model_id}/download`

**Path Parameters**:
- `model_id` (string, required): Model identifier

**Response**: Binary model file

**Headers**:
- `Content-Type`: `application/octet-stream`
- `Content-Disposition`: `attachment; filename="model.pkl"`

---

### Get Model Metadata
Retrieves metadata for a specific model.

**Endpoint**: `GET /models/{model_id}/metadata`

**Response** (200 OK):
```json
{
  "model_id": "model_550e8400",
  "name": "sentiment-classifier",
  "version": "1.0.0",
  "framework": "tensorflow",
  "description": "BERT-based sentiment analysis",
  "metrics": {
    "accuracy": 0.95,
    "f1_score": 0.93,
    "precision": 0.94,
    "recall": 0.92
  },
  "tags": ["nlp", "sentiment", "production"],
  "created_at": "2024-01-15T10:45:00Z",
  "updated_at": "2024-01-15T10:45:00Z",
  "s3_path": "s3://models/sentiment-classifier/v1.0.0",
  "file_size": 524288000,
  "checksum": "sha256:abcdef123456..."
}
```

---

### List Models
Lists all models with optional filtering.

**Endpoint**: `GET /models`

**Query Parameters**:
- `name` (string, optional): Filter by model name
- `tag` (string, optional): Filter by tag
- `framework` (string, optional): Filter by framework
- `limit` (integer, optional): Max results (default: 20)
- `offset` (integer, optional): Pagination offset

**Response** (200 OK):
```json
{
  "models": [
    {
      "model_id": "model_550e8400",
      "name": "sentiment-classifier",
      "version": "1.0.0",
      "framework": "tensorflow",
      "tags": ["nlp", "sentiment"],
      "created_at": "2024-01-15T10:45:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### Update Model Metadata
Updates metadata for an existing model.

**Endpoint**: `PATCH /models/{model_id}/metadata`

**Request Body**:
```json
{
  "description": "Updated description",
  "tags": ["nlp", "sentiment", "v2"],
  "metrics": {
    "accuracy": 0.96
  }
}
```

**Response** (200 OK): Updated model metadata

---

### Delete Model
Removes a model from the registry.

**Endpoint**: `DELETE /models/{model_id}`

**Response** (204 No Content): Model deleted successfully

**Status Codes**:
- `204`: Model deleted
- `404`: Model not found
- `409`: Model in use (cannot delete)

## Query Parser Service

### Parse Query
Parses natural language queries into structured database operations.

**Endpoint**: `POST /parse`

**Request Body**:
```json
{
  "query": "Show me all customers who purchased items last month",
  "context": {
    "database": "sales_db",
    "user_id": "user123"
  }
}
```

**Response** (200 OK):
```json
{
  "parsed_query": {
    "type": "SELECT",
    "table": "customers",
    "joins": [
      {
        "table": "orders",
        "on": "customers.id = orders.customer_id"
      }
    ],
    "conditions": [
      {
        "field": "orders.created_at",
        "operator": "BETWEEN",
        "value": ["2024-01-01", "2024-01-31"]
      }
    ],
    "sql": "SELECT * FROM customers JOIN orders ON customers.id = orders.customer_id WHERE orders.created_at BETWEEN '2024-01-01' AND '2024-01-31'"
  },
  "confidence": 0.92,
  "alternatives": []
}
```

---

### Validate Query
Validates a parsed query against the database schema.

**Endpoint**: `POST /validate`

**Request Body**:
```json
{
  "sql": "SELECT * FROM customers",
  "database": "sales_db"
}
```

**Response** (200 OK):
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Query may return large dataset"]
}
```

## ML Engine Service

### Train Model
Initiates model training with specified parameters.

**Endpoint**: `POST /train`

**Request Body**:
```json
{
  "model_type": "classification",
  "algorithm": "random_forest",
  "dataset_path": "s3://datasets/train.csv",
  "parameters": {
    "n_estimators": 100,
    "max_depth": 10,
    "random_state": 42
  },
  "validation_split": 0.2
}
```

**Response** (202 Accepted):
```json
{
  "training_id": "train_123456",
  "status": "started",
  "estimated_time": "15 minutes"
}
```

---

### Get Training Status
Monitors ongoing training progress.

**Endpoint**: `GET /train/{training_id}/status`

**Response** (200 OK):
```json
{
  "training_id": "train_123456",
  "status": "in_progress",
  "progress": 75,
  "current_epoch": 15,
  "total_epochs": 20,
  "metrics": {
    "loss": 0.234,
    "accuracy": 0.89
  }
}
```

---

### Predict
Makes predictions using a trained model.

**Endpoint**: `POST /predict`

**Request Body**:
```json
{
  "model_id": "model_550e8400",
  "input_data": {
    "text": "This product is amazing!"
  }
}
```

**Response** (200 OK):
```json
{
  "prediction": "positive",
  "confidence": 0.95,
  "probabilities": {
    "positive": 0.95,
    "negative": 0.03,
    "neutral": 0.02
  },
  "model_version": "1.0.0"
}
```

---

### Batch Predict
Processes multiple predictions in a single request.

**Endpoint**: `POST /predict/batch`

**Request Body**:
```json
{
  "model_id": "model_550e8400",
  "input_data": [
    {"text": "Great service!"},
    {"text": "Terrible experience"},
    {"text": "It's okay"}
  ]
}
```

**Response** (200 OK):
```json
{
  "predictions": [
    {
      "index": 0,
      "prediction": "positive",
      "confidence": 0.98
    },
    {
      "index": 1,
      "prediction": "negative",
      "confidence": 0.91
    },
    {
      "index": 2,
      "prediction": "neutral",
      "confidence": 0.76
    }
  ],
  "model_version": "1.0.0",
  "processing_time": 0.234
}
```

## Common Headers

All API requests should include:

```http
Content-Type: application/json
Accept: application/json
X-Request-ID: <unique-request-id>
```

For authenticated endpoints (future implementation):
```http
Authorization: Bearer <jwt-token>
```

## Error Responses

All services use consistent error response format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found",
    "details": {
      "resource_type": "model",
      "resource_id": "model_123"
    },
    "request_id": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `CONFLICT` | 409 | Resource conflict |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily down |

## Rate Limiting

API rate limits (when implemented):
- 100 requests per minute for regular endpoints
- 10 requests per minute for training endpoints
- 1000 requests per minute for prediction endpoints

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## Pagination

List endpoints support pagination:

**Request**:
```
GET /models?limit=20&offset=40
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 40,
    "has_next": true,
    "has_previous": true
  }
}
```

## Webhooks (Future)

Services will support webhooks for async operations:

```json
{
  "webhook_url": "https://your-service.com/webhook",
  "events": ["training.completed", "training.failed"],
  "secret": "webhook_secret_key"
}
```

## SDK Examples

### Python
```python
import requests

# Submit training job
response = requests.post(
    "http://localhost:8000/jobs",
    json={
        "model_name": "classifier",
        "dataset_location": "s3://data/train.csv",
        "cpu_request": 2
    }
)
job = response.json()
print(f"Job ID: {job['id']}")
```

### JavaScript
```javascript
// Make prediction
const response = await fetch('http://localhost:8083/predict', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model_id: 'model_123',
    input_data: { text: 'Sample text' }
  })
});
const result = await response.json();
console.log(`Prediction: ${result.prediction}`);
```

### cURL
```bash
# Check service health
curl -X GET http://localhost:8000/health

# Upload model
curl -X POST http://localhost:8080/models/upload \
  -F "model_file=@model.pkl" \
  -F 'metadata={"name":"my_model","version":"1.0"}'
```