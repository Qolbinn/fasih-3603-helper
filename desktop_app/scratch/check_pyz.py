from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.loader.pyimod01_archive import ZlibArchiveReader

p = 'desktop_app/dist/FASIH_3603_Helper/FASIH_3603_Helper.exe'
carc = CArchiveReader(p)
with open('desktop_app/scratch/latest_dist.pyz', 'wb') as f:
    f.write(carc.extract('PYZ.pyz'))

reader = ZlibArchiveReader('desktop_app/scratch/latest_dist.pyz')
np_keys = [k for k in reader.toc.keys() if 'numpy' in k]
openpyxl_keys = [k for k in reader.toc.keys() if 'openpyxl' in k]
print("Latest dist FASIH_3603_Helper.exe:")
print("numpy module count:", len(np_keys))
print("openpyxl module count:", len(openpyxl_keys))
