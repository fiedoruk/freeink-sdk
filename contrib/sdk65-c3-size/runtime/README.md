# C3 TLS memory diagnostic

This temporary opt-in probe measures the existing wolfSSL `SecureClient` in a
real CrossPoint build. It supports the CA-load and hostname-verification work
in SDK #65. It is a tester package, not a C3 result, an OTA qualification, or a
new TLS implementation. No physical C3 was identified while preparing it.

The source composition is CP PR #3877 at `fc3aed12100e3149cae6128a321c902f056786cc`
and SDK main `1a5448dfa705d6499fbff20371539bf553865dd2`, plus the already published
SDK65 compatibility checks and this diagnostic patch. The SDK differs from CP's
raw gitlink; `source-lock.json` records that deliberate override. SDK #65's raw
PR head is **not** the SDK used by this candidate. The diagnostic follows the
before/after sampling in SDK #14 (`34aabdf2c8045dc90df6ec1b95f974224d8fcf37`)
without importing its insecure fallback. Existing `AbortCallback` is already
present at the selected SDK main ref.

## Reconstruct and build

Run all commands below from this packet directory. The build uses a subshell,
so later scripts still resolve here.

Requirements: Python 3, Git and, for the fixture/host tests, `cryptography`.
Firmware uses CP's existing pinned PlatformIO/pioarduino setup. The fixture's
Python/OpenSSL must support TLS 1.2 and 1.3. Reconstruct into a new directory:

```sh
python3 reproduce.py ../receiver
```

The script verifies packet hashes, fetches both public refs, applies the two
patches, verifies result hashes and copies the opt-in `platformio.local.ini`.
It never builds, uploads or runs CI. For the one ESP32-C3 X3/X4 target:

```sh
(cd ../receiver/crosspoint &&
  PLATFORMIO_RUN_JOBS=2 nice -n 10 /path/to/pio run -e default -j2 > ../build.log 2>&1)
```

Keep an existing toolchain/cache. Do not build all boards or erase caches.
Record the exit status, compiler/core versions, actual flags, BIN/ELF hashes and
sizes. The local override preserves the target and base flags, enables only
`CROSSPOINT_TLS_MEMORY_PROBE`, and reduces CP logging to keep measurement noise
bounded. The temporary instrumented image is not a distribution artifact. With
the flag absent, the added caller blocks and SDK counters disappear. Restore
the previous CP image/configuration after the bench test.

The recorded build used Arduino 3.3.11 and ESP-IDF 5.5.5. Use the matching
platform/core; an existing global Arduino 2.x installation is not equivalent.
An isolated PlatformIO core avoids that version collision.
See [validation and remaining device work](VALIDATION.md) for the actual result.
A [ZIP containing this source packet](G10-tester-packet.zip) is available alongside it.

## Host checks

Reuse a compatible Arduino-wolfSSL 5.7.2 native archive and its matching headers.
The reused public SDK65 `build_wolfssl.py` is included if a recipient needs
to construct that archive; no archive is included here. CP pins the source
package `wolfssl/Arduino-wolfSSL@5.7.2` in `platformio.ini`. After obtaining
that version with the recipient's normal PlatformIO dependency setup, run
`python3 build_wolfssl.py --wolf-root /path/to/Arduino-wolfSSL`. This builds
only the native library with two workers, producing `build/libwolfssl-host.a`.
It does not compile firmware.
The required flags are in `run_host.py` and in the host receipt. Check the archive
and `user_settings.h` hashes before reusing a local build.

```sh
python3 run_host.py --cp ../receiver/crosspoint \
  --wolf-root /path/to/Arduino-wolfSSL \
  --wolf-archive /path/to/libwolfssl-host.a --output ../host.json
python3 check_repair.py --cp ../receiver/crosspoint --output ../repair.json
python3 test_parser.py
```

