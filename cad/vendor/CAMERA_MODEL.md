# Camera model provenance

Manufacturer mechanical resources: https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/#resources
Sense STEP archive: https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/seeed-studio-xiao-esp32s3-sense-3d_model.zip

Run `python -m tools.prepare_camera_model` before `python -m cad.clamp_camera_v2`.
The printable download includes the normalized OEM model. The model represents a supplier revision, not receipt or measured fit of the newly ordered camera.

Original model axes: board length X, stack Y, board width Z. Normalize to local U=-Z-6.1114,V=X-1.805,W=13.71-Y. Lens optical direction is negativeW. Motherboard 20.95 x17.78 x1.25; full model24.363 x17.78 x13.96 including USB/camera protrusions. Nominal lens centerU=.6386,V=6.945,W=.1; verify optical axis using actual image calibration.
