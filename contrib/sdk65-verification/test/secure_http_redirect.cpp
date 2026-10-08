#include "SecureHttpClient.h"
#include <iostream>
#include <string>

int main(int argc, char** argv) {
  if (argc != 3) return 2;
  freeink::SecureHttpClient http;
  http.setTimeout(1500);
  http.setFollowRedirects(std::stoi(argv[2]));
  if (!http.begin(argv[1])) return 3;
  http.addHeader("Authorization", "Bearer TEST-ONLY-TOKEN");
  const int status = http.GET();
  std::cout << "status=" << status << " body=" << http.getString() << "\n";
  http.end();
  return 0;
}
