#pragma once
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>

#include "Client.h"

// Host-only adapter: the requested name is deliberately mapped to loopback.
// SecureClient still sends that exact name as SNI and for certificate matching.
class WiFiClient : public Client {
 public:
  ~WiFiClient() override { stop(); }
  void setConnectionTimeout(uint32_t timeout) { timeout_ = timeout; }
  void setTimeout(uint32_t timeout) { timeout_ = timeout; }
  int connect(IPAddress, uint16_t port) override { return connect("127.0.0.1", port); }
  int connect(const char*, uint16_t port) override {
    stop();
    fd_ = socket(AF_INET, SOCK_STREAM, 0);
    if (fd_ < 0) return false;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    timeval tv{static_cast<time_t>(timeout_ / 1000), static_cast<suseconds_t>((timeout_ % 1000) * 1000)};
    setsockopt(fd_, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    if (::connect(fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
      stop();
      return false;
    }
    fcntl(fd_, F_SETFL, fcntl(fd_, F_GETFL, 0) | O_NONBLOCK);
    return true;
  }
  uint8_t connected() override {
    if (fd_ < 0) return false;
    char c;
    const int n = recv(fd_, &c, 1, MSG_PEEK | MSG_DONTWAIT);
    return n > 0 || (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK));
  }
  void stop() override {
    if (fd_ >= 0) {
      close(fd_);
      fd_ = -1;
    }
  }
  int available() override {
    int n = 0;
    if (fd_ >= 0) ioctl(fd_, FIONREAD, &n);
    return n;
  }
  size_t write(uint8_t b) override { return write(&b, 1); }
  size_t write(const uint8_t* data, size_t n) override {
    return fd_ < 0 ? 0 : static_cast<size_t>(std::max<ssize_t>(0, send(fd_, data, n, 0)));
  }
  int read() override {
    uint8_t b;
    return read(&b, 1) == 1 ? b : -1;
  }
  int read(uint8_t* data, size_t n) override { return fd_ < 0 ? -1 : static_cast<int>(recv(fd_, data, n, 0)); }
  int peek() override {
    uint8_t b;
    return fd_ >= 0 && recv(fd_, &b, 1, MSG_PEEK | MSG_DONTWAIT) == 1 ? b : -1;
  }
  void flush() override {}
  operator bool() override { return connected(); }

 private:
  int fd_ = -1;
  uint32_t timeout_ = 2000;
};
