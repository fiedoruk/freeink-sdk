#pragma once
#include <cstddef>
#include <cstdint>
using esp_err_t = int;
constexpr int ESP_OK = 0;
constexpr int ESP_FAIL = -1;
constexpr uint32_t MALLOC_CAP_INTERNAL = 1;
constexpr uint32_t MALLOC_CAP_8BIT = 2;
inline bool heapActive = false;
inline int starts = 0, stops = 0;
inline int failStop = 0;
inline size_t heap_caps_get_free_size(uint32_t) { return 100000; }
inline size_t heap_caps_get_largest_free_block(uint32_t) { return 50000; }
inline size_t heap_caps_get_minimum_free_size(uint32_t) { return heapActive ? 90000 : 80000; }
inline esp_err_t heap_caps_monitor_local_minimum_free_size_start() {
  ++starts;
  if (heapActive) return ESP_FAIL;
  heapActive = true;
  return ESP_OK;
}
inline esp_err_t heap_caps_monitor_local_minimum_free_size_stop() {
  ++stops;
  if (failStop) return failStop;
  if (!heapActive) return ESP_FAIL;
  heapActive = false;
  return ESP_OK;
}
