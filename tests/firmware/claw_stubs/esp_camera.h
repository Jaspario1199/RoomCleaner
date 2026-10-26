#pragma once
#include "Arduino.h"
#ifndef STUB_ESP_ERR_T
#define STUB_ESP_ERR_T
typedef int esp_err_t;
#define ESP_OK 0
#endif
#define PIXFORMAT_JPEG 4
#define FRAMESIZE_SVGA 9
#define CAMERA_FB_IN_PSRAM 1
#define CAMERA_GRAB_LATEST 1
struct camera_config_t {
  int ledc_channel, ledc_timer;
  int pin_d0, pin_d1, pin_d2, pin_d3, pin_d4, pin_d5, pin_d6, pin_d7;
  int pin_xclk, pin_pclk, pin_vsync, pin_href, pin_sccb_sda, pin_sccb_scl, pin_pwdn, pin_reset;
  int xclk_freq_hz, pixel_format, frame_size, jpeg_quality, fb_count, fb_location, grab_mode;
};
struct sensor_t { int (*set_lenc)(sensor_t*, int); };
inline int stub_set_lenc(sensor_t*, int) { return 0; }
inline esp_err_t esp_camera_init(const camera_config_t*) { return ESP_OK; }
inline sensor_t* esp_camera_sensor_get() { static sensor_t s{stub_set_lenc}; return &s; }
struct camera_fb_t { uint8_t* buf; size_t len; };
inline camera_fb_t* esp_camera_fb_get() { static uint8_t b[4] = {0xFF, 0xD8, 0xFF, 0xD9}; static camera_fb_t f{b, 4}; return &f; }
inline void esp_camera_fb_return(camera_fb_t*) {}
