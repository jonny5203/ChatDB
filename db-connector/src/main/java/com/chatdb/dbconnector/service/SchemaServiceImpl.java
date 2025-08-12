package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.ColumnSchema;
import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.TableSchema;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class SchemaServiceImpl implements SchemaService {

    private final Map<String, ConnectionService> connectionServiceMap;
    private final MongoConnectionService mongoConnectionService;

    public SchemaServiceImpl(Map<String, ConnectionService> connectionServiceMap, MongoConnectionService mongoConnectionService) {
        this.connectionServiceMap = connectionServiceMap;
        this.mongoConnectionService = mongoConnectionService;
    }

    @Override
    public List<String> listTables(DataSource dataSource) throws SQLException {
        List<String> tables = new ArrayList<>();
        switch (dataSource.getSourceType()) {
            case POSTGRESQL:
            case MYSQL:
                String serviceName = dataSource.getSourceType() == com.chatdb.dbconnector.model.SourceType.POSTGRESQL ? "postgresConnectionService" : "mySqlConnectionService";
                ConnectionService service = connectionServiceMap.get(serviceName);
                try (Connection connection = service.connect(dataSource)) {
                    DatabaseMetaData metaData = connection.getMetaData();
                    ResultSet rs = metaData.getTables(null, null, "%", new String[]{"TABLE"});
                    while (rs.next()) {
                        tables.add(rs.getString("TABLE_NAME"));
                    }
                }
                break;
            case MONGODB:
                try (MongoClient mongoClient = mongoConnectionService.connect(dataSource)) {
                    String dbName = (String) dataSource.getConnectionDetails().get("database");
                    MongoDatabase database = mongoClient.getDatabase(dbName);
                    for (String collectionName : database.listCollectionNames()) {
                        tables.add(collectionName);
                    }
                }
                break;
        }
        return tables;
    }

    @Override
    public TableSchema getTableSchema(DataSource dataSource, String tableName) throws SQLException {
        List<ColumnSchema> columns = new ArrayList<>();
        switch (dataSource.getSourceType()) {
            case POSTGRESQL:
            case MYSQL:
                String serviceName = dataSource.getSourceType() == com.chatdb.dbconnector.model.SourceType.POSTGRESQL ? "postgresConnectionService" : "mySqlConnectionService";
                ConnectionService service = connectionServiceMap.get(serviceName);
                try (Connection connection = service.connect(dataSource)) {
                    DatabaseMetaData metaData = connection.getMetaData();
                    ResultSet rs = metaData.getColumns(null, null, tableName, "%");
                    while (rs.next()) {
                        columns.add(new ColumnSchema(rs.getString("COLUMN_NAME"), rs.getString("TYPE_NAME")));
                    }
                }
                break;
            case MONGODB:
                try (MongoClient mongoClient = mongoConnectionService.connect(dataSource)) {
                    String dbName = (String) dataSource.getConnectionDetails().get("database");
                    MongoDatabase database = mongoClient.getDatabase(dbName);
                    Document doc = database.getCollection(tableName).find().first();
                    if (doc != null) {
                        for (String key : doc.keySet()) {
                            columns.add(new ColumnSchema(key, doc.get(key).getClass().getSimpleName()));
                        }
                    }
                }
                break;
        }
        return new TableSchema(tableName, columns);
    }
}
