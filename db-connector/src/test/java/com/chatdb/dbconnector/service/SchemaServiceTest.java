package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.SourceType;
import com.chatdb.dbconnector.model.TableSchema;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.MongoIterable;
import org.bson.Document;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

public class SchemaServiceTest {

    @Mock
    private Map<String, ConnectionService> connectionServiceMap;

    @Mock
    private MongoConnectionService mongoConnectionService;

    @Mock
    private ConnectionService connectionService;

    @Mock
    private Connection connection;

    @Mock
    private DatabaseMetaData databaseMetaData;

    @Mock
    private ResultSet resultSet;

    @Mock
    private MongoClient mongoClient;

    @Mock
    private MongoDatabase mongoDatabase;

    @Mock
    private MongoIterable<String> mongoIterable;

    private SchemaService schemaService;

    @BeforeEach
    public void setUp() throws SQLException {
        MockitoAnnotations.openMocks(this);
        schemaService = new SchemaServiceImpl(connectionServiceMap, mongoConnectionService);
        when(connectionServiceMap.get(anyString())).thenReturn(connectionService);
        when(connectionService.connect(any())).thenReturn(connection);
        when(connection.getMetaData()).thenReturn(databaseMetaData);
    }

    @Test
    public void testListTablesSql() throws SQLException {
        when(databaseMetaData.getTables(any(), any(), anyString(), any())).thenReturn(resultSet);
        when(resultSet.next()).thenReturn(true, true, false);
        when(resultSet.getString("TABLE_NAME")).thenReturn("table1", "table2");

        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.POSTGRESQL);

        List<String> tables = schemaService.listTables(dataSource);

        assertEquals(2, tables.size());
        assertEquals("table1", tables.get(0));
        assertEquals("table2", tables.get(1));
    }

    @Test
    public void testGetTableSchemaSql() throws SQLException {
        when(databaseMetaData.getColumns(any(), any(), anyString(), anyString())).thenReturn(resultSet);
        when(resultSet.next()).thenReturn(true, true, false);
        when(resultSet.getString("COLUMN_NAME")).thenReturn("col1", "col2");
        when(resultSet.getString("TYPE_NAME")).thenReturn("varchar", "int4");

        DataSource dataSource = new DataSource();
        dataSource.setSourceType(SourceType.POSTGRESQL);

        TableSchema schema = schemaService.getTableSchema(dataSource, "test_table");

        assertEquals("test_table", schema.getName());
        assertEquals(2, schema.getColumns().size());
        assertEquals("col1", schema.getColumns().get(0).getName());
        assertEquals("varchar", schema.getColumns().get(0).getType());
        assertEquals("col2", schema.getColumns().get(1).getName());
        assertEquals("int4", schema.getColumns().get(1).getType());
    }
}
