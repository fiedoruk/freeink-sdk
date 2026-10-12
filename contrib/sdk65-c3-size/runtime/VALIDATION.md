# Validation and remaining device work

The CP/SDK sources in this package reconstruct from the public refs and patches
listed in `source-lock.json`. The SDK override is explicit. The candidate is a
temporary diagnostic build, not a C3 runtime result or an official CP release.

## Checks completed

- Four independent review axes covered correctness, architecture, embedded
  behavior and documentation. One grouped repair and a targeted follow-up
  closed the findings. The final raw-console binding correction uses CP's
  existing `logSerial`; it leaves the protocol and state behavior unchanged.
- 52 native TLS cases passed with the actual SDK client, with instrumentation
  enabled and disabled. They cover TLS 1.2/TLS 1.3 repeated connections, host/CA
  rejection, malformed trust data, stalled handshakes, cancellation and a
  closed transport. The transport did not change after these checks.
- Nine source-based dispatcher/reader/production-probe flow cases and the
  configuration/window contracts passed with ASan/UBSan. Twenty-nine parser
  cases passed. The radio, CPU and heap boundaries in these tests are mocks.
- A separate receiver reconstructed the public sources and final source hashes.
  The affected flow, contract and parser checks also passed there.
- The final `default` ESP32-C3 X3/X4 diagnostic target compiled and linked with
  Arduino 3.3.11 / ESP-IDF 5.5.5, the pinned 55.03.311 platform and the packaged
  probe flags. Source hashes remained unchanged during the build.

Firmware SHA-256: `1d0eb5184a4d3cf1fef8834c9ac01e2bcb2547b9134725dad2993b57056d39a2`.
The BIN is 5897536 bytes and is not included in this source package.
The linker's static RAM figure is 63,664 bytes; linked flash usage is 5,883,361 bytes.
These are build figures, not available runtime heap or peak TLS usage.
The named static probe symbols total 4,481 bytes. This sum excludes linker padding,
SDK client counters/stack and transient allocations; it is not a full firmware delta.

## Required C3 run

No physical C3 was identified for this work. Minimum free heap, fragmentation,
actual radio/CPU behavior, stack high-water, watchdog behavior, weak RF, energy
and OTA remain unmeasured. Host values must not be copied into those fields.

Follow the paired `early_boot` and real EPUB `reader_ui` procedure in README.
Capture all raw records and server receipts, including failed runs. A failed
positive TLS case is useful evidence to inspect even when the parser refuses
`DATA_VALIDATED`; never discard it or turn it into a pass. The parser validates
supplied records and their consistency, not cryptographic device provenance.

These results support review of the existing SDK verification work. They do
not imply that SDK #65 or the CP consumer contract has been accepted upstream.
