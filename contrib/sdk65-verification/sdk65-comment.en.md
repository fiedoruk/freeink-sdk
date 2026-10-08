I adapted @sfoulad's two `SecureClient` verification changes from #65 onto current SDK `main` (`425d200`) without replacing the later abort callback from #115 or the TLS 1.2 fallback. The attached two-hunk diff fails closed when a CA buffer cannot be loaded and enables hostname matching for verified connections. `setInsecure()` callers keep their existing behavior.

I tested the production `SecureClient.cpp` with Arduino-wolfSSL 5.7.2 and a loopback POSIX transport. A synthetic ECDSA P-256 CA and matching SAN connected over TLS 1.2 and TLS 1.3; a complete intermediate chain connected. Wrong SAN signed by the same CA, unknown or malformed CA, expired or not-yet-valid leaf, and incomplete chain all refused without sending the test Authorization marker. The unpatched SDK accepted the same-CA wrong-host case and sent that marker, confirming the negative control. A stalled handshake honored the existing abort callback. The older stub-boundary suite still passes 11 cases. These are host results; C3 peak heap, OTA and device behavior have not been measured.

One API caveat from the host test: changing the **same** `SecureClient` from `setInsecure()` to `setCACert()` does not clear its insecure flag. Our verified caller creates a fresh transport for each request. `SecureHttpClient` does not follow redirects by default; an explicit `setFollowRedirects(1)` forwards an Authorization header to another origin, so private callers should leave redirect following off.

Could the compatible verification hunks be incorporated in this PR, and which official SDK ref should a dependent CrossPoint caller target once this is accepted? Credit for the original verification changes remains with @sfoulad.

AI tools assisted the compatibility adaptation, host tests, review and this description.
