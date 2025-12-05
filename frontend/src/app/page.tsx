'use client';

import { useEffect, useMemo, useState } from "react";
import { GoogleMap, HeatmapLayer, Polygon, useLoadScript } from "@react-google-maps/api";

type Dimension = {
  name?: string | null;
  zone?: string | null;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  value?: number | null;
  color?: string;
};

type ZoneSummary = {
  zone: string;
  color: string;
  count: number;
  district_count: number;
  sample: Dimension[];
};

type DistrictSummary = {
  district: string;
  color: string;
  count: number;
};

type DistrictPolygon = {
  id: number;
  code: string;
  name: string;
  color: string;
  polygons: { lat: number; lng: number }[][];
};

type HeatPoint = {
  lat?: number;
  lng?: number;
  latitude?: number;
  longitude?: number;
  count: number;
  device_id: number;
};

type FilterOption = { id: number; name: string };
type FilterSets = {
  moments: FilterOption[];
  altitude_levels: FilterOption[];
  signal_levels: FilterOption[];
  speed_levels: FilterOption[];
  operators: FilterOption[];
  networks: FilterOption[];
};

type Filters = {
  moment_id?: string;
  altitude_level_id?: string;
  signal_level_id?: string;
  speed_level_id?: string;
  operator_id?: string;
  network_id?: string;
  district_id?: string;
  date_from?: string;
  date_to?: string;
  time_from?: string;
  time_to?: string;
};

const API_BASE =  "http://localhost:8000/api";
const MAP_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ;

const mapContainerClass =
  "w-full h-[540px] rounded-3xl overflow-hidden border border-white/5 shadow-2xl shadow-black/30";

const mapLibraries: ("visualization")[] = ["visualization"];

const mapStyle: google.maps.MapTypeStyle[] = [
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#0f172a" }] },
  { featureType: "water", stylers: [{ color: "#0b3b60" }] },
  { featureType: "landscape", stylers: [{ color: "#0b1224" }] },
  { featureType: "administrative", elementType: "labels.text.fill", stylers: [{ color: "#8da2c0" }] },
];

