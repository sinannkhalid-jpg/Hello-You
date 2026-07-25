"use client";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// White-on-dark marker, no neon
const icon = L.divIcon({
  html: `<div style="background:#ffffff;width:12px;height:12px;border-radius:50%;border:2px solid #111111;"></div>`,
  className: "",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

export function IpMap({ lat, lng, label }: { lat: number; lng: number; label: string }) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={4}
      scrollWheelZoom
      style={{ height: "100%", width: "100%", background: "#111111" }}
      attributionControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
      />
      <CircleMarker center={[lat, lng]} radius={28} pathOptions={{ color: "#ffffff", fillColor: "#ffffff", fillOpacity: 0.1, weight: 1 }} />
      <Marker position={[lat, lng]} icon={icon}>
        <Popup>{label}</Popup>
      </Marker>
    </MapContainer>
  );
}
