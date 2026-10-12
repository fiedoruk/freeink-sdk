#include <SecureClient.h>
#include <fstream>
#include <iterator>
#include <cstdio>
#include <cstring>
#include <string>
int main(int argc, char** argv) {
  if (argc != 6) return 2;
  std::ifstream file(argv[3]);
  const std::string ca{std::istreambuf_iterator<char>(file), {}};
  freeink::SecureClient client;
  client.setTimeout(200);
  const uint32_t started = millis();
  if (strcmp(argv[4], "abort") == 0) client.setAbortCallback([started]() { return millis() - started >= 50; });
  client.setCACert(ca.c_str());
  const bool connected = client.connect(argv[1], static_cast<uint16_t>(std::stoi(argv[2]))) == 1;
  const uint32_t elapsed = millis() - started;
  char request[160];
  snprintf(request, sizeof(request), "GET /G10_PROTECTED/%s/1 HTTP/1.1\r\nHost: fixture\r\nConnection: close\r\n\r\n", argv[5]);
  if (connected) client.write(reinterpret_cast<const uint8_t*>(request), strlen(request));
  char response[192] = {};
  size_t received = 0;
  while (connected && millis() - started < 2000 && received + 1 < sizeof(response)) {
    const int n = client.read(reinterpret_cast<uint8_t*>(response) + received, sizeof(response) - received - 1);
    if (n > 0) received += n;
    else if (n < 0 || !client.connected()) break;
    delay(5);
  }
  const bool aborted = client.aborted();
#if defined(CROSSPOINT_TLS_MEMORY_PROBE)
  const auto stats = client.probeStats();
#endif
  client.stop();
  printf("{\"connected\":%s,\"aborted\":%s,\"elapsed_ms\":%u,\"response_ok\":%s",
         connected ? "true" : "false", aborted ? "true" : "false", elapsed,
         strstr(response, "G10_OK") ? "true" : "false");
#if defined(CROSSPOINT_TLS_MEMORY_PROBE)
  printf(",\"attempts\":%u,\"connect_calls\":%u,\"timeouts\":%u,\"tls\":\"%s\",\"samples\":\"HOST_MOCK_ONLY\"",
         stats.attempts, stats.connectCalls, stats.timeouts, stats.version);
#endif
  puts("}");
}
