# Mapa de zonas y distritos (Django REST + Next.js)

Backend en Django REST (Python 3.11+) que lee Postgres y expone dimensiones; frontend en Next.js 14 con Google Maps que pinta zonas/distritos por color.

> Nota: el host `postgres.railway.internal` no es accesible desde aquí (es interno de Railway). Conecta el backend desde la misma red o coloca una cadena `DATABASE_URL` accesible desde tu máquina para que el API lea las tablas reales.

## Backend (Django)

1) Crear entorno y dependencias

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

2) Variables de entorno (`backend/.env.example`):

- `DATABASE_URL`: cadena completa de Postgres.
- `MAP_*_FIELD`: nombres de columnas en la tabla de dimensiones (`MAP_TABLE` por defecto `dimensiones`).
- Opcional `MAP_WHERE_CLAUSE` para filtrar filas.

3) Ejecutar

```bash
python manage.py runserver 0.0.0.0:8000
```

4) Endpoints REST

- `GET /api/health/`
- `GET /api/dimensions/` → filas con `name, zone, district, latitude, longitude, value, color`.
- `GET /api/zones/` → agregado por zona con conteos y muestra.
- `GET /api/districts/` → agregado por distrito.

> Si tienes la BD disponible, puedes generar modelos con `python manage.py inspectdb > maps/models.py` para usar el ORM; el API actual usa SQL dinámico con los campos configurables.

## Frontend (Next.js 14 + Tailwind + Google Maps)

1) Variables (`frontend/.env.local.example`):

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api`
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=tu_api_key`

2) Instalar y levantar

```bash
cd frontend
npm install
npm run dev
```

3) Funcionalidad

- Mapa Google con pines coloreados por zona.
- Filtros por zona y distrito, leyenda de colores y resumen lateral.
- Usa datos reales del backend; si el API falla, muestra los puntos de ejemplo incluidos para que la UI siga funcionando.

## Flujo esperado

1. Ajusta `.env` en backend con tu `DATABASE_URL` y nombres de columnas reales.
2. Inicia el backend y verifica `http://localhost:8000/api/health/`.
3. Ajusta `.env.local` en frontend con la URL del backend y tu clave de Maps.
4. Levanta Next.js y verifica el mapa con los colores por zona/distrito.
