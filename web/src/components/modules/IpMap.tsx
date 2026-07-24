"use client";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix default marker icon paths under bundlers
const icon = L.divIcon({
  html: `<div style="background:#00f0ff;width:14px;height:14px;border-radius:50%;box-shadow:0 0 16px rgba(0,240,255,0.8);border:2px solid #020617;"></div>`,
  className: "",
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

export function IpMap({ lat, lng, label }: { lat: number; lng: number; label: string }) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={4}
      scrollWheelZoom
      style={{ height: "100%", width: "100%", background: "#0b1020" }}
      attributionControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"
      />
      <CircleMarker center={[lat, lng]} radius={28} pathOptions={{ color: "#00f0ff", fillColor: "#00f0ff", fillOpacity: 0.15, weight: 1 }} />
      <Marker position={[lat, lng]} icon={icon}>
        <Popup>{label}</Popup>
      </Marker>
    </MapContainer>
  );
}
