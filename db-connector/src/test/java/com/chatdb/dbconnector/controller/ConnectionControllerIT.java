package com.chatdb.dbconnector.controller;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.SourceType;
import com.fasterxml.jackson.databind.ObjectMapper;
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

import java.util.HashMap;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
public class ConnectionControllerIT {

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

    @Test
    public void testPostgresConnection() throws Exception {
        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.POSTGRESQL);
        Map<String, Object> connectionDetails = new HashMap<>();
        connectionDetails.put("url", postgresContainer.getJdbcUrl());
        connectionDetails.put("username", postgresContainer.getUsername());
        connectionDetails.put("password", postgresContainer.getPassword());
        dataSource.setConnectionDetails(connectionDetails);

        mockMvc.perform(post("/api/connections/test")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dataSource)))
                .andExpect(status().isOk())
                .andExpect(content().string("Connection successful!"));
    }

    @Test
    public void testMySqlConnection() throws Exception {
        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.MYSQL);
        Map<String, Object> connectionDetails = new HashMap<>();
        connectionDetails.put("url", mysqlContainer.getJdbcUrl());
        connectionDetails.put("username", mysqlContainer.getUsername());
        connectionDetails.put("password", mysqlContainer.getPassword());
        dataSource.setConnectionDetails(connectionDetails);

        mockMvc.perform(post("/api/connections/test")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dataSource)))
                .andExpect(status().isOk())
                .andExpect(content().string("Connection successful!"));
    }

    @Test
    public void testMongoConnection() throws Exception {
        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.MONGODB);
        Map<String, Object> connectionDetails = new HashMap<>();
        connectionDetails.put("connectionString", mongoDBContainer.getReplicaSetUrl());
        dataSource.setConnectionDetails(connectionDetails);

        mockMvc.perform(post("/api/connections/test")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dataSource)))
                .andExpect(status().isOk())
                .andExpect(content().string("Connection successful!"));
    }
}
