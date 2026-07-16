# RoomCleaner — Research Notes & Sources

Background research that informed the hardware and gripper choices. Prices are
2026 US estimates (±20%); verify current listings before buying.

## Gripper selection (mechanical, no vacuum)

The core problem: flat cloth on a hard floor gives a gripper nothing to close
around and no purchase against the floor. Working solutions **pierce** the fabric,
**pinch** it against a rigid anvil, or **scoop** a thin edge under it.

| Approach | Flat-cloth pickup | Buildability | Verdict |
|----------|-------------------|--------------|---------|
| Parallel-jaw alone | Poor | Buy/print, 1 servo | Needs a pinch/scoop trick added |
| Fin Ray soft fingers alone | Poor–fair | 3D-print TPU | Great *component*, weak alone |
| Underactuated tendon fingers | Fair | 3D-print + tendon | Good paired with a rake/scoop |
| **Scoop + soft flap (spatula)** | **Best mechanical** | Print + thin steel edge | **Primary pick** |
| **Needle/pin gripper** | **Best physics straight-down** | Moderate DIY | **Fallback pick** |
| Jamming/granular | Fair | Needs vacuum pump | Excluded (it's ~suction) |

**Decision:** prototype the **spatula-scoop + Fin Ray flap** first (safe, cheap,
all-printable); keep a **needle/pin head** as the fallback for thin flat socks.
Biggest reliability gain: **pinch/scoop against the floor**, never close in
mid-air.

Sources:
- IEEE, flat-surface gripper for limp material — https://ieeexplore.ieee.org/document/414922/
- IRI/UPC, "A Versatile Gripper for Cloth Manipulation" — http://www.iri.upc.edu/files/scidoc/2360-A-Versatile-Gripper-for-Cloth-Manipulation.pdf
- G.O.G. bimanual cloth gripper (arXiv 2401.10702) — https://arxiv.org/html/2401.10702v1
- Quad-Spatula gripper — https://www.researchgate.net/publication/342192971_The_Quad-Spatula_Gripper_A_Novel_Soft-Rigid_Gripper_for_Food_Handling
- Schmalz needle gripper SNG — https://www.schmalz.com/en/solutions/media-center/schmalz-needle-gripper-sng-m-for-handling-composite-textiles-and-preforms/
- CRG needle grippers — https://crgeoat.com/needle-grippers.html
- Fin Ray print-in-place (Thingiverse 6900815) — https://www.thingiverse.com/thing:6900815
- Fin Ray 3-finger TPU (Thingiverse 4894257) — https://www.thingiverse.com/thing:4894257
- Fin Ray adaptive gripper (Printables 621918) — https://www.printables.com/model/621918-fin-ray-adaptive-gripper-for-gobilda-pattern
- SINONING MG996R metal claw — https://www.sinoning.com/product/mechanical-claw-metal-mechanical-arm-gripper-with-mg996r-servo-robot/
- Amazon SZDoit metal claw — https://www.amazon.com/Mechanical-Robotic-Gripper-MG996R-Steering/dp/B099W5R2NP
- Single-servo 4-claw print (MakerWorld) — https://makerworld.com/en/models/2327544-mg996-single-servo-four-claw-gripper
- Trunk-inspired pinch-against-floor gripper — https://newatlas.com/robotics/kimm-trunk-inspired-robot-gripper/
- Jamming gripper needs vacuum (Make:) — https://makezine.com/projects/universal-robot-gripper/

## Bill of materials — product links

- NEMA 17 steppers: https://www.amazon.com/STEPPERONLINE-Stepper-Bipolar-Connector-compatible/dp/B00PNEQKC0 · 4-pack https://www.amazon.com/Stepper-Bipolar-Printer-Machine-Robotics/dp/B07BKRWK1Q
- Worm-gear DC + encoder: https://www.amazon.com/uxcell-50Kg-cm-Self-Locking-Encoder-Reduction/dp/B078J521TG · https://www.amazon.com/torque-turbine-encoder-strong-self-locking/dp/B08KWDN7CJ
- BTS7960/IBT-2 driver: https://www.amazon.com/HiLetgo-BTS7960-Driver-Arduino-Current/dp/B00WSN98DC
- TMC2209 drivers (5-pack): https://www.amazon.com/BIGTREETECH-DIRECT-TMC2209-Stepsticks-Motherboard/dp/B07ZQ3C1XW
- Raspberry Pi 5: https://www.amazon.com/Raspberry-Pi-8GB-SC1112-Quad-core/dp/B0CK2FCG1K · Pi price context https://www.raspberrypi.com/news/1gb-raspberry-pi-5-now-available-at-45-and-memory-driven-price-rises/
- ESP32 DevKit (2-pack): https://www.amazon.com/MELIFE-ESP32-DevKitC-Development-ESP32-WROOM-32U-Arduino/dp/B0811KLGDD
- 12 V 30 A PSU: https://www.amazon.com/SUPERNIGHT-Universal-Transformer-Industrial-Automation/dp/B007MWNF5Q
- Dyneema braid 100 lb: https://www.amazon.com/9KM-DWLIFE-Anti-Bite-Freshwater-Saltwater/dp/B0DLNQFQKK
- Logitech C920x: https://www.amazon.com/Logitech-C920x-Pro-HD-Webcam/dp/B085TFF7M1 · Pi Camera Module 3 https://www.amazon.com/Raspberry-Pi-Camera-Module/dp/B0BRY6MVXL
- MG996R servo (4-pack): https://www.amazon.com/4-Pack-MG996R-Torque-Digital-Helicopter/dp/B07MFK266B · SG90 https://www.amazon.com/Micro-Servos-Helicopter-Airplane-Controls/dp/B07MLR1498
- E-stop 22 mm NC: https://www.amazon.com/Uxcell-a14122300ux0109-Emergency-Latching-Mushroo/dp/B00W947PS0
- KW12-3 limit switches (10-pack): https://www.amazon.com/HiLetgo-KW12-3-Roller-Switch-Normally/dp/B07X142VGC
- 304 stainless eye screws: https://www.amazon.com/Stainless-Steel-Screws-Heavy-Inches/dp/B08SVMJ6NZ

> Note: Amazon returns HTTP 403 to automated price fetches, so prices in the BOM
> are conservative estimates from search results + market knowledge, not live
> quotes. Confirm before purchasing.
