#pragma once
#include "Arduino.h"
struct IPAddress {
  uint8_t bytes[4] = {127, 0, 0, 1};
  uint8_t operator[](unsigned i) const { return bytes[i]; }
};
class Client {
 public:
  virtual ~Client() = default;
  virtual int connect(IPAddress, uint16_t) = 0;
  virtual int connect(const char*, uint16_t) = 0;
  virtual size_t write(uint8_t) = 0;
  virtual size_t write(const uint8_t*, size_t) = 0;
  virtual int available() = 0;
  virtual int read() = 0;
  virtual int read(uint8_t*, size_t) = 0;
  virtual int peek() = 0;
  virtual void flush() = 0;
  virtual void stop() = 0;
  virtual uint8_t connected() = 0;
  virtual operator bool() = 0;
  uint32_t getTimeout() const { return timeout_; }
  void setTimeout(uint32_t value) { timeout_ = value; }
 private:
  uint32_t timeout_ = 2000;
};
