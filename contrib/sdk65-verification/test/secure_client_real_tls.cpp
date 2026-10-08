#include "SecureClient.h"
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 5) return 2;
  const std::string host = argv[1];
  const int port = std::stoi(argv[2]);
  const std::string caPath = argv[3];
  const std::string mode = argv[4];
  std::ifstream file(caPath);
  std::string ca((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
  freeink::SecureClient client;
  client.setTimeout(1700);
  if (mode == "legacy" || mode == "mode-switch") client.setInsecure();
  else client.setCACert(ca.c_str());
  int abortPolls = 0;
  if (mode == "abort") client.setAbortCallback([&abortPolls]() { return ++abortPolls >= 3; });
  int first = 0;
  if (mode == "mode-switch") {
    first = client.connect(host.c_str(), static_cast<uint16_t>(port));
    client.stop();
    client.setCACert(ca.c_str());
  }
  const int connected = client.connect(host.c_str(), static_cast<uint16_t>(port));
  const char request[] = "GET /private HTTP/1.1\r\nHost: good.test\r\nAuthorization: Bearer TEST-ONLY-TOKEN\r\nConnection: close\r\n\r\n";
  const size_t written = connected ? client.write(reinterpret_cast<const uint8_t*>(request), sizeof(request)-1) : 0;
  const int aborted = client.aborted();
  client.stop();
  std::cout << "first=" << first << " connected=" << connected << " written=" << written << " aborted=" << aborted
            << " abort_polls=" << abortPolls << " after_stop=" << static_cast<int>(client.connected()) << "\n";
  return 0;
}
