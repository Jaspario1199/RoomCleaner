#pragma once
// LEDC stand-in for the host build of firmware/claw_s3: records the pulse width the servo would see (test only).
#include "Arduino.h"
#include <cmath>
#ifndef STUB_ESP_ERR_T
#define STUB_ESP_ERR_T
typedef int esp_err_t;
#define ESP_OK 0
#endif
typedef int ledc_mode_t;
typedef int ledc_timer_t;
typedef int ledc_channel_t;
#define LEDC_LOW_SPEED_MODE 0
#define LEDC_TIMER_1 1
#define LEDC_CHANNEL_1 1
#define LEDC_TIMER_14_BIT 14
#define LEDC_AUTO_CLK 0
struct ledc_timer_config_t { int speed_mode, duty_resolution, timer_num, freq_hz, clk_cfg; };
struct ledc_channel_config_t { int gpio_num, speed_mode, channel, timer_sel; uint32_t duty; int hpoint; };
inline int g_servo_us = -1;      // last pulse written (what a real servo would see), from the duty at 50 Hz / 14 bit
inline uint32_t g_ledc_duty = 0;
inline esp_err_t ledc_timer_config(const ledc_timer_config_t*) { return ESP_OK; }
inline esp_err_t ledc_channel_config(const ledc_channel_config_t*) { return ESP_OK; }
inline esp_err_t ledc_set_duty(ledc_mode_t, ledc_channel_t, uint32_t d) { g_ledc_duty = d; return ESP_OK; }
inline esp_err_t ledc_update_duty(ledc_mode_t, ledc_channel_t) {
  g_servo_us = (int)std::lround(g_ledc_duty * 20000.0 / 16383.0);
  return ESP_OK;
}
