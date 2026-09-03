# M30.1 Operational Process Resolution

Implementation generation resolves framework-library processes into customer
operational processes using the deterministic identity `organization code +
source process code` within the implementation company and organization.

The resolver flushes the process identity before lookup, so controls sharing a
source process reuse a process created earlier in the same transaction. It
fails clearly if corrupted data contains multiple matching operational
processes. Framework source processes are never reassigned or mutated.

The behavior is covered by focused Odoo tests for zero-state generation,
existing-process reuse, shared source processes, duplicate detection,
cross-company isolation, framework immutability, and repeated synchronization.
