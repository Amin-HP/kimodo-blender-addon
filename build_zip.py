"""Build the installable add-on zip: dist/kimodo_npz_importer.zip

The zip contains a single ``kimodo_npz_importer/`` folder with ``__init__.py`` and
``blender_manifest.toml`` so it installs both as a Blender 4.2+ extension and as a
legacy add-on on older Blender versions.
"""

import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PKG = "kimodo_npz_importer"
FILES = ("__init__.py", "blender_manifest.toml")


def main():
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"{PKG}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in FILES:
            zf.write(os.path.join(ROOT, PKG, name), f"{PKG}/{name}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