The real TLS matrix runs the actual SDK client with and without instrumentation:
ten TLS 1.2 and ten TLS 1.3 connect/stop runs, wrong hostname, unknown CA,
malformed CA, stalled handshake, in-flight callback abort and an abruptly closed
transport. The host's heap functions are deliberate mocks used only to test
monitor ownership, error preservation and config parsing; they produce no C3
memory claim. ASan/UBSan check the production config/window headers. Production
probe syntax is also checked against host boundary stubs. The targeted flow
check compiles the actual main command dispatcher and ready-reader guarded
caller with the production probe, then checks the request latch, one-shot run,
foreign-radio refusal, owned-radio cleanup and CPU locks using deliberate mocks. Arduino radio, IDF
heap behavior, stack and physical reader activity still require C3.

## Hardware run

Use only a separately identified and authorized ESP32-C3 X3/X4, with no PSRAM.
Record its model/revision, flash, previous image, SD data/config backup and
recovery procedure. A Sticky/ESP32-S3 does not fill the C3 row. This package
contains no flash command and grants no device or network permission.

1. Start one fixture on an authorized local bench network. Use a DNS name
   resolvable by the reader, or its literal IPv4 address; the generated leaf
   carries the supplied host in SAN and the SDK checks that exact string.

   ```sh
   python3 fixture.py ../fixture --bind 0.0.0.0 --host BENCH_HOST
   ```

   Keep the process alive for both contexts: same CA, leaf, ports and timestamp.
   It uses synthetic P-256/SHA256 certificates, one leaf signed by one local CA,
   a second unknown CA, a wrong-host leaf, TLS-1.2-only/TLS-1.3-only listeners,
   stall and immediate-close listeners. Keys remain local with restricted
   permissions. The protected marker is synthetic and contains no grant.

2. Edit **only your local** `probe.conf`: `ssid`, `password`, `host` if needed,
   and `context=early_boot`. The generated epoch provides a controlled valid
   certificate clock; this does not prove SNTP. Copy `probe.conf`, `root.pem`
   and `unknown.pem` to `/.crosspoint/g10/` on the SD card. Do not commit or
   upload the config, credentials, certificate keys, real grants or Wi-Fi logs.
   Blank passwords are accepted for an authorized open lab network. All other
   fields are mandatory; unknown/duplicate fields, invalid ports, long fields
   and truncated PEM files are rejected.

3. Run the approved image and record serial output. `early_boot` runs after SD
   startup, before display/font initialization and reader routing. Existing
   static CP globals still exist. Wait for `G10_END`; a `G10_ERROR` is a failed
   or incomplete run. Wi-Fi association (15 seconds maximum) and the fixture
   clock happen before every TLS sample window.

4. Change only the context to `reader_ui`, restart the same image, open the pinned CP fixture
   `test/epubs/test_reader_menu_progress.epub` (SHA256
   `2597db6f017f4f051d351b0e04e342bac2f31fe661d2d87e2bd8943dc9f20979`).
   Select Noto Serif, size 14, portrait and page 2; keep those choices during
   the run and record the visible page indicator. Record concurrent workers as
   `none observed` only when checked, otherwise describe them. Wait for a rendered
   page. Then send the line `CMD:G10` followed by a newline through serial. The existing main serial dispatcher latches that request; it survives until
   the ready reader consumes it once. The reader calls the probe only with a loaded EPUB section, completed render and the
   existing `RenderLock`. It retains the reader, page and font caches. One case
   runs per reader loop; the lock is released between cases and on failure.
   The probe refuses any already active foreign Wi-Fi mode/connection, uses
   nonpersistent credentials for its own STA, keeps it between cases and shuts
   down only its own radio on preparation failure, monitor failure or normal
   completion. Existing CPU locks restore normal C3 160 MHz for preparation and
   each step; metadata and every row record the actual CPU checkpoint. Network
   preparation and each case temporarily block reader interaction in
   this explicit lab mode. This is not production background-reading support.
   Set idle sleep to at least five minutes during each run, so CP does not end
   the reader run between cases; restore the previous setting afterward.
   Do not navigate while the paired measurement runs. Record page/font/input
   settings, EPUB hash, and any concurrent worker activity in `identity.json`.

