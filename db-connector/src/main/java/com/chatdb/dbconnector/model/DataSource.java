package com.chatdb.dbconnector.model;

import java.util.Date;
import java.util.Map;
import java.util.UUID;

public class DataSource {
    private UUID id;
    private String name;
    private SourceType sourceType;
    private Map<String, Object> connectionDetails;
    private Date createdAt;
    private Date updatedAt;

    // Getters and setters

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public SourceType getSourceType() {
        return sourceType;
    }

    public void setSourceType(SourceType sourceType) {
        this.sourceType = sourceType;
    }

    public Map<String, Object> getConnectionDetails() {
        return connectionDetails;
    }

    public void setConnectionDetails(Map<String, Object> connectionDetails) {
        this.connectionDetails = connectionDetails;
    }

    public Date getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Date createdAt) {
        this.createdAt = createdAt;
    }

    public Date getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Date updatedAt) {
        this.updatedAt = updatedAt;
    }
}
