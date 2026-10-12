#include "TlsProbeConfig.h"
#include "TlsProbeWindow.h"
#include <cassert>
#include <string>
using namespace tlsmemoryprobe;
static bool line(Config& config, const std::string& value) {
  std::string mutableLine = value;
  return parseLine(config, mutableLine.data());
}
int main() {
  Config c;
  assert(line(c, "context=reader_ui"));
  assert(!line(c, "context=early_boot"));
  assert(line(c, "host=192.0.2.1"));
  assert(line(c, "ssid=synthetic"));
  assert(line(c, "password="));
  assert(line(c, "epoch=1800000000"));
  for (const char* key : {"tls12", "tls13", "wronghost", "stall", "drop"}) assert(line(c, std::string(key) + "=20000"));
  assert(complete(c));
  for (const char* bad : {"context=home", "host=https://host", "host=secret@host", "host=", "epoch=-1", "epoch=123", "epoch=9999999999999999999999", "tls12=0", "tls12=65536", "tls12=+3", "tls12=22z", "unknown=1", "ssid=a\tsecret"}) {
    Config invalid;
    assert(!line(invalid, bad));
  }
  Config tooLong;
  assert(!line(tooLong, "password=" + std::string(65, 'x')));
  assert(!complete(tooLong));
  {
    HeapWindow own;
    assert(own.owned());
    own.finish(); own.finish();
    assert(own.minimum == 90000 && own.stopResult == ESP_OK && own.stopCalled);
  }
  assert(stops == 1 && !heapActive);
  {
    HeapWindow own;
  }
  assert(stops == 2 && !heapActive);
  heapActive = true;
  {
    HeapWindow foreign;
    assert(!foreign.owned());
    foreign.finish();
    assert(!foreign.stopCalled);
  }
  assert(stops == 2 && heapActive);
  heapActive = false;
  failStop = 42;
  {
    HeapWindow failing;
    failing.finish();
    assert(failing.stopResult == 42);
  }
  assert(stops == 3 && heapActive);
}