5. After the second `G10_END`, stop the fixture with Ctrl-C to write
   `server-results.json`. Copy `identity-template.json` to your private
   `identity.json` and fill the actual model, revision, source refs, firmware
   hash, fixture root hash and every reader workload field. Set `physicalC3` to
   `IDENTIFIED` only after identifying the actual authorized C3; the template
   remains `NOT_IDENTIFIED` until then. Parse both serial captures:

   ```sh
   python3 parse_results.py ../early.log ../reader.log \
     --server ../fixture/server-results.json --fixture ../fixture/fixture.json \
     --identity ../identity.json --output ../runtime.json
   ```

   The parser rejects incomplete/duplicate rows, unowned or failed allocator
   windows, S3 identity, missing source hashes, unconfirmed physical identification,
   incomplete reader workload, CPU checkpoints below the expected 160 MHz,
   unexpected retry/abort behavior,
   absent good responses, and any extra protected-request marker. Keep raw logs
   and server receipts even on failure. `DATA_VALIDATED` validates supplied data;
   it does not certify hardware provenance, energy, OTA or a release.

6. Remove `/.crosspoint/g10/`, stop the fixture, restore previous settings/data
   and the agreed CP image, and verify normal reading. Keep redacted evidence;
   delete the local lab keys and credential-bearing config when no longer
   needed. Never erase the full flash merely to remove this probe.

## Measurement semantics

`before` is **before `setCACert()`**, with both PEM buffers and configuration
already loaded from SD, Wi-Fi connected and the fixture clock set. `setCACert`
only borrows the buffer; the actual CA parse occurs inside connect. The owned
IDF local-minimum window starts immediately before `connect()` and ends after
its return, including TCP connect, CA parse, handshake and SDK retry. It measures
all matching heap regions/system activity during that window, not exclusive
TLS allocation. Per-region minima can occur at different times.

`connect`, `response` and `stop` are sampled internal/8-bit free bytes and
largest block; `stop` is after explicit `SecureClient::stop()` but before the
stack client object's destruction. The two lifetime values come from outside
the owned window. They are not attributable handshake peaks. If monitor start
fails, the probe skips connect and never stops a foreign monitor. Both return
codes and whether stop was called are retained; a failed monitor ends the run.

SDK sampled minima bracket each `wolfSSL_connect()` invocation, including its
successful return. They can miss allocations freed inside that call. A value
of `4294967295` means no sample was taken, as in malformed-CA rejection.
Attempt count includes the existing explicit TLS 1.2 retry; connect-call count
includes WANT_IO polling. Each handshake has a 2-second deadline; TCP connect
also has a 2-second bound, so the whole call can exceed 2 seconds. `stall` must
show two handshake timeouts. `abort` uses the existing callback after 100 ms;
it must return aborted with no retry or protected request. The drop endpoint
models a transport close; it is not a weak-radio/RF or power-loss test.

The config, two bounded 2048-byte PEM buffers and a shared 192-byte I/O buffer
remain in static RAM in **both** contexts; `config_static_bytes` reports their
combined `sizeof`. Flags, SDK counters, stack client and sampling also add
measurement overhead. Compare these two instrumented contexts, and do not
present either as a zero-overhead production heap measurement. The probe adds
no task, TLS engine, permanent product API, account integration or private data.
Review raw per-iteration cleanup drift instead of declaring no leak from one
sample. TLS 1.2/1.3, certificate algorithm, chain and response size belong to
this fixture; production trust chains need their own bounded follow-up.

## Attribution and boundaries

CP and SDK MIT notices are included separately. Their authors retain ownership
of the reader, transport, SDK65 verification work and SDK14 diagnostics. The
fixture certificate generator and POSIX transport stubs are adapted from the
already public TIMED/W06 support material. wolfSSL retains its own upstream
licensing; no library source, archive or firmware binary is shipped here.
AI tools assisted diagnostic code, tests and documentation. This packet is
support material, not an upstream merge or a C3 runtime result.
