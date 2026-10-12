#pragma once
#include <Arduino.h>
inline int locksHeld = 0, locksCreated = 0;
struct HalPowerManager {
  struct Lock {
    Lock() { ++locksHeld; ++locksCreated; cpuMHz = 160; }
    ~Lock() { --locksHeld; }
  };
};
