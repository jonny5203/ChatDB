package com.chatdb.dbconnector.service;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.TableSchema;

import java.sql.SQLException;
import java.util.List;

public interface SchemaService {
    List<String> listTables(DataSource dataSource) throws SQLException;
    TableSchema getTableSchema(DataSource dataSource, String tableName) throws SQLException;
}
