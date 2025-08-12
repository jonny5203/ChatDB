# MindsDB Clone - Product Requirements Document (PRD) v2

## 1. Goals and Background Context
The primary goal is to build a portfolio-ready, cloud-native version of MindsDB using a modern microservices architecture. The platform will enable users to query machine learning models using SQL syntax. While the initial MVP will focus on the e-commerce domain to demonstrate core capabilities, the underlying platform is designed to be domain-agnostic for future expansion.

## 2. High-Level Requirements
*(The detailed list of Functional and Non-Functional Requirements, including the use of microservices, Kubernetes, Kafka, a polyglot backend, and support for stream and batch data.)*

## 3. Epic Plan

### Epic 1: API Gateway Implementation
**Goal:** Build, test, and deploy the core API Gateway service, including routing, JWT validation, and federated IAM with Okta/Keycloak.
* **1.1:** Basic Service Scaffolding
* **1.2:** Request Routing
* **1.3:** Federated Authentication (IAM)
* **1.4:** JWT Validation & Authorization

### Epic 2: Query Parser Implementation
**Goal:** Build, test, and deploy the Query Parser service, including handling standard SQL, custom ML extensions, validation, and execution plan generation.
* **2.1:** Basic Service Scaffolding
* **2.2:** Standard SQL Parsing
* **2.3:** Custom ML Syntax Parsing
* **2.4:** Query Validation and Error Handling

### Epic 3: ML Engine Implementation
**Goal:** Build, test, and deploy the ML Engine service, including the complete model training pipeline with advanced AutoML.
* **3.1:** Basic Service Scaffolding
* **3.2:** Data Preprocessing and Feature Engineering
* **3.3:** AutoML Algorithm Selection
* **3.4:** Model Training and Evaluation Pipeline

### Epic 4: Database Connector Implementation
**Goal:** Build, test, and deploy the Database Connector service, perfecting connections for PostgreSQL, MySQL, and MongoDB.
* **4.1:** Basic Service Scaffolding
* **4.2:** PostgreSQL and MySQL Connection Management
* **4.3:** MongoDB Connection Management
* **4.4:** Schema Introspection

### Epic 5: Model Registry Implementation
**Goal:** Build, test, and deploy the Model Registry service, including model storage on AWS S3, metadata management, and versioning.
* **5.1:** Basic Service Scaffolding
* **5.2:** S3 Integration for Model Storage
* **5.3:** Model Metadata Management
* **5.4:** Model Versioning

### Epic 6: Training Orchestrator Implementation
**Goal:** Build, test, and deploy the Training Orchestrator service, including job queuing and CPU-only resource management.
* **6.1:** Basic Service Scaffolding
* **6.2:** Training Job Queuing
* **6.3:** Training Workflow Orchestration
* **6.4:** CPU Resource Management

### Epic 7: Prediction Service Implementation
**Goal:** Build, test, and deploy the high-performance Prediction Service, including dynamic model loading and real-time inference.
* **7.1:** Basic Service Scaffolding
* **7.2:** Dynamic Model Loading
* **7.3:** Real-time Prediction Endpoint
* **7.4:** Performance Monitoring