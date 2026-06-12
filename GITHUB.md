# Publicar PDS_2026 en GitHub

## 1. Inicializar repositorio (primera vez)

```powershell
cd PDS_2026
git init
git add .
git status
```

Verificar que **no** se incluyen: `venv/`, `out_/`, `logs/`, `*.xlsx` (excepto demo en `entrada_canonica/PDS_*.xlsx` si aplica).

## 2. Primer commit

```powershell
git commit -m "PDS_2026: plataforma PMO multicliente config-driven"
```

## 3. Crear repo en GitHub y subir

```powershell
git branch -M main
git remote add origin https://github.com/TU_ORG/PDS_2026.git
git push -u origin main
```

## 4. Clonar en otra máquina / cliente

```powershell
git clone https://github.com/TU_ORG/PDS_2026.git
cd PDS_2026
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python scripts/setup_cliente.py nuevo_cliente --name "Nuevo Cliente"
```

Seguir `GUIA_APLICACION_CLIENTE.md`.

## Política JLL

Antes de desplegar en infraestructura externa (Vercel, Azure público, etc.), obtener aprobación InfoSec.
Para prototipos usar **localhost** o repositorio privado interno.

## CI (GitHub Actions)

El workflow `.github/workflows/test.yml` ejecuta los tests en cada push/PR a `main`.
