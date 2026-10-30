package main

import "testing"

func TestGeneratedLegacySymbolCatalogAllMigrated(t *testing.T) {
    stats := legacyMonolithSymbolStats()
    if stats["total"] != 0 {
        t.Fatalf("expected all symbols migrated, but catalog still has %d entries: %#v", stats["total"], stats)
    }
}

func TestGeneratedLegacySymbolCatalogEmptyAfterMigration(t *testing.T) {
    for _, contract := range legacyMonolithSymbolContracts {
        t.Fatalf("expected empty catalog after migration, got: %#v", contract)
    }
}

func TestGeneratedLegacySymbolCatalogHelpersWork(t *testing.T) {
    provider := legacyMonolithSymbolsByReplacement("provider_chat_service.go")
    if len(provider) != 0 {
        t.Fatalf("expected empty replacement filter, got %d symbols", len(provider))
    }
    critical := legacyMonolithSymbolsByRisk("critical")
    if len(critical) != 0 {
        t.Fatalf("expected empty risk filter, got %d symbols", len(critical))
    }
}
