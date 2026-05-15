package main

import "testing"

func TestGeneratedLegacySymbolCatalogIsLargeEnoughForQwen3DeletionGate(t *testing.T) {
	stats := legacyMonolithSymbolStats()
	if stats["total"] < 400 {
		t.Fatalf("legacy symbol catalog is unexpectedly small: %#v", stats)
	}
	if stats["route_symbols"] < 200 {
		t.Fatalf("legacy symbol catalog missed route handlers: %#v", stats)
	}
	if stats["high_risk"] == 0 || stats["critical"] == 0 {
		t.Fatalf("legacy symbol catalog did not classify risky symbols: %#v", stats)
	}
}

func TestGeneratedLegacySymbolCatalogCarriesPortingGates(t *testing.T) {
	for _, contract := range legacyMonolithSymbolContracts {
		if contract.ID == "" || contract.Name == "" || contract.Kind == "" || contract.ReplacementFile == "" {
			t.Fatalf("incomplete legacy symbol contract: %#v", contract)
		}
		if len(contract.BehaviorInvariants) < 5 {
			t.Fatalf("missing behavior invariants for %#v", contract)
		}
		if len(contract.SecurityInvariants) < 5 {
			t.Fatalf("missing security invariants for %#v", contract)
		}
		if len(contract.PersistenceInvariants) < 4 {
			t.Fatalf("missing persistence invariants for %#v", contract)
		}
		if len(contract.PortingChecklist) < 6 {
			t.Fatalf("missing porting checklist for %#v", contract)
		}
	}
}

func TestGeneratedLegacySymbolCatalogCanFilterReplacementAndRisk(t *testing.T) {
	provider := legacyMonolithSymbolsByReplacement("provider_chat_service.go")
	if len(provider) == 0 {
		t.Fatal("expected provider chat replacement symbols")
	}
	critical := legacyMonolithSymbolsByRisk("critical")
	if len(critical) == 0 {
		t.Fatal("expected critical legacy symbols")
	}
	for _, contract := range critical {
		if contract.RiskLevel != "critical" {
			t.Fatalf("risk filter returned wrong symbol: %#v", contract)
		}
	}
}
