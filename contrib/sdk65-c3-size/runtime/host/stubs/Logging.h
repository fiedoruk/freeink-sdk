#pragma once
#include <Arduino.h>
inline SerialStub& logSerial = Serial;
#define Serial G10_DIRECT_SERIAL_IS_FORBIDDEN
