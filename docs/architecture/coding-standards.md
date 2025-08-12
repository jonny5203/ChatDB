# Coding Standards

This document outlines the coding standards and conventions for the project. Adherence to these standards is mandatory for all code committed to the repository to ensure consistency, readability, and maintainability across our polyglot environment.

## General Principles
* **Language**: All code, comments, and documentation must be written in English.
* **Formatting**: Code will be automatically formatted on commit using pre-configured formatters. Manual formatting changes are discouraged.
* **SOLID**: All services, especially in the Java and Python codebases, should adhere to SOLID principles.

## Monorepo Structure
* **Applications**: All deployable services and frontends reside in the `apps/` directory.
* **Shared Libraries**: Code shared between services (e.g., TypeScript types, utility functions) resides in the `packages/` directory.
* **Infrastructure**: All Terraform and Kubernetes configurations reside in the `infrastructure/` directory.

## Language-Specific Standards

### Go
* **Formatting**: Use the standard `gofmt` tool.
* **Linting**: Use `golangci-lint` with the default configuration.
* **Naming**: Follow the conventions outlined in "Effective Go." Package names should be lowercase.
* **Error Handling**: Errors should be handled explicitly. Do not use `_` to discard error return values unless absolutely necessary and commented.

### Python
* **Formatting**: Use `black` for uncompromising code formatting.
* **Linting**: Use `flake8` with plugins for security and complexity.
* **Type Hinting**: All new code should use Python 3.9+ type hints for all function signatures.
* **Dependency Management**: Use `Poetry` or `pip-tools` for managing dependencies and locking versions.

### Java
* **Build Tool**: Use Maven or Gradle for dependency management (as per Spring Boot standard).
* **Formatting**: Adhere to the Google Java Style Guide, enforced automatically.
* **Naming**: Follow standard Java naming conventions (e.g., `PascalCase` for classes, `camelCase` for methods and variables).
* **Framework**: Utilize Spring Boot conventions for dependency injection and application structure.

## Commits and Version Control
* **Branching**: Use a GitFlow-like model (feature branches, `develop`, `main`). All work must be done in feature branches.
* **Commit Messages**: Follow the Conventional Commits specification (e.g., `feat:`, `fix:`, `docs:`).
* **Pull Requests**: All code must be reviewed via a pull request before being merged into the `develop` branch.
