// Copy to secrets.h (git-ignored). One file per station: change STATION_ID and
// STATION_IP; the host config's stations[].address must be "<STATION_IP>:8771".
#pragma once
#define STATION_ID "A"
#define WIFI_SSID "your-network"
#define WIFI_PASS "your-password"
#define STATION_IP IPAddress(192, 168, 1, 61)
#define GATEWAY IPAddress(192, 168, 1, 1)
#define SUBNET IPAddress(255, 255, 255, 0)
// Over-the-air update password (Arduino IDE asks for it when uploading to the network port). Pick your own.
#define OTA_PASS "change-me"
