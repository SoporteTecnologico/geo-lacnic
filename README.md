# geo-lacnic

Listas de IPs por país (Argentina por defecto) generadas a diario desde los
datos oficiales de asignaciones de **LACNIC**, listas para importar en
MikroTik (`.rsc`) o usar como alias en pfSense (`.txt`).

## Cómo funciona

1. GitHub Actions corre `lacnic2rsc.py` todos los días a las 04:17 (hora Argentina).
2. El script baja `delegated-lacnic-extended-latest`, filtra por país,
   convierte los rangos a prefijos CIDR y los resume.
3. Si la lista cambió, la commitea en `output/`.
4. Cada MikroTik baja `output/AR.rsc` con un scheduler y la importa.

Si LACNIC falla o la lista viene con menos de 100 prefijos, el script aborta
sin escribir nada: los equipos siguen usando la última lista buena.

## Archivos

| Archivo | Para qué |
|---|---|
| `lacnic2rsc.py` | Conversor LACNIC → `.rsc` / `.txt` |
| `.github/workflows/geoip.yml` | Ejecución diaria programada |
| `mikrotik/instalar-geoip-AR.rsc` | Script + scheduler para cada MikroTik |
| `output/AR.rsc` | Address-list `AR` para RouterOS |
| `output/AR.txt` | Lista CIDR plana (pfSense URL Table, etc.) |

## Puesta en marcha

1. Crear un repositorio **público** en GitHub (ej. `geo-lacnic`) y subir estos archivos.
2. En el repo: **Settings > Actions > General > Workflow permissions** →
   *Read and write permissions* → Save.
3. Pestaña **Actions** → *Actualizar listas GeoIP (LACNIC)* → **Run workflow**
   para la primera ejecución. Verificar que aparezca `output/AR.rsc`.
4. En cada MikroTik: editar `mikrotik/instalar-geoip-AR.rsc`, reemplazar
   `<USUARIO>` y `<REPO>`, y pegarlo en la terminal.
5. Verificar en el equipo: `/ip firewall address-list print count-only where list=AR`
   (debería dar alrededor de 1600) y revisar `/log print where message~"geoip"`.
6. Recién con la lista cargada, agregar las reglas de firewall que la usan.

## Uso en pfSense

**Firewall > Aliases > URLs > Add** → Type: *URL Table (IPs)* →
URL: `https://raw.githubusercontent.com/<USUARIO>/<REPO>/main/output/AR.txt` →
Update frequency: 1 día.

## Notas

- **Antes de una regla `drop` con `!AR`**, confirmar que la lista tiene contenido.
  Con la lista vacía, un drop así bloquea a todos (incluido vos).
- Dejá siempre un camino alternativo (VPN, excepciones en `geo-excepciones`).
- Es la lista de **asignaciones** de LACNIC a entidades argentinas, no
  geolocalización: un cliente con IP de un proveedor extranjero (ej. Starlink)
  puede no figurar. Para esos casos, usar `geo-excepciones`.
- GitHub desactiva los workflows programados tras 60 días sin actividad en el
  repo; el archivo `output/last_run.txt` se actualiza en cada corrida para
  evitarlo. Si igual se desactiva, GitHub avisa por mail y se reactiva con un clic.
- Para más países: `--countries AR,UY,CL` en el workflow (solo región LACNIC).
