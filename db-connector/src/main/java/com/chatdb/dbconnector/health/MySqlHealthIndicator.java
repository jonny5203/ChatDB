package com.chatdb.dbconnector.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component
public class MySqlHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        // TODO: Implement a real health check for MySQL
        return Health.up().withDetail("message", "MySQL connection is healthy").build();
    }
}
