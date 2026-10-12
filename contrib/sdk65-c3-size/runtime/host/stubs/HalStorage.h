#pragma once
#include <cstddef>
struct HalFile {
  size_t size();
  int read(void*, size_t);
  int read();
  int available();
};
struct StorageStub {
  bool openFileForRead(const char*, const char*, HalFile&);
};
extern StorageStub Storage;
