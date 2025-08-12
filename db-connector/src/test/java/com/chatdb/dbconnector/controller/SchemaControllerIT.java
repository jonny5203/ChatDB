package com.chatdb.dbconnector.controller;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.SourceType;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.MongoDBContainer;
import org.testcontainers.containers.MySQLContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
public class SchemaControllerIT {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Container
    public static PostgreSQLContainer<?> postgresContainer = new PostgreSQLContainer<>("postgres:13.3");

    @Container
    public static MySQLContainer<?> mysqlContainer = new MySQLContainer<>("mysql:8.0.26");

    @Container
    public static MongoDBContainer mongoDBContainer = new MongoDBContainer("mongo:4.4.2");

    @BeforeAll
    public static void setUp() throws Exception {
        // Setup PostgreSQL
        try (Connection conn = DriverManager.getConnection(postgresContainer.getJdbcUrl(), postgresContainer.getUsername(), postgresContainer.getPassword());
             Statement stmt = conn.createStatement()) {
            stmt.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100))");
        }

        // Setup MySQL
        try (Connection conn = DriverManager.getConnection(mysqlContainer.getJdbcUrl(), mysqlContainer.getUsername(), mysqlContainer.getPassword());
             Statement stmt = conn.createStatement()) {
            stmt.execute("CREATE TABLE products (id INT PRIMARY KEY, description VARCHAR(255))");
        }

        // Setup MongoDB
        com.mongodb.client.MongoClient mongoClient = com.mongodb.client.MongoClients.create(mongoDBContainer.getReplicaSetUrl());
        mongoClient.getDatabase("test").getCollection("orders").insertOne(new org.bson.Document("order_id", 123).append("item", "test_item"));
        mongoClient.close();
    }

    @Test
    public void testListTablesPostgres() throws Exception {
        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.POSTGRESQL);
        Map<String, Object> connectionDetails = new HashMap<>();
        connectionDetails.put("url", postgresContainer.getJdbcUrl());
        connectionDetails.put("username", postgresContainer.getUsername());
        connectionDetails.put("password", postgresContainer.getPassword());
        dataSource.setConnectionDetails(connectionDetails);

        mockMvc.perform(post("/api/schema/tables")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dataSource)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0]").value("users"));
    }

    @Test
    public void testGetTableSchemaPostgres() throws Exception {
        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.POSTGRESQL);
        Map<String, Object> connectionDetails = new HashMap<>();
        connectionDetails.put("url", postgresContainer.getJdbcUrl());
        connectionDetails.put("username", postgresContainer.getUsername());
        connectionDetails.put("password", postgresContainer.getPassword());
        dataSource.setConnectionDetails(connectionDetails);

        mockMvc.perform(post("/api/schema/tables/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dataSource)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("users"))
                .andExpect(jsonPath("$.columns[0].name").value("id"))
                .andExpect(jsonPath("$.columns[1].name").value("name"));
    }
}
