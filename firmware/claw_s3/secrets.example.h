// Copy to secrets.h (git-ignored) and fill in. 2.4 GHz network only.
#pragma once
#define WIFI_SSID "your-network"
#define WIFI_PASS "your-password"
// Over-the-air update password (Arduino IDE asks for it when uploading to the network port). Pick your own.
#define OTA_PASS "change-me"
// Optional fixed address (recommended: the host config's claw.address must stay the same). Leave these three lines
// commented out to take whatever address the router hands out (printed on the Serial Monitor at boot).
// #define CLAW_IP IPAddress(192, 168, 1, 70)
// #define GATEWAY IPAddress(192, 168, 1, 1)
// #define SUBNET IPAddress(255, 255, 255, 0)
