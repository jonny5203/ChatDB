package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.SourceType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;
import org.mockito.Mockito;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;

public class ConnectionServiceTest {

    private PostgresConnectionService postgresConnectionService;
    private MySqlConnectionService mySqlConnectionService;

    @BeforeEach
    public void setUp() {
        postgresConnectionService = new PostgresConnectionService();
        mySqlConnectionService = new MySqlConnectionService();
    }

    @Test
    public void testPostgresConnection() throws SQLException {
        try (MockedStatic<DriverManager> mockedDriverManager = Mockito.mockStatic(DriverManager.class)) {
            Connection mockedConnection = mock(Connection.class);
            mockedDriverManager.when(() -> DriverManager.getConnection(anyString(), anyString(), anyString())).thenReturn(mockedConnection);

            DataSource dataSource = new DataSource();
            dataSource.setSourceType(SourceType.POSTGRESQL);
            Map<String, Object> connectionDetails = new HashMap<>();
            connectionDetails.put("url", "jdbc:postgresql://localhost:5432/test");
            connectionDetails.put("username", "user");
            connectionDetails.put("password", "password");
            dataSource.setConnectionDetails(connectionDetails);

            Connection connection = postgresConnectionService.connect(dataSource);
            assertNotNull(connection);
        }
    }

    @Test
    public void testMySqlConnection() throws SQLException {
        try (MockedStatic<DriverManager> mockedDriverManager = Mockito.mockStatic(DriverManager.class)) {
            Connection mockedConnection = mock(Connection.class);
            mockedDriverManager.when(() -> DriverManager.getConnection(anyString(), anyString(), anyString())).thenReturn(mockedConnection);

            DataSource dataSource = new DataSource();
            dataSource.setSourceType(SourceType.MYSQL);
            Map<String, Object> connectionDetails = new HashMap<>();
            connectionDetails.put("url", "jdbc:mysql://localhost:3306/test");
            connectionDetails.put("username", "user");
            connectionDetails.put("password", "password");
            dataSource.setConnectionDetails(connectionDetails);

            Connection connection = mySqlConnectionService.connect(dataSource);
            assertNotNull(connection);
        }
    }
}
