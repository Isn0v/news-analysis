package database

import _ "embed"

// CreateTableQuery встраивает schema.sql в бинарник на этапе компиляции.
//
//go:embed schema.sql
var CreateTableQuery string

// InsertNewsQuery встраивает insert_news.sql в бинарник на этапе компиляции.
//
//go:embed insert_news.sql
var InsertNewsQuery string
