# Data Models

This document defines the core data entities for the platform. These models serve as the conceptual blueprint for database schemas, API contracts, and shared types in the monorepo.

---
## 1. DataSource
**Purpose:** Represents a configured connection to an external data source, such as a user's e-commerce database.

```typescript
interface DataSource {
  id: string; // UUID
  name: string;
  sourceType: 'POSTGRESQL' | 'MYSQL' | 'MONGODB';
  connectionDetails: any; // Encrypted connection credentials
  createdAt: Date;
  updatedAt: Date;
}
