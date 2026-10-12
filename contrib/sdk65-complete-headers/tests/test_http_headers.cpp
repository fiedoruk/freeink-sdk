#include <SecureHttpClient.h>

#include <cassert>
#include <cstdio>

#include "test_secure_client_stubs.h"

static void setup(const std::string& reply, bool keepOpen) {
  FakeNet::replies() = {reply};
  FakeNet::requests().clear();
  FakeNet::hosts().clear();
  FakeNet::keepOpen() = keepOpen;
  fakeNow() = 0;
}
static int fetch(freeink::SecureHttpClient& http, std::string& body) {
  assert(http.begin("http://fixture.invalid/frame"));
  http.setTimeout(20);
  return http.GET([&](const uint8_t* data, size_t n) {
    body.append(reinterpret_cast<const char*>(data), n);
    return true;
  });
}
int main(int argc, char**) {
  if (argc > 1) {
    setup("HTTP/1.1 304 Not Modified\r\nETag: \"v1\"\r\n", false);
    freeink::SecureHttpClient http;
    std::string body;
    const int status = fetch(http, body);
    return status == 304 && http.responseComplete() ? 42 : 0;
  }
  for (const char* headers : {"", "Content-Length: 90000\r\n", "Transfer-Encoding: chunked\r\n"}) {
    setup(std::string("HTTP/1.1 304 Not Modified\r\nETag: \"v1\"\r\n") + headers + "\r\n", true);
    freeink::SecureHttpClient http;
    std::string body;
    assert(fetch(http, body) == 304 && http.responseComplete() && body.empty());
    assert(fakeNow() == 0);
  }
  setup("HTTP/1.1 204 No Content\r\n\r\n", true);
  {
    freeink::SecureHttpClient http;
    std::string body;
    assert(fetch(http, body) == 204 && http.responseComplete() && body.empty());
  }
  for (const auto& wire : {std::string("HTTP/1.1 304 Not Modified\r\nETag: \"v1\"\r\n"),
                           std::string("HTTP/1.1 304 Not Modified\r\nETag: \"v1\""),
                           std::string("HTTP/1.1 304 Not Modified\r\nETag: ") + std::string(4097, 'x') + "\r\n\r\n",
                           std::string("HTTP/1.1 200 OK\r\nContent-Length: 0\r\n")}) {
    for (bool open : {false, true}) {
      setup(wire, open);
      freeink::SecureHttpClient http;
      std::string body;
      assert(fetch(http, body) == -1 && !http.responseComplete() && body.empty());
    }
  }
  setup("HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc", false);
  {
    freeink::SecureHttpClient http;
    std::string body;
    assert(fetch(http, body) == 200 && http.responseComplete() && body == "abc");
  }
  setup("HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n", false);
  {
    freeink::SecureHttpClient http;
    std::string body;
    assert(fetch(http, body) == 200 && http.responseComplete() && body == "abc");
  }
  setup(
      "HTTP/1.1 304 Not Modified\r\nContent-Length: 90000\r\n\r\n"
      "HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc",
      true);
  {
    freeink::SecureHttpClient http;
    std::string body;
    assert(fetch(http, body) == 304 && http.responseComplete() && body.empty());
    assert(fetch(http, body) == 200 && http.responseComplete() && body == "abc");
    assert(FakeNet::hosts().size() == 1);
  }

  std::puts("HTTP complete-header/bodyless framing cases PASS");
}
