package main

import "testing"

func TestGeneratedQwen3RouteContractsCoverLegacySurface(t *testing.T) {
	stats := qwen3RouteContractStats()
	if stats["total"] < 200 {
		t.Fatalf("route contract catalog is unexpectedly small: %#v", stats)
	}
	if stats["missing"] != 0 {
		t.Fatalf("Go route contract has missing handlers: %#v", stats)
	}
	if stats["covered"] != stats["total"] {
		t.Fatalf("covered/total mismatch: %#v", stats)
	}
	if stats["high_risk"] == 0 {
		t.Fatalf("route contract did not classify any high-risk routes: %#v", stats)
	}
}

func TestGeneratedQwen3RouteContractsCarryDeletionGates(t *testing.T) {
	for _, contract := range qwen3RouteContracts {
		if contract.Endpoint == "" || contract.LegacySymbol == "" || contract.GoPattern == "" {
			t.Fatalf("incomplete contract: %#v", contract)
		}
		if len(contract.RequestContract) < 4 || len(contract.ResponseContract) < 4 || len(contract.FailureContract) < 4 {
			t.Fatalf("contract lacks request/response/failure gates: %#v", contract)
		}
		if contract.RiskLevel == "high" || contract.RiskLevel == "critical" {
			if !contract.RequiresPermission {
				t.Fatalf("high-risk route lacks permission gate: %#v", contract)
			}
		}
	}
}

func TestGeneratedQwen3RouteContractsCanFilterDomains(t *testing.T) {
	agentRoutes := qwen3RouteContractsByDomain("agent")
	if len(agentRoutes) == 0 {
		t.Fatal("expected agent domain contracts")
	}
	for _, contract := range agentRoutes {
		if contract.Domain != "agent" {
			t.Fatalf("domain filter returned wrong route: %#v", contract)
		}
	}
}
