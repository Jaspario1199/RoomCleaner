# Station USB connection check — Rev A

2026-10-14. Target: one delivered XIAO ESP32-C3, powered only from a computer's USB data cable. Disconnect external wiring, driver, 12 V supply and battery. This isolated diagnostic is not the experimental motion controller and does not bypass its interlocks.

1. Install Arduino IDE and `esp32` by Espressif Systems through Boards Manager. If needed, add the stable package URL: https://espressif.github.io/arduino-esp32/package_esp32_index.json .
2. Select `XIAO_ESP32C3`, select its USB serial port, and enable `USB CDC On Boot` in Tools where the option is exposed.
3. Open `station_usb_check.ino` from its matching folder and upload.
4. Open Serial Monitor at 115200 baud. Expected text once per second: `RoomCleaner station: USB OK`.
5. Report successful output or the exact upload error. No physical pass has yet been recorded. This sketch has not been compiled with an ESP32 toolchain in this workspace.

If no port appears, confirm a data-capable cable. If the board will not upload, hold BOOT, press/release RESET, then release BOOT and reselect the port before uploading; after uploading, reset if needed and reselect the runtime port.

Next checkpoint: photograph both sides of one actual DROK regulator and A4988 carrier, plus motor and supply labels. Meter-check regulator output before connecting logic. Driver current limit, carrier sense resistors, mode straps, startup states and separate logic power must be established before motion. The old DRV8825 adapter is not the A4988 motor test firmware.

Sources: https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/ ; https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html ; https://docs.espressif.com/projects/arduino-esp32/en/latest/tutorials/cdc_dfu_flash.html .
