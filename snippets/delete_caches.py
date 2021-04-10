from pathlib import Path
import os

p = Path('.').parent
for file in p.glob('.cache*'):
    print(file)
    os.remove(file)
