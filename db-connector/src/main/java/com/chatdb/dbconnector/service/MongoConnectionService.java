package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import org.springframework.stereotype.Service;

@Service
public class MongoConnectionService {

    public MongoClient connect(DataSource dataSource) {
        String connectionString = (String) dataSource.getConnectionDetails().get("connectionString");
        return MongoClients.create(connectionString);
    }
}
