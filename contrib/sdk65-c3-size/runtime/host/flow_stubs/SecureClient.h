#pragma once
#include <Arduino.h>
#include <HalPowerManager.h>
#include <functional>
#include <cassert>
inline int fakeConnects = 0;
namespace freeink {
struct SecureClient {
  struct ProbeStats {
    size_t sampledFree = 100000, sampledLargest = 50000;
    uint32_t attempts = 2, connectCalls = 1, timeouts = 0;
    int lastError = 0;
    const char* version = "none";
    const char* cipher = "none";
  };
  void setTimeout(uint32_t) {}
  void setAbortCallback(std::function<bool()>) {}
  void setCACert(const char*) {}
  int connect(const char*, uint16_t) { assert(locksHeld == 1 && cpuMHz == 160); ++fakeConnects; return 0; }
  size_t write(const uint8_t*, size_t) { return 0; }
  int read(uint8_t*, size_t) { return -1; }
  bool connected() { return false; }
  bool aborted() { return false; }
  ProbeStats probeStats() { return {}; }
  void stop() {}
};
}
