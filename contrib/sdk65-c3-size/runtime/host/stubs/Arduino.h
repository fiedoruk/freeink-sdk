#pragma once
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <thread>

unsigned getCpuFrequencyMhz();
inline uint32_t millis() {
  static const auto start = std::chrono::steady_clock::now();
  return static_cast<uint32_t>(
      std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count());
}
inline void delay(uint32_t ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
struct SerialStub {
  int available();
  int read();
  explicit operator bool() const { return true; }
  template <typename... Args>
  void printf(const char* format, Args... args) {
    std::fprintf(stderr, format, args...);
  }
  void println(const char* value) { std::fprintf(stderr, "%s\n", value); }
};
inline SerialStub Serial;
struct ESPStub {
  const char* getChipModel();
  unsigned getChipRevision();
  unsigned getPsramSize();
  unsigned getFlashChipSize();
  unsigned getFreeHeap() const { return 1000000; }
  unsigned getMaxAllocHeap() const { return 1000000; }
};
inline ESPStub ESP;
