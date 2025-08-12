# Testing Strategy

This document defines the comprehensive testing strategy for the project, ensuring the reliability and correctness of our distributed system. We will adhere to the principles of the Testing Pyramid.

## Testing Pyramid
The majority of tests will be fast, isolated unit tests. We will have a healthy number of integration tests to verify interactions between services, and a smaller, targeted set of end-to-end tests for critical user flows.

## 1. Unit Tests
* **Purpose**: To test individual functions, methods, or components in isolation.
* **Scope**: All business logic, helper functions, and UI components must have unit tests.
* **Tools**:
    * **Go**: `go test` with `testify/assert`.
    * **Python**: `pytest`.
    * **Java**: `JUnit 5` with `Mockito`.
    * **Frontend (React)**: `Vitest` with `React Testing Library`.

## 2. Integration Tests
* **Purpose**: To test the interaction points between microservices.
* **Scope**:
    * API Gateway routing to a downstream service.
    * Service-to-database communication.
    * Service-to-Kafka message production and consumption.
* **Tools**:
    * **TestContainers**: To spin up ephemeral Docker containers for dependencies like PostgreSQL, Redis, and Kafka during tests.
    * **Docker Compose**: For local end-to-end integration testing of the entire stack.
    * **Mock Servers**: For simulating external services.

## 3. End-to-End (E2E) Tests
* **Purpose**: To test a complete user workflow from the frontend through the entire backend stack.
* **Scope**: Focus on a few "happy path" critical user journeys, such as:
    1.  A user successfully authenticating.
    2.  A user creating a new model via a SQL query.
    3.  A user successfully getting a prediction from a trained model.
* **Tools**:
    * **Playwright**: For browser automation and testing the frontend application.

## CI/CD Pipeline Integration
* **Unit Tests**: Will run on every commit to a feature branch.
* **Integration Tests**: Will run after a successful unit test stage, before merging to `develop`.
* **E2E Tests**: Will run on a dedicated staging environment after a successful deployment. A merge to `main` is blocked until E2E tests pass.
