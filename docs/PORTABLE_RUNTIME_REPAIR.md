# Portable D1/D2 repair integration

The earlier isolated prerequisite QA reported 35 passes and two strict expected
failures. Those failures were real defects, not passing safeguards. A separate
CPU worker supplied a hash-bound repair; Connector reviewed and integrated it
alongside W01/W02. Original QA evidence remains historical and unchanged.

D1: recursive finite-number checks now reject JSON overflow (`1e309`) and nested
in-memory NaN/infinity during read/trial validation. Previously, the host-memory
floor accepted overflow until a later strict JSON write rejected it; the six
finite existing specs were unaffected. This is not general schema/type expansion.

D2: an exited worker with zero persisted telemetry samples now has null unknown
peaks, `unknown_no_samples` status and a non-success telemetry stop reason. Its
actual exit code and any earlier deadline/error reason remain intact. A measured
zero remains numeric zero. A late unpersisted sample does not manufacture
retrospective resource coverage. Existing runner/result consumers reject clean
completion when a supervisor stop reason exists.

The supplied 109 ordinary regressions and 22 overlay tests pass together: 131
local tests, no skips or expected failures. Saved-array overlay verification and
repository structural checks also pass. See the source pins, exact integration
hashes and resource measurements in
[integration evidence](../validation/portable-d1-d2-integration-2026-09-13.json).
The contracts change preserves the previously added W02 endpoint-binding check.

These are portable-only repairs. Local tests mock process/Git/signal objects;
they do not qualify actual native/CUDA termination or full-data CPU/GPU PORT.
No native P1 timing, owner, physics, optimizer or model implementation is changed.
Manager remains the sole native/GPU owner. No new executable trial or UVA job
is granted by this integration.
