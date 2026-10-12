#pragma once
#include <cstdarg>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
inline uint32_t nowMs = 0;
inline uint32_t cpuMHz = 10;
inline uint32_t millis() { return nowMs; }
inline void delay(uint32_t amount) { nowMs += amount; }
inline uint32_t getCpuFrequencyMhz() { return cpuMHz; }
class String {
 public:
  std::string value;
  String(const std::string& text = "") : value(text) {}
  bool startsWith(const char* prefix) const { return value.rfind(prefix, 0) == 0; }
  String substring(size_t start) const { return String(value.substr(start)); }
  void trim() {
    auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) { value.clear(); return; }
    value = value.substr(first, value.find_last_not_of(" \t\r\n") - first + 1);
  }
  bool operator==(const char* other) const { return value == other; }
};
struct SerialStub {
  std::string input, output;
  int available() { return static_cast<int>(input.size()); }
  String readStringUntil(char delimiter) {
    const size_t end = input.find(delimiter);
    const std::string line = input.substr(0, end);
    input.erase(0, end == std::string::npos ? input.size() : end + 1);
    return String(line);
  }
  void printf(const char* fmt, ...) __attribute__((format(printf, 2, 3))) {
    char buffer[4096]; va_list args; va_start(args, fmt); vsnprintf(buffer, sizeof(buffer), fmt, args); va_end(args);
    output += buffer;
  }
  void println(const char* line) { output += std::string(line) + '\n'; }
  void write(const uint8_t*, size_t) {}
};
inline SerialStub Serial;
inline SerialStub& logSerial = Serial;
struct ESPStub {
  const char* getChipModel() { return "HOST_MOCK"; }
  unsigned getChipRevision() { return 1; }
  unsigned getPsramSize() { return 0; }
  unsigned getFlashChipSize() { return 16000000; }
};
inline ESPStub ESP;
