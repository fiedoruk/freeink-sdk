#pragma once
constexpr int WIFI_STA = 1;
constexpr int WIFI_OFF = 0;
constexpr int WIFI_MODE_NULL = 0;
constexpr int WL_CONNECTED = 3;
struct WiFiStub {
  bool mode(int);
  int getMode();
  void persistent(bool);
  void disconnect(bool, bool);
  void begin(const char*, const char*);
  int status();
};
extern WiFiStub WiFi;
