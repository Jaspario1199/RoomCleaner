"""
Approved materials and properties (authoritative).

Values are vendor-typical for FDM prints, NOT certified; treat as ±20 % and
design with margin (REQUIREMENTS R17 demands >=3x on structure, achieved >>10x).
Sources: filament manufacturer datasheets (Overture/Hatchbox/SUNLU typical).
"""

MATERIALS = {
    "PETG": {
        "use": "structural: frame, hub, standoffs, drum, cover, winch parts",
        "density_g_cm3": 1.27,
        "youngs_modulus_GPa": 2.1,
        "yield_MPa": 45.0,          # XY, well-bonded walls; derate 40 % for Z loads
        "max_service_C": 70,
    },
    "TPU95A": {
        "use": "tentacle fingers only (compliant)",
        "density_g_cm3": 1.21,
        "shore_hardness": "95A",
        "youngs_modulus_GPa": 0.08,  # order-of-magnitude; used only for curl feel
        "note": "heat-set inserts do NOT hold in TPU; screw threads carry <10 N only",
    },
    "PLA": {
        "use": "acceptable substitute for indoor, low-heat structural parts",
        "density_g_cm3": 1.24,
        "youngs_modulus_GPa": 3.5,
        "yield_MPa": 50.0,
        "max_service_C": 50,        # avoid near motors/sunlight
    },
}

PURCHASED_MASS_G = {
    "MG996R": 55, "ESP32_devkit": 10, "LiPo_2S_1000": 90,
    "buck_MP1584": 5, "switch_wiring_screws": 25,
}
