package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.SourceType;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;

public class MongoConnectionServiceTest {

    private MongoConnectionService mongoConnectionService;

    @BeforeEach
    public void setUp() {
        mongoConnectionService = new MongoConnectionService();
    }

    @Test
    public void testMongoConnection() {
        try (MockedStatic<MongoClients> mockedMongoClients = Mockito.mockStatic(MongoClients.class)) {
            MongoClient mockedMongoClient = mock(MongoClient.class);
            mockedMongoClients.when(() -> MongoClients.create(anyString())).thenReturn(mockedMongoClient);

            DataSource dataSource = new DataSource();
            dataSource.setSourceType(SourceType.MONGODB);
            Map<String, Object> connectionDetails = new HashMap<>();
            connectionDetails.put("connectionString", "mongodb://localhost:27017/test");
            dataSource.setConnectionDetails(connectionDetails);

            MongoClient mongoClient = mongoConnectionService.connect(dataSource);
            assertNotNull(mongoClient);
        }
    }
}
