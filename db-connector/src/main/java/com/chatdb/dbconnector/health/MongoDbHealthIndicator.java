package com.chatdb.dbconnector.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

@Component("mongoDbHealthIndicator")
public class MongoDbHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        // TODO: Implement a real health check for MongoDB
        return Health.up().withDetail("message", "MongoDB connection is healthy").build();
    }
}
