#include <sys/time.h>
#include <cassert>
#include <string>
#include <Arduino.h>
#include <HalStorage.h>
#include <HalPowerManager.h>
#include <WiFi.h>
#include <esp_heap_caps.h>
inline int clockResult = 0;
inline int mockSetTimeOfDay(const timeval*, const void*) { assert(locksHeld == 1 && cpuMHz == 160); return clockResult; }
#define settimeofday mockSetTimeOfDay
#include "util/TlsMemoryProbe.cpp"
#undef settimeofday
#undef Serial
struct Display {
  uint32_t getBufferSize() { return 0; }
  uint8_t* getFrameBuffer() { return nullptr; }
} display;
#include "dispatch.inc"
struct RenderLock {
  enum class Mode { Try };
  explicit RenderLock(Mode) {}
  bool ownsLock() { return true; }
};
struct Section { bool isBuilding() { return false; } } mockSection;
inline Section* section = &mockSection;
inline unsigned long lastRenderCompleteMs = 1;
#include "reader.inc"
int main(int argc, char** argv) {
  assert(argc==2);
  const std::string scenario=argv[1];
#if !defined(CROSSPOINT_TLS_MEMORY_PROBE)
  Serial.input="CMD:G10\n"; dispatch();
  assert(Serial.input.empty() && WiFi.begins==0 && locksCreated==0);
#else
  const std::string config="context=reader_ui\nhost=127.0.0.1\nssid=test\npassword=\nepoch=1800000000\ntls12=1\ntls13=2\nwronghost=3\nstall=4\ndrop=5\n";
  Storage.files["/.crosspoint/g10/probe.conf"]=config;
  Storage.files["/.crosspoint/g10/root.pem"]="TEST CERT";
  Storage.files["/.crosspoint/g10/unknown.pem"]="UNKNOWN CERT";
  tlsmemoryprobe::earlyBoot();
  readyReader();
  assert(fakeConnects==0 && WiFi.begins==0);
  if(scenario=="wrong-command") {
    Serial.input="G\n"; dispatch(); readyReader();
    assert(fakeConnects==0 && WiFi.begins==0); return 0;
  }
  if(scenario=="foreign-radio") WiFi.currentMode=2;
  if(scenario=="prep-timeout") WiFi.connects=false;
  if(scenario=="mode-failure") WiFi.modeWorks=false;
  if(scenario=="clock-failure") clockResult=-1;
  if(scenario=="foreign-monitor") heapActive=true;
  if(scenario=="monitor-stop-failure") failStop=42;
  Serial.input="CMD:G10\n"; dispatch();
  assert(Serial.input.empty() && fakeConnects==0 && WiFi.begins==0);
  // Request survives unrelated idle/main iterations until the ready reader calls it.
  dispatch(); dispatch();
  lastRenderCompleteMs=0;
  readyReader();
  assert(fakeConnects==0 && WiFi.begins==0);
  lastRenderCompleteMs=1;
  readyReader();
  if(scenario=="foreign-radio") { assert(WiFi.currentMode==2 && WiFi.offs==0 && WiFi.begins==0); return 0; }
  if(scenario=="prep-timeout" || scenario=="mode-failure" || scenario=="clock-failure") {
    assert(WiFi.currentMode==0 && WiFi.offs==1 && WiFi.disconnects==1 && fakeConnects==0 && locksHeld==0); return 0;
  }
  if(scenario=="foreign-monitor" || scenario=="monitor-stop-failure") {
    assert(WiFi.currentMode==0 && WiFi.offs==1 && WiFi.disconnects==1 && locksHeld==0);
    assert(fakeConnects==(scenario=="foreign-monitor" ? 0 : 1));
    assert(stops==(scenario=="foreign-monitor" ? 0 : 1)); return 0;
  }
  assert(fakeConnects==1 && WiFi.currentMode==WIFI_STA && WiFi.offs==0 && locksHeld==0);
  assert(Serial.output.find("\"cpu_mhz\":160")!=std::string::npos);
  Serial.input="CMD:G10\nCMD:G10\n"; dispatch(); dispatch();
  for(int step=1;step<26;++step) readyReader();
  assert(fakeConnects==26 && WiFi.begins==1 && WiFi.persistentCalls==1 && WiFi.offs==1 && WiFi.disconnects==1 && locksHeld==0);
  readyReader();
  Serial.input="CMD:G10\n"; dispatch(); readyReader();
  assert(fakeConnects==26 && Serial.output.find("G10_END")!=std::string::npos);
#endif
}
