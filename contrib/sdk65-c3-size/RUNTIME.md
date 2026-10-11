# Remaining C3 runtime measurement

This is a measurement protocol, not a device result. The static comparison
does not qualify peak heap, fragmentation, latency, energy or OTA behavior.

Reuse the existing SDK work in [#14](https://github.com/Free-Ink/freeink-sdk/pull/14)
at `34aabdf2c8045dc90df6ec1b95f974224d8fcf37`. Its
`handshakeMinFree()` / `handshakeMinLargest()` diagnostics sample before and
after calls to `wolfSSL_connect()`. Those samples can miss a short-lived
allocation freed inside a call. Keep their result labelled sampled minimum.
Do not bring the opt-in insecure fallback into a caller carrying private grants.

For an accepted C3 bench run:

1. Record CP/SDK refs, firmware hash, compiler/flags, C3 board, certificate
   algorithm and chain length. Use the same image configuration for both
   variants. Keep endpoint credentials out of the record.
2. Start with Wi-Fi connected and stable. Record internal free bytes and largest
   block before CA loading, after connect and after `stop()`. Use
   `MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT`; record any other capability class
   separately. C3 has no PSRAM.
3. For a bounded allocator low-water window, use the pinned IDF's
   `heap_caps_monitor_local_minimum_free_size_start()` before connect, read
   `heap_caps_get_minimum_free_size()` before stopping the monitor, then call
   `heap_caps_monitor_local_minimum_free_size_stop()`. Check both return values;
   an already-active monitor is not owned by this probe. Keep other workloads
   stable and record them: this measures the system during the window, not an
   exclusive TLS allocation total. Aggregated per-region minima need not occur
   at the same instant. Keep largest-block samples as a separate metric.
4. Use a fresh transport per case. Run a valid SAN/CA, wrong SAN signed by the
   trusted CA, malformed/unknown CA, stalled handshake and abort. Include TLS
   1.2/1.3 and the actual planned trust roots. Repeat the normal connect/stop
   sequence ten times to inspect cleanup drift. Capture attempts and latency,
   since the existing TLS 1.2 retry remains part of this patch's behavior.
5. For failed verification, the synthetic protected-request marker must not
   reach the server. Successful insecure legacy calls are a compatibility
   case, not a secure-delivery result. `setCACert()` after `setInsecure()` on
   the same object remains an existing API trap; use a new object.
6. Report failures and raw values. Do not derive runtime free heap from static
   RAM or copy S3 results into the C3 row. OTA and active-reading coexistence
   require their own caller-level observations before those claims are made.

The local monitoring API was checked against the installed IDF 5.5.5 C3
`esp_heap_caps.h`. Its contract is documented in the
[ESP-IDF C3 heap reference](https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32c3/api-reference/system/mem_alloc.html).
This protocol adds no permanent SDK diagnostics or firmware dependency.
