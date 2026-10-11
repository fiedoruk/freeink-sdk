# Evidence boundaries

- The current source reconstruction fetched public CP and SDK refs and verified both patches and result hashes. No private repository is needed.
- Two local default/C3 builds passed. The first also validated the bundle guard; it is counted once. The second reused that exact checkout, configuration and cache with only SecureClient.cpp changed.
- Pinned platform: PioArduino 55.03.311, Arduino 3.3.11, IDF 5.5.5, RISC-V GCC 14.2.0. The two effective configurations match byte-for-byte. Static measurements and binary hashes are in results.json.
- The size parser uses the last firmware size report: a cold custom-core build can print a small scaffold result first. ELF sections and TLS symbol sizes independently reconcile the +364 B flash delta.
- The public script's source-only path was executed. Its optional build path provides the same pio target and bounded command used for the recorded builds; it was not rerun just to exercise the wrapper. No third baseline build is claimed.
- The patch is unchanged from the public SDK #65 support package. Real TLS host tests and code review are reused. The later capability method is omitted; the CA/hostname/abort/fallback implementation matches the earlier reviewed code.
- No fresh TLS handshake, C3 device, runtime heap, largest-block, power, active-reading or OTA measurement was performed. The original SDK file was restored exactly after the comparison.
- Existing modes and retry behavior are preserved; no insecure fallback policy from PR #14 is included. The mode-switch trap documented in the public package remains outside this adaptation.
