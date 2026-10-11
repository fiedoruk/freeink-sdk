# C3 size comparison for the SDK #65 compatibility patch

This compares the already published adaptation of sfoulad's CA-load and
hostname-verification changes against the original SDK. It does not introduce
a new TLS implementation, include a CA bundle, change insecure legacy calls,
or claim ownership of SDK #65.

Both sides use CP PR #3877 at `44626dd5bc`, its SDK pin `425d200a8e`, the same
small bundle-subdirectory guard, and the `default` ESP32-C3 environment. Only
`SecureClient.cpp` changes between the builds. That SDK's SecureNet source is
identical to main `2ca5e31e68`; the numbers still belong to this specific CP
composition, not a current release or a runtime test.

The bundle guard is included only to reproduce the exact CP source used for the
baseline build, which also validated that separate installer contribution.
It is present on both sides of the comparison.

## Recorded result

| Measure | Original SDK | Two verification checks | Difference |
|---|---:|---:|---:|
| Flash | 5922777 B | 5923141 B | +364 B |
| Static RAM | 59168 B | 59168 B | 0 B |

The flash change consists of +220 B executable text and +144 B read-only data.
ELF symbols show +86 B in `connectWithMethod()` and a newly linked 134 B
`wolfSSL_check_domain_name()`. No other section contributing to static RAM changed.
These numbers do not measure the temporary allocations made at handshake time.

## Reproduce

Check the source composition without compiling firmware:

```sh
python3 reproduce.py ../tls-size-source
```

For a separate fresh directory and an existing working PlatformIO setup:

```sh
python3 reproduce.py ../tls-size-build --build --pio /path/to/pio
```

Requirements: Git, Python 3, and for builds the platform/toolchains specified by
CP's pinned `platformio.ini`. Builds run sequentially with two jobs and reduced
priority, also set `PLATFORMIO_RUN_JOBS=2` for nested PlatformIO invocations,
reuse one checkout/build directory, and do not clean the cache.
No upload, CI or device operation is performed. A failed build stops the script.

See `results.json` for the recorded static measurements and `RUNTIME.md` for the
remaining C3 bench protocol. Static RAM is not runtime free heap. This comparison
measures the marginal cost of two checks in firmware already using wolfSSL;
it does not compare verified TLS against plaintext or a firmware without TLS.

The existing [public verification package](https://github.com/fiedoruk/freeink-sdk/tree/cddb06ee5ac6bd39bb577098b11dfbea3b9b7b39/contrib/sdk65-verification)
contains the real wolfSSL host tests and explains their limitations. The patch
here is byte-identical. Those tests are reused evidence, not new device results.
The optional `peerVerificationAvailable()` API from later work is not included.

CrossPoint and SDK licenses/notices are included. No wolfSSL source, compiled
library or firmware is bundled. AI tools assisted the measurement packaging
and documentation. This material supports the existing PRs, not a new TLS PR.
