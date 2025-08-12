package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;

import java.sql.Connection;
import java.sql.SQLException;

public interface ConnectionService {
    Connection connect(DataSource dataSource) throws SQLException;
}
