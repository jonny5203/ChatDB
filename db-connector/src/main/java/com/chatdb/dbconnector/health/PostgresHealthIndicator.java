package com.chatdb.dbconnector.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class PostgresHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        // TODO: Implement a real health check for PostgreSQL
        return Health.up().withDetail("message", "PostgreSQL connection is healthy").build();
    }
}
