package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import org.springframework.stereotype.Service;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

@Service
public class PostgresConnectionService implements ConnectionService {

    @Override
    public Connection connect(DataSource dataSource) throws SQLException {
        String url = (String) dataSource.getConnectionDetails().get("url");
        String username = (String) dataSource.getConnectionDetails().get("username");
        String password = (String) dataSource.getConnectionDetails().get("password");
        return DriverManager.getConnection(url, username, password);
    }
}
