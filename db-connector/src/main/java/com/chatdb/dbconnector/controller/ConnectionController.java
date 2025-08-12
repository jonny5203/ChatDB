package com.chatdb.dbconnector.controller;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.service.ConnectionService;
import com.chatdb.dbconnector.service.MongoConnectionService;
import com.mongodb.client.MongoClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.Map;

@RestController
@RequestMapping("/api/connections")
public class ConnectionController {

    private final Map<String, ConnectionService> connectionServiceMap;
    private final MongoConnectionService mongoConnectionService;

    @Autowired
    public ConnectionController(Map<String, ConnectionService> connectionServiceMap, MongoConnectionService mongoConnectionService) {
        this.connectionServiceMap = connectionServiceMap;
        this.mongoConnectionService = mongoConnectionService;
    }

    @PostMapping("/test")
    public ResponseEntity<String> testConnection(@RequestBody DataSource dataSource) {
        switch (dataSource.getSourceType()) {
            case POSTGRESQL:
            case MYSQL:
                String serviceName = dataSource.getSourceType() == com.chatdb.dbconnector.model.SourceType.POSTGRESQL ? "postgresConnectionService" : "mySqlConnectionService";
                ConnectionService service = connectionServiceMap.get(serviceName);
                if (service == null) {
                    return ResponseEntity.badRequest().body("Unsupported database type: " + dataSource.getSourceType());
                }

                try (Connection connection = service.connect(dataSource)) {
                    if (connection != null && !connection.isClosed()) {
                        return ResponseEntity.ok("Connection successful!");
                    }
                } catch (SQLException e) {
                    return ResponseEntity.status(500).body("Connection failed: " + e.getMessage());
                }
                break;
            case MONGODB:
                try (MongoClient mongoClient = mongoConnectionService.connect(dataSource)) {
                    // A simple check to see if we can get the list of database names
                    mongoClient.listDatabaseNames().first();
                    return ResponseEntity.ok("Connection successful!");
                } catch (Exception e) {
                    return ResponseEntity.status(500).body("Connection failed: " + e.getMessage());
                }
        }
        return ResponseEntity.status(500).body("Connection failed for an unknown reason.");
    }
}
