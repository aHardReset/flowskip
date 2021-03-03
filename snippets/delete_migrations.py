from pathlib import Path
import os

p = Path('.').parent
paths = [x for x in p.iterdir() if x.is_dir()]
for path in paths:
    migrations = (path/'migrations')
    if migrations.exists():
        for file in migrations.iterdir():
            if file.is_file() and not file.name == "__init__.py":
                print(file)
                os.remove(file)
