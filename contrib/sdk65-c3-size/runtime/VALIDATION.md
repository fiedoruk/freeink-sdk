# Validation and remaining device work

The CP/SDK sources in this package reconstruct from the public refs and patches
listed in `source-lock.json`. The SDK override is explicit. The candidate is a
temporary diagnostic build, not a C3 runtime result or an official CP release.

## SDK refresh

The SDK base changes from `1a5448df` to `7fcd3b34`; CP remains `fc3aed12`.
The only upstream source change ends an existing UC8279 SPI transaction before
the next command. It does not change the probe, SecureNet, test fixtures or
measurement contract. Previous host results apply to identical checked sources.
A fresh receiver reconstructed this revision from both public refs and applied
the unchanged patches. The C3 build passed with these sources. Four independent
reviews covered this SDK delta; metadata corrections aligned the identity
template and archive links. The older firmware receipt is historical, not
validation of the new SDK base. No physical C3 was tested.

## Earlier checks retained for unchanged diagnostic/TLS sources

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

## Build for this SDK revision

The `default` ESP32-C3 X3/X4 diagnostic target compiled and linked with
Arduino 3.3.11 / ESP-IDF 5.5.5, the pinned 55.03.311 platform and the packaged
probe flags. Source hashes remained unchanged during the build.

Firmware SHA-256: `15a5c2d423f41a4fd14ece4e40a41eb0b78404e22500d3bcff802d7825b0f397`.
The BIN is 5897536 bytes and is not included in this source package.
The linker's static RAM figure is 63,664 bytes; linked flash usage is 5,883,367 bytes.
These are build figures, not available runtime heap or peak TLS usage.
The earlier build counted 4,481 bytes in named static probe symbols. That is
historical evidence for unchanged probe code, excluding linker padding, SDK
client counters/stack and transient allocations; it is not a full firmware delta.

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
