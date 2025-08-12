package com.chatdb.dbconnector.controller;

import com.chatdb.dbconnector.model.DataSource;
import com.chatdb.dbconnector.model.TableSchema;
import com.chatdb.dbconnector.service.SchemaService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.sql.SQLException;
import java.util.List;

@RestController
@RequestMapping("/api/schema")
public class SchemaController {

    private final SchemaService schemaService;

    @Autowired
    public SchemaController(SchemaService schemaService) {
        this.schemaService = schemaService;
    }

    @PostMapping("/tables")
    public ResponseEntity<?> listTables(@RequestBody DataSource dataSource) {
        try {
            List<String> tables = schemaService.listTables(dataSource);
            return ResponseEntity.ok(tables);
        } catch (SQLException e) {
            return ResponseEntity.status(500).body("Failed to list tables: " + e.getMessage());
        }
    }

    @PostMapping("/tables/{tableName}")
    public ResponseEntity<?> getTableSchema(@RequestBody DataSource dataSource, @PathVariable String tableName) {
        try {
            TableSchema schema = schemaService.getTableSchema(dataSource, tableName);
            return ResponseEntity.ok(schema);
        } catch (SQLException e) {
            return ResponseEntity.status(500).body("Failed to get table schema: " + e.getMessage());
        }
    }
}
