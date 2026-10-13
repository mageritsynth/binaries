import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/mageritsynth/binaries/main"

ruta_actual = Path(__file__).resolve().parents[0]

VERSION_RE = re.compile(r"^v(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def version_key(nombre_archivo, slug):
    """Extrae 'vX.Y[.Z]' de '<slug>_vX.Y[.Z].bin' y lo convierte en tupla
    de enteros para poder comparar cuál es la más alta."""
    version = nombre_archivo.removeprefix(f"{slug}_").removesuffix(".bin")
    match = VERSION_RE.match(version)
    if not match:
        return None, version
    mayor, menor, parche = match.groups()
    tupla = (int(mayor), int(menor or 0), int(parche or 0))
    return tupla, version


def sha256_de(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def fecha_de(ruta):
    return datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc).date().isoformat()


def cargar_changelog(slug):
    ruta = ruta_actual / slug / "changelog.json"
    if not ruta.exists():
        return {}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def entrada_para(ruta_bin, slug, changelog):
    version_tupla, version = version_key(ruta_bin.name, slug)
    cl = changelog.get(version)
    changelog_entry = None
    if cl:
        changelog_entry = {"es": cl.get("es"), "en": cl.get("en")}
    return version_tupla, {
        "version": version,
        "url": f"{RAW_BASE}/{slug}/{ruta_bin.name}",
        "sha256": sha256_de(ruta_bin),
        "date": fecha_de(ruta_bin),
        "changelog": changelog_entry,
    }


def construir_modulo(slug, info_icono):
    carpeta = ruta_actual / slug
    bins = sorted(carpeta.glob(f"{slug}_v*.bin"))
    if not bins:
        return None

    changelog = cargar_changelog(slug)
    entradas = [entrada_para(b, slug, changelog) for b in bins]
    entradas = [e for e in entradas if e[0] is not None]
    entradas.sort(key=lambda e: e[0])

    actual = entradas[-1][1]
    historial = [e[1] for e in reversed(entradas[:-1])]

    icono_path = ruta_actual / "icons" / f"{slug}.png"

    return {
        "slug": slug,
        "name": info_icono.get("name", slug.capitalize()),
        "chip": info_icono.get("chip", "unknown"),
        "icon_url": f"{RAW_BASE}/icons/{slug}.png" if icono_path.exists() else None,
        "manual_url": info_icono.get("manual_url"),
        "current": actual,
        "history": historial,
    }


def main():
    with open(ruta_actual / "icons" / "data.json", "r", encoding="utf-8") as f:
        iconos = json.load(f)

    modulos = []
    for slug, info in iconos.items():
        modulo = construir_modulo(slug, info)
        if modulo:
            modulos.append(modulo)
            print(f"{slug}: actual {modulo['current']['version']}, "
                  f"{len(modulo['history'])} version(es) en el historial")
        else:
            print(f"{slug}: sin binarios, omitido del manifest")

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modules": modulos,
    }

    ruta_manifest = ruta_actual / "manifest.json"
    with open(ruta_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\nEscrito {ruta_manifest}")


if __name__ == "__main__":
    main()