function qs(filters: Filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v) params.append(k, v);
  });
  return params.toString();
}

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${path} devolvió ${res.status}`);
  }
  const body = await res.json();
  return (body.data ?? body) as T;
}

export default function Home() {
  const [dimensions, setDimensions] = useState<Dimension[]>([]);
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [districts, setDistricts] = useState<DistrictSummary[]>([]);
  const [districtPolygons, setDistrictPolygons] = useState<DistrictPolygon[]>([]);
  const [heatPoints, setHeatPoints] = useState<HeatPoint[]>([]);
  const [filterOptions, setFilterOptions] = useState<FilterSets>({
    moments: [],
    altitude_levels: [],
    signal_levels: [],
    speed_levels: [],
    operators: [],
    networks: [],
  });
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const defaultFilters: Filters = useMemo(
    () => ({ date_from: today, date_to: today, speed_level_id: "1" }),
    [today]
  );
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { isLoaded, loadError } = useLoadScript({
    googleMapsApiKey: MAP_KEY!,
    libraries: mapLibraries,
  });

  useEffect(() => {
    fetcher<FilterSets>("/filters/").then(setFilterOptions).catch(() => {});
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const query = qs(filters);
      try {
        const [dimRes, zoneRes, districtRes, polyRes, heatRes] = await Promise.allSettled([
          fetcher<Dimension[]>(`/dimensions/${query ? "?" + query : ""}`),
          fetcher<ZoneSummary[]>(`/zones/${query ? "?" + query : ""}`),
          fetcher<DistrictSummary[]>(`/districts/${query ? "?" + query : ""}`),
          fetcher<DistrictPolygon[]>("/district-polygons/"),
          fetcher<HeatPoint[]>(`/heatmap/${query ? "?" + query : ""}`),
        ]);

        setDimensions(dimRes.status === "fulfilled" ? dimRes.value : []);
        setZones(zoneRes.status === "fulfilled" ? zoneRes.value : []);
        setDistricts(districtRes.status === "fulfilled" ? districtRes.value : []);
        setDistrictPolygons(polyRes.status === "fulfilled" ? polyRes.value : []);
        setHeatPoints(heatRes.status === "fulfilled" ? heatRes.value : []);
        setError(null);
      } catch (err) {
        console.error(err);
        setError("No se pudo leer la base de datos.");
        setDimensions([]);
        setZones([]);
        setDistricts([]);
        setDistrictPolygons([]);
        setHeatPoints([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [filters]);

  const filteredDimensions = useMemo(() => {
    return dimensions.filter((item) => item.latitude && item.longitude);
  }, [dimensions]);

  const districtOptions = useMemo(() => districtPolygons.map((d) => ({ id: d.id, name: d.name })), [districtPolygons]);

  const mapCenter = useMemo(() => {
    if (districtPolygons.length && districtPolygons[0].polygons.length) {
      const pt = districtPolygons[0].polygons[0][0];
      return { lat: pt.lat, lng: pt.lng };
    }
    if (filteredDimensions.length) {
      return {
        lat: filteredDimensions[0].latitude as number,
        lng: filteredDimensions[0].longitude as number,
      };
    }
    return { lat: -17.7833, lng: -63.1821 };
  }, [filteredDimensions, districtPolygons]);

  const heatData = useMemo(
    () =>
      heatPoints
        .map((p) => {
          const lat = p.latitude ?? p.lat;
          const lng = p.longitude ?? p.lng;
          if (lat == null || lng == null) return null;
          return { location: new google.maps.LatLng(lat, lng), weight: p.count };
        })
        .filter(Boolean) as google.maps.visualization.WeightedLocation[],
    [heatPoints]
  );

  const districtLegend = useMemo(() => {
    return districtPolygons.map((d) => ({
      ...d,
      count: districts.find((x) => x.district === d.name)?.count ?? 0,
    }));
  }, [districtPolygons, districts]);

  return (
    <div className="min-h-screen p-6 sm:p-10 font-[family-name:var(--font-geist-sans)]">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-emerald-300/80">Monitoreo territorial</p>
              <h1 className="text-4xl sm:text-5xl font-semibold text-white drop-shadow-[0_10px_35px_rgba(34,197,94,0.35)]">
                Distritos coloreados y calor por puntos GPS
              </h1>
              <p className="text-sm text-slate-300 mt-2 max-w-2xl">
                Pintado por distrito usando dimdistrito y agrupando dispositivos quietos como heatmap para no saturar.
              </p>
            </div>
            <div className="glass-card px-4 py-3 text-sm text-slate-200">
              <p className="font-semibold">Backend</p>
              <p className="text-slate-300">Python 3.11.9 · Django REST</p>
              <p className="mt-1">
                API: <span className="text-emerald-300">{API_BASE}</span>
              </p>
            </div>
          </div>
          {error && <p className="text-amber-300 text-sm">{error}</p>}
          {loadError && <p className="text-rose-300 text-sm">Google Maps no pudo cargar: {loadError.message}</p>}
          {!MAP_KEY && (
            <p className="text-amber-300 text-sm">
              Falta NEXT_PUBLIC_GOOGLE_MAPS_API_KEY para mostrar el mapa real. Edita <code>.env.local</code>.
            </p>
          )}
        </header>

        <div className="grid md:grid-cols-3 gap-4">
          <StatCard label="Puntos" value={dimensions.length} />
          <StatCard label="Zonas" value={zones.length || new Set(dimensions.map((d) => d.zone)).size} />
          <StatCard
            label="Distritos"
            value={
              districtPolygons.length ||
              districts.length ||
              new Set(dimensions.map((d) => d.district)).size
            }
          />
        </div>

        <div className="glass-card p-4 grid gap-3 md:grid-cols-3">
          <FilterSelect
            label="Momento del día"
            value={filters.moment_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, moment_id: v || undefined }))}
            options={filterOptions.moments}
          />
          <FilterSelect
            label="Nivel altitud"
            value={filters.altitude_level_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, altitude_level_id: v || undefined }))}
            options={filterOptions.altitude_levels}
          />
          <FilterSelect
            label="Nivel señal"
            value={filters.signal_level_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, signal_level_id: v || undefined }))}
            options={filterOptions.signal_levels}
          />
          <FilterSelect
            label="Nivel velocidad"
            value={filters.speed_level_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, speed_level_id: v || undefined }))}
            options={filterOptions.speed_levels}
          />
          <FilterSelect
            label="Operador"
            value={filters.operator_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, operator_id: v || undefined }))}
            options={filterOptions.operators}
          />
          <FilterSelect
            label="Red"
            value={filters.network_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, network_id: v || undefined }))}
            options={filterOptions.networks}
          />
          <FilterSelect
            label="Distrito"
            value={filters.district_id ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, district_id: v || undefined }))}
            options={districtOptions}
          />
          <DateInput
            label="Fecha desde"
            value={filters.date_from ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, date_from: v || undefined }))}
          />
          <DateInput
            label="Fecha hasta"
            value={filters.date_to ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, date_to: v || undefined }))}
          />
          <TimeInput
            label="Hora desde"
            value={filters.time_from ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, time_from: v || undefined }))}
          />
          <TimeInput
            label="Hora hasta"
            value={filters.time_to ?? ""}
            onChange={(v) => setFilters((f) => ({ ...f, time_to: v || undefined }))}
          />
          <div className="md:col-span-3 flex justify-end">
            <button
              className="rounded-xl border border-emerald-400/50 bg-emerald-500/20 text-emerald-100 px-4 py-2 hover:bg-emerald-500/30 transition-colors"
              onClick={() => setFilters(defaultFilters)}
            >
              Quitar filtros
            </button>
          </div>
        </div>

        <section className="grid lg:grid-cols-[2fr_1fr] gap-6">
          <div className="space-y-4">
            <div className="glass-card p-4 flex flex-col gap-4">
              <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                {districtLegend.length
                  ? districtLegend.map((item) => (
                      <span
                        key={item.name}
                        className="inline-flex items-center gap-2 rounded-full px-3 py-1 bg-white/5 border border-white/10"
                      >
                        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                        {item.name} ({item.count} pts)
                      </span>
                    ))
                  : null}
              </div>
            </div>

            <div className="glass-card p-4">
              {isLoaded && MAP_KEY ? (
                <GoogleMap
                  mapContainerClassName={mapContainerClass}
                  center={mapCenter}
                  zoom={11}
                  options={{
                    disableDefaultUI: true,
                    zoomControl: true,
                    styles: mapStyle,
                  }}
                >
                  {districtPolygons
                    .filter((d) => !filters.district_id || String(d.id) === filters.district_id)
                    .map((district) =>
                      district.polygons.map((poly, idx) => (
                        <Polygon
                          key={`${district.id}-${idx}`}
                          path={poly}
                          options={{
                            fillColor: district.color,
                            fillOpacity: 0.25,
                            strokeColor: district.color,
                            strokeWeight: filters.district_id ? 2 : 1,
                          }}
                        />
                      ))
                    )}

                  {heatData.length ? (
                    <HeatmapLayer
                      key={`heat-${JSON.stringify(filters)}`}
                      data={[...heatData]}
                      options={{
                        radius: 28,
                        dissipating: true,
                        opacity: 0.85,
                        gradient: [
                          "rgba(0, 0, 255, 0)",
                          "rgba(0, 0, 255, 0.6)",
                          "rgba(0, 255, 255, 0.7)",
                          "rgba(0, 255, 0, 0.8)",
                          "rgba(255, 255, 0, 0.9)",
                          "rgba(255, 165, 0, 0.95)",
                          "rgba(255, 0, 0, 1)",
                          "rgba(179, 0, 0, 1)",
                        ],
                      }}
                    />
                  ) : null}

                  {/* Sin marcadores individuales; solo heatmap y pol?gonos */}
                </GoogleMap>
              ) : (
                <div className="h-[540px] flex items-center justify-center text-slate-300 text-sm">
                  {loading ? "Cargando datos..." : "Cargando Google Maps..."}
                </div>
              )}
            </div>
          </div>

          <aside className="glass-card p-5 space-y-4">
            <h3 className="text-lg font-semibold">Distritos (poligonos)</h3>
            <div className="space-y-3 max-h-[540px] overflow-y-auto pr-1">
              {(districtLegend.length
                ? districtLegend
                : districtOptions.map((name, idx) => ({ id: idx, name: name.name, color: "#22C55E", count: 0, polygons: [] as {lat:number;lng:number}[][] }))
              ).map((district) => (
                <div
                  key={district.id ?? district.name}
                  className="p-3 rounded-xl border border-white/5 bg-white/5 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: district.color }} />
                    <div>
                      <p className="font-medium">{district.name}</p>
                      {"code" in district && (district as DistrictPolygon).code ? (
                        <p className="text-xs text-slate-300">Codigo {(district as DistrictPolygon).code}</p>
                      ) : null}
                      <p className="text-xs text-slate-400">{district.count ?? 0} puntos</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass-card px-5 py-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className="text-3xl font-semibold text-white">{value}</p>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { id: number; name: string }[];
}) {
  return (
    <label className="text-sm text-slate-200 space-y-1 w-full">
      <span className="text-xs uppercase tracking-[0.15em] text-slate-400">{label}</span>
      <select
        className="w-full rounded-xl bg-slate-800/90 border border-slate-600/80 px-3 py-2 outline-none focus:ring-2 focus:ring-emerald-400/60 text-slate-100"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ color: "#e2e8f0", backgroundColor: "#1f2937" }}
      >
        <option value="">Todos</option>
        {options.map((opt) => (
          <option
            key={opt.id}
            value={opt.id}
            style={{ backgroundColor: "#1f2937", color: "#e2e8f0" }}
          >
            {opt.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function DateInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="text-sm text-slate-200 space-y-1 w-full">
      <span className="text-xs uppercase tracking-[0.15em] text-slate-400">{label}</span>
      <input
        type="date"
        className="w-full rounded-xl bg-slate-800/90 border border-slate-600/80 px-3 py-2 outline-none focus:ring-2 focus:ring-emerald-400/60 text-slate-100"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function TimeInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="text-sm text-slate-200 space-y-1 w-full">
      <span className="text-xs uppercase tracking-[0.15em] text-slate-400">{label}</span>
      <input
        type="time"
        className="w-full rounded-xl bg-slate-800/90 border border-slate-600/80 px-3 py-2 outline-none focus:ring-2 focus:ring-emerald-400/60 text-slate-100"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
