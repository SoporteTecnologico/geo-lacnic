# ============================================================
# GeoIP Argentina (LACNIC) para MikroTik RouterOS 7
# Pegar en la terminal (o /import) UNA sola vez por equipo.
#
# ANTES DE PEGAR: reemplazar <USUARIO> y <REPO> por los de GitHub.
# ============================================================

/system script
add name=geoip-AR policy=ftp,read,write,policy,test source={
  :local url "https://raw.githubusercontent.com/<USUARIO>/<REPO>/main/output/AR.rsc"
  :local archivo "geoip-AR.rsc"
  :do {
    /tool fetch url=$url dst-path=$archivo check-certificate=no
    :delay 3s
    # Control mínimo: si el archivo vino vacío o muy chico, no se toca la lista actual
    :if ([/file get [find name=$archivo] size] < 10000) do={
      :log warning "geoip-AR: archivo demasiado chico, se conserva la lista actual"
    } else={
      /import file-name=$archivo
    }
    /file remove [find name=$archivo]
  } on-error={
    :log warning "geoip-AR: falló la descarga, se conserva la lista actual"
  }
}

/system scheduler
add name=geoip-AR interval=1d start-time=05:23:00 on-event=geoip-AR \
  policy=ftp,read,write,policy,test comment="Actualiza address-list AR desde GitHub"

# Primera carga ahora
/system script run geoip-AR

# ------------------------------------------------------------
# Lista de excepciones (IPs fuera de Argentina que igual deben entrar).
# Ejemplo, agregar las que hagan falta:
# /ip firewall address-list add list=geo-excepciones address=203.0.113.10 comment="Martin viaje"
# ------------------------------------------------------------

# ------------------------------------------------------------
# EJEMPLOS DE USO EN EL FIREWALL (no se aplican solos, adaptar y pegar a mano)
#
# Winbox / SSH solo desde Argentina (mejor aún: solo por la VPN)
# /ip firewall filter add chain=input protocol=tcp dst-port=8291,22 \
#   src-address-list=!AR action=drop comment="Gestion solo desde AR" \
#   in-interface-list=WAN place-before=0
#
# Puerto de VPN solo desde Argentina o excepciones (ej. WireGuard 13231)
# /ip firewall filter add chain=input protocol=udp dst-port=13231 \
#   src-address-list=AR action=accept comment="WG desde AR"
# /ip firewall filter add chain=input protocol=udp dst-port=13231 \
#   src-address-list=geo-excepciones action=accept comment="WG excepciones"
# (ubicarlas antes del drop general de input en WAN)
# ------------------------------------------------------------
