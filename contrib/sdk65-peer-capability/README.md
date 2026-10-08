# Optional peer-verification capability for SDK65

This supplement adds `SecureClient::peerVerificationAvailable()` and a
`SecureHttpClient` wrapper above the already-published compatible SDK65 patch.
It is a proposed API, not an accepted SDK contract or a second verification PR.
The incremental patch adds 13 lines across three SDK paths; it does not repeat
the CA-loading and hostname changes credited to Sameh Foulad (@sfoulad).

A downstream caller can use the capability to refuse an opt-in before starting
network work when it runs against an older or unsupported backend. The query
returns true for the patched wolfSSL backend and false when that backend is
absent. It reports backend support, not the verification state of a connection.
The caller still needs a trust anchor, valid time and a fresh transport. In
particular, calling `setCACert()` on an object previously configured with
`setInsecure()` does not clear that object's insecure state.

The implementation follows the existing `tls13Available()` pattern. The query
itself adds no per-connection allocation; this does not measure certificate
verification's memory cost or address the outstanding C3 heap qualification.
Existing insecure/local-server callers are unchanged.

## Reconstruct and check

The script starts from the public support commit, verifies its source files,
applies its existing verification patch and then this incremental patch.
Requirements: Git, Python 3, C++20 and Arduino-wolfSSL 5.7.2 sources.

```sh
python3 check.py ../sdk-capability-review --wolf-root /path/to/Arduino-wolfSSL
```

The destination must not exist. The published host helper builds the crypto
archive with two workers and nice 10; an existing compatible archive can instead
be passed with `--wolf-archive`. No firmware, device, server or CI is started.

The checker builds three variants of the actual SDK source/headers: older API,
patched API without the backend, and patched API with wolfSSL. It checks both
the SecureClient declaration/result and the SecureHttpClient wrapper. It does
not run TLS handshakes. The previously published TLS tests remain the evidence
for CA/hostname behavior; this supplement isolates the API compatibility check.

## Provenance and limits

- SDK source base: 425d200a8ea447326b4b9696e4e47dc84ad9d7f6.
- Existing support and reusable tests:
  https://github.com/fiedoruk/freeink-sdk/tree/cddb06ee5ac6bd39bb577098b11dfbea3b9b7b39/contrib/sdk65-verification
- Original verification PR: https://github.com/Free-Ink/freeink-sdk/pull/65
- Resulting three SDK files match the locally tested downstream integration.
  This is not a C3 heap, OTA, unlocker or hardware result.
- LICENSE and NOTICE preserve the SDK's MIT terms and attribution. Downloaded
  wolfSSL keeps its own licensing; no crypto source or binary is distributed here.

AI tools assisted the code, compatibility check, review and these notes.
