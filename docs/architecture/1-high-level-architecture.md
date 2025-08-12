# 1. High Level Architecture

### Technical Summary
This document outlines a distributed, event-driven microservices architecture designed for scalability and resilience. The system is polyglot, leveraging Go for the high-performance API Gateway, Java for the robust Configuration and Auth Services, and Python for the data-centric Ingestion and Insight Engines. All services will be containerized and orchestrated on Kubernetes. This architecture directly supports the primary goal of creating a real-time, AI-powered insight engine, while providing a robust and modern foundation suitable for a high-skill portfolio project.

### Platform and Infrastructure Choice
* **Platform:** Google Cloud Platform (GCP)
* **Key Services:**
    * **Google Kubernetes Engine (GKE):** For container orchestration.
    * **Confluent Cloud on GCP (or self-managed Kafka):** For the event-driven backbone.
    * **AWS S3 (emulated with LocalStack):** For model storage.
    * **Cloud SQL (PostgreSQL):** To serve as the initial Data Mart for insights.

### Repository Structure
The project will use a **Monorepo** managed with a tool like **Nx** or **Turborepo** to handle the polyglot build processes and shared package dependencies efficiently.

### High Level Architecture Diagram
```mermaid
graph TD
    subgraph User
        U[User via Client App]
    end

    subgraph External IAM
        IAM[Okta / Keycloak]
    end

    subgraph KubernetesCluster
        GW[API Gateway - Go]

        subgraph Kafka
            K[Kafka Backbone]
        end

        Auth[Auth Service - Java]
        CS[Config Service - Java]
        IS[Ingestion Service - Python]
        IE[Insight Engine - Python]
        DM[Data Mart - PostgreSQL]
        MR[Model Registry - Go]
        TO[Training Orchestrator - Python]
        PS[Prediction Service - Go]
    end

    subgraph External
        Ext[External Data Source]
    end
    
    U -- Login --> GW
    GW -- Authenticate --> Auth
    Auth -- Federate --> IAM
    U -- SQL Query --> GW
    GW -- Authorize --> Auth
    GW -- Parse --> QP[Query Parser - Python]
    QP -- Get Schema --> DBC[DB Connector - Java]
    QP -- Create Plan --> EE[Execution Engine]
    EE -- Get Data --> DBC
    EE -- Train Model --> TO
    EE -- Get Model --> MR
    TO -- Run Job --> IE
    IE -- Get Data --> DBC
    IE -- Save Model --> MR
    EE -- Predict --> PS
    PS -- Load Model --> MR
    DBC -- Connect --> Ext