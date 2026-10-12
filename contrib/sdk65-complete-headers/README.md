# Complete headers before a bodyless response

This is a one-file supplement to @sfoulad's SDK #65 head
`6d33e9fd8c6fd1c53c40c0ef1ccaa4535606610a`. It keeps the existing bodyless-response
handling and requires the blank line that terminates the headers before returning
success. A dropped connection or timeout halfway through a 304 must not set
responseComplete().

The patch adds one boolean and checks it alongside the existing abort flag.
It does not add the downstream cache/header API, change TLS verification, or
replace the original author's bodyless guard.

Run `python3 replay.py /absolute/path/to/new-empty-receiver`. Requirements: Git,
Python3 and a C++17 compiler with AddressSanitizer/UndefinedBehaviorSanitizer.
The script fetches the exact public PR head, first confirms the original truncated
304 case (expected exit 42), applies the patch, then runs complete/truncated header,
200/204/304 and persistent-connection cases against the production HTTP class.
Wi-Fi/TCP are scripted host boundaries; these are not TLS or physical-device tests.

The header-completion change is the same logic already reviewed in the dependent
conditional-image work; this package projects only that fix onto the author's
branch. Its current host tests pass. No new firmware build or device result is
claimed for this older SDK branch. Source license/notice and original authorship
are retained. AI tools assisted the adaptation, tests and documentation.
