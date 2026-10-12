I found one edge case in the bodyless-response path: if the connection closes after a 304 header line but before the terminating blank line, GET() currently returns 304 with responseComplete() set.

The [patch](ARTIFACT_URL) keeps your bodyless handling and tracks whether the header section actually ended. Truncated headers return -1 and close the connection. It applies directly to `6d33e9fd` and adds no downstream cache API or TLS changes.

The reproducer confirms the original failure and passes with the patch under ASan/UBSan. It also covers complete 304 responses with Content-Length, 204, ordinary 200 responses and a following response on a reused connection. Transport is a scripted host boundary; I have not run this exact branch on a reader.

AI tools assisted the adaptation and tests. Your bodyless-response implementation remains the base of the fix.
