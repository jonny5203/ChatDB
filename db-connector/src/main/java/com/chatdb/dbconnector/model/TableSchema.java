package com.chatdb.dbconnector.model;

import java.util.List;

public class TableSchema {
    private String name;
    private List<ColumnSchema> columns;

    public TableSchema(String name, List<ColumnSchema> columns) {
        this.name = name;
        this.columns = columns;
    }

    // Getters and setters

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public List<ColumnSchema> getColumns() {
        return columns;
    }

    public void setColumns(List<ColumnSchema> columns) {
        this.columns = columns;
    }
}
