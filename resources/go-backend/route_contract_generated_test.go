package main

import "testing"

func TestGeneratedQwen3RouteContractsAllMigrated(t *testing.T) {
    stats := legacyRouteContractStats()
    if stats["total"] != 0 {
        t.Fatalf("expected all routes migrated, but catalog still has %d entries: %#v", stats["total"], stats)
    }
    if stats["missing"] != 0 {
        t.Fatalf("no missing handlers expected: %#v", stats)
    }
}

func TestGeneratedQwen3RouteContractsEmptyAfterMigration(t *testing.T) {
    for _, contract := range legacyRouteContracts {
        t.Fatalf("expected empty catalog after migration, got: %#v", contract)
    }
}

func TestGeneratedQwen3RouteContractsHelpersWork(t *testing.T) {
    domainRoutes := legacyRouteContractsByDomain("agent")
    if len(domainRoutes) != 0 {
        t.Fatalf("expected empty domain filter, got %d routes", len(domainRoutes))
    }
}
