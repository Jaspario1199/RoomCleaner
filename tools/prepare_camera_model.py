"""Fetch the manufacturer STEP linked in Seeed's mechanical resources; normalize axes."""
import io,zipfile,urllib.request,hashlib
import cadquery as cq
from pathlib import Path
URL='https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/seeed-studio-xiao-esp32s3-sense-3d_model.zip'
def main():
 data=urllib.request.urlopen(URL,timeout=45).read()
 out=Path('cad/exports/clamp_camera_v2');out.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  source=z.read('Seeed Studio XIAO-ESP32-S3-Sense.step')
 raw=out/'camera_manufacturer_source.step';raw.write_bytes(source)
 p=cq.importers.importStep(str(raw)).rotate((0,0,0),(0,0,1),90).rotate((0,0,0),(0,1,0),-90).translate((-6.1114,-1.805,13.71))
 cq.exporters.export(p,str(out/'camera_oem_normalized.step'))
 (out/'camera_source.txt').write_text(URL+'\nSTEP SHA256: '+hashlib.sha256(source).hexdigest()+'\nSource is Seeed model, not a measurement of delivered hardware.\n')
 print('Manufacturer camera model prepared')
if __name__=='__main__':main()
