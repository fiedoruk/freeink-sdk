#pragma once
#include <string>
#include <map>
#include <cstring>
struct HalFile {
  const std::string* contents = nullptr;
  size_t position = 0;
  size_t size() { return contents->size(); }
  int available() { return position < size(); }
  int read() { return available() ? static_cast<unsigned char>((*contents)[position++]) : -1; }
  int read(void* output, size_t length) {
    length = std::min(length, size()-position);
    memcpy(output, contents->data()+position, length); position += length; return static_cast<int>(length);
  }
};
struct StorageStub {
  std::map<std::string,std::string> files;
  bool openFileForRead(const char*, const char* path, HalFile& file) {
    auto found=files.find(path); if(found==files.end()) return false;
    file.contents=&found->second; return true;
  }
};
inline StorageStub Storage;
