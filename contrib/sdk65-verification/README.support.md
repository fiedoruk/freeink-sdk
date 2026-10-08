# SecureClient peer-verification tests and compatibility patch

This package adapts **only** sfoulad / Sameh Foulad's CA-load and hostname
verification changes from [Free-Ink/freeink-sdk#65](https://github.com/Free-Ink/freeink-sdk/pull/65)
to SDK `425d200a8ea447326b4b9696e4e47dc84ad9d7f6`. The two-hunk patch
retains the newer abort callback and TLS 1.2 fallback in that base. It does not
replace the PR's other SecureHttpClient change or claim ownership of #65.

The host test compiles the actual SDK `SecureClient.cpp` and the actual
Arduino-wolfSSL 5.7.2 C sources, with a POSIX socket adapter. It generates
synthetic ECDSA P-256 CA/server keys in a temporary directory and removes them after the
run. No account token, private endpoint, credential or fixture key is stored.
`TEST-ONLY-TOKEN` is a literal marker for checking whether an HTTP request
crossed the verified boundary.

Requirements: C/C++ compiler, `ar`, Python 3, Python `cryptography`, and a
local SDK checkout at the exact base plus installed Arduino-wolfSSL 5.7.2.

```sh
python3 build_wolfssl.py --wolf-root /path/to/Arduino-wolfSSL
python3 build_host_test.py --sdk-root /path/to/freeink-sdk --wolf-root /path/to/Arduino-wolfSSL
python3 test/run_real_tls.py
python3 test/run_real_tls.py --exe build/secure_client_raw_tls --negative-control
python3 test/run_redirect.py
```

Apply `sdk65-compatible.patch` to a clean SDK `425d200` checkout before
building. The raw negative control deliberately compiles the unpatched HEAD:
its **passing test means the wrong-host flaw was reproduced**, not that raw
SDK is safe. The test runner's `pass` field on the same-object mode-switch case
also means an existing unsafe transition was observed; verified callers must
use a fresh transport. Neither case is a security approval of the raw API.

The host build retains `WOLFSSL_USER_SETTINGS`, `WOLFSSL_TLS13`, `HAVE_SNI`,
`HAVE_CURVE25519`, ECC and small-stack choices used by the firmware. It uses
POSIX sockets and host timing and omits ESP hardware acceleration, FreeRTOS,
PSRAM/heap limits, Wi-Fi/DNS behaviour and physical power/abort timing.
RSA certificate chains, firmware/device/C3 peak-heap and real OTA behaviour remain unmeasured.

FreeInk SDK is MIT licensed; retain its LICENSE and NOTICE if distributing
SDK code. Arduino-wolfSSL 5.7.2 is GPL-2.0-only according to its package
metadata, and its source is compiled from the installed dependency rather than
copied here. No wolfSSL sources or compiled libraries are bundled.

The package contains the compatibility patch and its host test sources.
Build archives, generated binaries and local result files are not included.
AI tools assisted the adaptation, test harness and documentation.
