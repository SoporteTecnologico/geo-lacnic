#!/usr/bin/env python3
"""
lacnic2rsc.py — Genera address-lists de MikroTik por país usando los datos
oficiales de asignaciones de LACNIC (delegated stats).

Salidas por país (ej. AR):
  output/AR.rsc      -> para importar en MikroTik (/ip firewall address-list)
  output/AR.txt      -> lista CIDR plana (sirve también para un alias URL Table de pfSense)
  output/AR-v6.rsc   -> idem IPv6 (solo con --ipv6)
  output/AR-v6.txt
  output/last_run.txt

Solo cubre países de la región LACNIC (Latinoamérica y Caribe).
"""
import argparse
import datetime
import ipaddress
import pathlib
import sys
import urllib.request

SOURCES = [
    "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest",
    "https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest",
]
VALID_STATUS = {"allocated", "assigned"}


def download():
    last_err = None
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lacnic2rsc/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return url, r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"AVISO: no se pudo bajar {url}: {e}", file=sys.stderr)
    sys.exit(f"ERROR: ninguna fuente disponible ({last_err})")


def parse(data, countries, want_v6):
    nets = {cc: {"ipv4": [], "ipv6": []} for cc in countries}
    for line in data.splitlines():
        if not line or line.startswith("#"):
            continue
        p = line.split("|")
        if len(p) < 7:
            continue
        _registry, cc, typ, start, value, _date, status = p[:7]
        # Saltea la línea de versión, los resúmenes (start == "*") y otros países
        if cc not in nets or start == "*" or status not in VALID_STATUS:
            continue
        try:
            if typ == "ipv4":
                first = ipaddress.IPv4Address(start)
                last = first + int(value) - 1
                nets[cc]["ipv4"].extend(ipaddress.summarize_address_range(first, last))
            elif typ == "ipv6" and want_v6:
                nets[cc]["ipv6"].append(ipaddress.IPv6Network(f"{start}/{value}", strict=False))
        except ValueError as e:
            print(f"AVISO: línea ignorada ({e}): {line}", file=sys.stderr)
    for cc in nets:
        for fam in nets[cc]:
            nets[cc][fam] = list(ipaddress.collapse_addresses(nets[cc][fam]))
    return nets


def write_rsc(path, listname, nets, family, source, now):
    """
    Carga primero en una lista temporal (<lista>-new) y recién al final
    reemplaza la definitiva. Si el archivo llega cortado, el import falla
    antes del reemplazo y el equipo conserva la lista anterior intacta.
    """
    cmd = "/ip firewall address-list" if family == "ipv4" else "/ipv6 firewall address-list"
    tmp = f"{listname}-new"
    lines = [
        f"# {listname} ({family}) generado {now}",
        f"# Fuente: {source}",
        f"# Prefijos: {len(nets)}",
        f'{cmd} remove [find list="{tmp}"]',
        cmd,
    ]
    lines += [f'add list="{tmp}" address={n} comment="{listname} LACNIC"' for n in nets]
    lines += [
        f'{cmd} remove [find list="{listname}"]',
        f'{cmd} set [find list="{tmp}"] list="{listname}"',
        f':log info "{listname}: {len(nets)} prefijos cargados (lista del {now})"',
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_txt(path, nets):
    path.write_text("\n".join(str(n) for n in nets) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="LACNIC -> address-lists MikroTik por país")
    ap.add_argument("--countries", default="AR", help="Códigos ISO separados por coma (ej. AR,UY)")
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--ipv6", action="store_true", help="Generar también listas IPv6")
    ap.add_argument("--min-v4", type=int, default=100,
                    help="Mínimo de prefijos IPv4 esperados por país; si hay menos, aborta sin escribir")
    ap.add_argument("--input", help="Usar un archivo local en vez de descargar (para pruebas)")
    a = ap.parse_args()

    countries = [c.strip().upper() for c in a.countries.split(",") if c.strip()]
    if a.input:
        source, data = a.input, pathlib.Path(a.input).read_text(encoding="utf-8", errors="replace")
    else:
        source, data = download()

    nets = parse(data, countries, a.ipv6)

    # Control de cordura ANTES de escribir nada: si la fuente vino vacía o rota,
    # el workflow falla y los equipos siguen usando la última lista buena.
    for cc in countries:
        n = len(nets[cc]["ipv4"])
        if n < a.min_v4:
            sys.exit(f"ERROR: {cc} tiene solo {n} prefijos IPv4 (mínimo {a.min_v4}). No se escribe nada.")

    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for cc in countries:
        v4 = nets[cc]["ipv4"]
        write_rsc(out / f"{cc}.rsc", cc, v4, "ipv4", source, now)
        write_txt(out / f"{cc}.txt", v4)
        msg = f"{cc}: {len(v4)} prefijos IPv4"
        if a.ipv6:
            v6 = nets[cc]["ipv6"]
            write_rsc(out / f"{cc}-v6.rsc", cc, v6, "ipv6", source, now)
            write_txt(out / f"{cc}-v6.txt", v6)
            msg += f", {len(v6)} IPv6"
        print(msg)

    # Se escribe en cada corrida para que el repo tenga actividad:
    # GitHub desactiva los workflows programados tras 60 días sin actividad.
    (out / "last_run.txt").write_text(f"{now}\n{source}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
