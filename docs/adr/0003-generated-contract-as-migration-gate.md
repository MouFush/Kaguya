# Generated Contracts as Migration Gates

During Python-to-Go migration, contract files cataloged all legacy routes and symbols as deletion gates. After migration confirmation, contracts are slimmed to empty arrays and tests verify total=0.

## Status
Accepted

## Consequences
- Contract files generated from legacy monolith source
- Legacy code deleted only after Go covers all cases
- Test files verify all contracts are migrated
