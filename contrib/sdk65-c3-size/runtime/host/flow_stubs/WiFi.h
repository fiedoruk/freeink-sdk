#pragma once
#include <Arduino.h>
constexpr int WIFI_STA = 1, WIFI_OFF = 0, WIFI_MODE_NULL = 0, WL_CONNECTED = 3;
struct WiFiStub {
  int currentMode = 0, begins = 0, offs = 0, disconnects = 0, persistentCalls = 0;
  bool connects = true, modeWorks = true;
  int getMode() { return currentMode; }
  void persistent(bool flag) { if (!flag) ++persistentCalls; }
  bool mode(int mode) { currentMode = mode; if (!mode) ++offs; return modeWorks; }
  void begin(const char*, const char*) { ++begins; }
  int status() { return currentMode == WIFI_STA && begins && connects ? WL_CONNECTED : 0; }
  void disconnect(bool, bool) { ++disconnects; }
};
inline WiFiStub WiFi;
