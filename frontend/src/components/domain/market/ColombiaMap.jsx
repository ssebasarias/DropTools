import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const COLOMBIA_CENTER = [4.6, -74];
const COLOMBIA_ZOOM = 5;

/** Normalize department name for matching (lowercase, trim, remove accents). */
function normalizeName(name) {
    if (!name || typeof name !== 'string') return '';
    return name
        .trim()
        .toLowerCase()
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, '');
}

/** Build map: normalized name -> { orders, revenue } */
function buildRegionLookup(byRegion) {
    const lookup = new Map();
    if (!Array.isArray(byRegion)) return lookup;
    for (const r of byRegion) {
        const key = normalizeName(r.department);
        if (!key) continue;
        lookup.set(key, {
            orders: r.orders ?? 0,
            revenue: r.revenue ?? 0,
            avgShippingPrice: r.avg_shipping_price ?? 0,
            topCarrier: r.top_carrier ?? 'Sin transportadora',
            topCarrierOrders: r.top_carrier_orders ?? 0,
        });
    }
    return lookup;
}

/** Interpolate color by orders (min = default gray, max = primary green). */
function getFillColor(orders, maxOrders) {
    if (orders == null || orders <= 0) return 'rgba(148, 163, 184, 0.35)';
    if (maxOrders <= 0) return 'rgba(16, 185, 129, 0.5)';
    const t = Math.min(1, orders / maxOrders);
    const r = Math.round(148 + (16 - 148) * t);
    const g = Math.round(163 + (185 - 163) * t);
    const b = Math.round(184 + (129 - 184) * t);
    return `rgba(${r}, ${g}, ${b}, ${0.35 + 0.5 * t})`;
}

function FitBounds({ geojson }) {
    const map = useMap();
    useEffect(() => {
        if (!geojson?.features?.length) return;
        const layer = L.geoJSON(geojson);
        const bounds = layer.getBounds();
        if (!bounds.isValid()) return;
        map.fitBounds(bounds, { padding: [20, 20], maxZoom: 7 });
        map.setMaxBounds(bounds.pad(0.08));
        map.setMinZoom(map.getZoom());
    }, [map, geojson]);
    return null;
}

export default function ColombiaMap({ byRegion, style: containerStyle }) {
    const [geojson, setGeojson] = useState(null);
    const [loadError, setLoadError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        fetch('/colombia-deptos.geojson')
            .then((res) => {
                if (!res.ok) throw new Error('No se pudo cargar el mapa');
                return res.json();
            })
            .then((data) => {
                if (!cancelled) {
                    setGeojson(data);
                    setLoadError(null);
                }
            })
            .catch((err) => {
                if (!cancelled) setLoadError(err?.message || 'Error al cargar el mapa');
            });
        return () => { cancelled = true; };
    }, []);

    const regionLookup = useMemo(() => buildRegionLookup(byRegion), [byRegion]);
    const maxOrders = useMemo(() => {
        let max = 0;
        regionLookup.forEach((v) => { if (v.orders > max) max = v.orders; });
        return max;
    }, [regionLookup]);

    const geoJsonStyle = useMemo(() => {
        return (feature) => {
            const name = feature?.properties?.shapeName;
            const key = normalizeName(name);
            const stats = regionLookup.get(key);
            const orders = stats?.orders ?? 0;
            return {
                fillColor: getFillColor(orders, maxOrders),
                fillOpacity: 0.75,
                weight: 1.5,
                color: 'rgba(255,255,255,0.4)',
            };
        };
    }, [regionLookup, maxOrders]);

    const onEachFeature = useMemo(() => {
        return (feature, layer) => {
            const name = feature?.properties?.shapeName ?? 'Sin nombre';
            const key = normalizeName(name);
            const stats = regionLookup.get(key);
            const orders = stats?.orders ?? 0;
            const revenue = stats?.revenue ?? 0;
            const avgShippingPrice = stats?.avgShippingPrice ?? 0;
            const topCarrier = stats?.topCarrier ?? 'Sin transportadora';
            const topCarrierOrders = stats?.topCarrierOrders ?? 0;
            const fmt = (n) => (n == null || Number.isNaN(n)) ? '—' : new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n);
            layer.bindPopup(
                `<div style="min-width:140px;font-family:inherit;">
                  <strong>${name}</strong><br/>
                  Pedidos: ${orders}<br/>
                  Facturación: ${fmt(revenue)}<br/>
                  Flete prom.: ${fmt(avgShippingPrice)}<br/>
                  Top transportadora: ${topCarrier} (${topCarrierOrders})
                </div>`
            );
        };
    }, [regionLookup]);

    if (loadError) {
        return (
            <div style={{ minHeight: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid var(--glass-border)', color: 'var(--text-muted)' }}>
                {loadError}
            </div>
        );
    }

    if (!geojson) {
        return (
            <div style={{ minHeight: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid var(--glass-border)', color: 'var(--text-muted)' }}>
                Cargando mapa…
            </div>
        );
    }

    return (
        <div style={{ height: '100%', minHeight: '280px', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--glass-border)', ...containerStyle }}>
            <MapContainer
                center={COLOMBIA_CENTER}
                zoom={COLOMBIA_ZOOM}
                style={{ height: '100%', minHeight: '280px', background: 'var(--glass-bg)' }}
                zoomControl={true}
                scrollWheelZoom={false}
                maxBoundsViscosity={1.0}
                attributionControl={false}
            >
                <GeoJSON data={geojson} style={geoJsonStyle} onEachFeature={onEachFeature} />
                <FitBounds geojson={geojson} />
            </MapContainer>
        </div>
    );
}
