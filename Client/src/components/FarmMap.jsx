
import { useState, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  ZoomControl,
  useMapEvents,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const DEFAULT_POSITION = [30.3753, 69.3451];

// Map styles the user can switch between
const MAP_LAYERS = {
  satellite: {
    label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
    // place names drawn on top of the satellite photo
    labelsUrl:
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
  },
  street: {
    label: "Map",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
};

// Human (person) pin used as the map marker
const personIcon = L.divIcon({
  className: "", // remove Leaflet's default white box
  html: `
    <svg width="40" height="52" viewBox="0 0 40 52" xmlns="http://www.w3.org/2000/svg"
         style="filter:drop-shadow(0 3px 3px rgba(0,0,0,.45))">
      <!-- pin shape -->
      <path d="M20 51C20 51 38 32 38 19A18 18 0 0 0 2 19C2 32 20 51 20 51Z"
            fill="#16a34a" stroke="#ffffff" stroke-width="2.5"/>
      <!-- person: head + shoulders -->
      <circle cx="20" cy="14" r="5" fill="#ffffff"/>
      <path d="M10.5 28a9.5 9.5 0 0 1 19 0Z" fill="#ffffff"/>
    </svg>`,
  iconSize: [40, 52],
  iconAnchor: [20, 51], // the pin's tip sits exactly on the location
  popupAnchor: [0, -46], // popup opens above the pin
});

function MapClickHandler({ onSelect }) {
  useMapEvents({
    click(e) {
      onSelect([e.latlng.lat, e.latlng.lng]);
    },
  });

  return null;
}

function MapRecenter({ position }) {
  const map = useMap();

  useEffect(() => {
    map.setView(position, 13);
  }, [position, map]);

  return null;
}

export default function FarmMap({ onLocationSelect }) {
  const [position, setPosition] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selectedPlace, setSelectedPlace] = useState("");
  const [loading, setLoading] = useState(false); // search in progress
  const [locating, setLocating] = useState(false); // GPS in progress
  const [error, setError] = useState("");
  const [layer, setLayer] = useState("satellite");
  const tiles = MAP_LAYERS[layer];

  const currentPosition = position || DEFAULT_POSITION;

  // Select a location from any source
  const selectPosition = (coords, place = "Selected farm location") => {
    setPosition(coords);
    setSelectedPlace(place);
    setError("");
    setResults([]);

    onLocationSelect?.({
      latitude: coords[0],
      longitude: coords[1],
      placeName: place,
    });
  };

  // Search locations using Nominatim
  const searchLocation = async (e) => {
    e.preventDefault();

    if (!searchQuery.trim()) {
      setError("Please enter a location.");
      return;
    }

    setLoading(true);
    setError("");
    setResults([]);

    try {
      const params = new URLSearchParams({
        q: searchQuery,
        format: "jsonv2",
        limit: "5",
        addressdetails: "1",
      });

      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?${params}`,
        {
          headers: {
            "Accept-Language": "en",
          },
        }
      );

      if (!response.ok) {
        throw new Error("Location search failed. Please try again.");
      }

      const data = await response.json();

      if (data.length === 0) {
        setError("No locations found. Try another search.");
      } else {
        setResults(data);
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  // GPS location
  const getMyLocation = () => {
    if (!navigator.geolocation) {
      setError("Your browser doesn't support location. Search or click on the map instead.");
      return;
    }
    // Browsers only allow location on https:// or localhost
    if (!window.isSecureContext) {
      setError("Location only works on a secure (https) site. Search or click on the map instead.");
      return;
    }

    setLocating(true);
    setError("");
    setResults([]);

    const onSuccess = async (pos) => {
      const { latitude, longitude, accuracy } = pos.coords;
      const coords = [latitude, longitude];

      // Show the point right away, then try to get a real place name
      selectPosition(coords, `My location (±${Math.round(accuracy)} m)`);
      setLocating(false);

      try {
        const params = new URLSearchParams({
          lat: latitude,
          lon: longitude,
          format: "jsonv2",
          zoom: "14",
        });
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?${params}`, {
          headers: { "Accept-Language": "en" },
        });
        const data = await res.json();
        if (data?.display_name) selectPosition(coords, data.display_name);
      } catch {
        /* keep the "My location" label if the name lookup fails */
      }
    };

    const onError = (err) => {
      setLocating(false);
      if (err.code === err.PERMISSION_DENIED) {
        setError(
          "Location access is blocked. Click the 🔒 icon in your browser's address bar, allow Location, then try again."
        );
      } else if (err.code === err.TIMEOUT) {
        setError("Finding your location took too long. Try again, or search / click on the map.");
      } else {
        setError("Couldn't find your location. Turn on device location (or Wi-Fi) and try again.");
      }
    };

    // 1st try: precise GPS. If unavailable or slow (common on laptops),
    // retry once with normal accuracy (Wi-Fi / network based).
    navigator.geolocation.getCurrentPosition(
      onSuccess,
      (err) => {
        if (err.code === err.PERMISSION_DENIED) return onError(err);
        navigator.geolocation.getCurrentPosition(onSuccess, onError, {
          enableHighAccuracy: false,
          timeout: 15000,
          maximumAge: 5 * 60 * 1000,
        });
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
    );
  };

  // Select a search result
  const handleResultSelect = (result) => {
    selectPosition(
      [Number(result.lat), Number(result.lon)],
      result.display_name
    );

    setSearchQuery(result.display_name);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Map with floating controls */}
      <div className="relative h-[460px] sm:h-[520px]">
        <MapContainer
          center={currentPosition}
          zoom={5}
          className="h-full w-full"
          scrollWheelZoom={true}
          zoomControl={false}
        >
          <TileLayer key={layer} attribution={tiles.attribution} url={tiles.url} />
          {tiles.labelsUrl && <TileLayer key={`${layer}-labels`} url={tiles.labelsUrl} />}

          <ZoomControl position="bottomright" />

          <MapClickHandler onSelect={(coords) => selectPosition(coords)} />

          {position && (
            <>
              <MapRecenter position={position} />
              <Marker position={position} icon={personIcon}>
                <Popup>{selectedPlace}</Popup>
              </Marker>
            </>
          )}
        </MapContainer>

        {/* ---- Search (top-left) ---- */}
        <div className="absolute top-3 left-3 right-3 sm:right-auto sm:w-[380px] z-[1000]">
          <form
            onSubmit={searchLocation}
            className="flex items-center gap-1 p-1.5 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg ring-1 ring-black/5"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5 ml-2 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search city, village, country…"
              aria-label="Search location"
              className="flex-1 min-w-0 px-2 py-2 text-sm bg-transparent outline-none text-slate-900 placeholder:text-slate-400"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-xl hover:bg-green-700 disabled:opacity-50 transition"
            >
              {loading ? "…" : "Search"}
            </button>
          </form>

          {/* Results dropdown */}
          {results.length > 0 && (
            <div className="mt-2 max-h-64 overflow-y-auto bg-white/95 backdrop-blur-md rounded-2xl shadow-xl ring-1 ring-black/5 divide-y divide-slate-100">
              {results.map((result) => (
                <button
                  key={result.place_id}
                  type="button"
                  onClick={() => handleResultSelect(result)}
                  className="w-full flex items-start gap-3 text-left px-4 py-3 hover:bg-green-50 transition"
                >
                  <span className="mt-0.5 text-green-600" aria-hidden="true">📍</span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-slate-800 truncate">
                      {result.name || result.display_name}
                    </span>
                    <span className="block text-xs text-slate-500 truncate">
                      {result.display_name}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-2 px-4 py-2.5 text-sm text-red-700 bg-red-50/95 backdrop-blur rounded-xl shadow ring-1 ring-red-200">
              {error}
            </div>
          )}
        </div>

        {/* ---- Layer switch + GPS (top-right) ---- */}
        <div className="absolute top-16 sm:top-3 right-3 z-[1000] flex flex-col items-end gap-2">
          <div className="flex p-1 bg-white/90 backdrop-blur-md rounded-xl shadow-lg ring-1 ring-black/5">
            {Object.entries(MAP_LAYERS).map(([key, l]) => (
              <button
                key={key}
                type="button"
                onClick={() => setLayer(key)}
                aria-pressed={layer === key}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                  layer === key
                    ? "bg-slate-900 text-white shadow"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {key === "satellite" ? "🛰️ " : "🗺️ "}
                {l.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={getMyLocation}
            disabled={locating}
            title={locating ? "Finding your location…" : "Use my current location"}
            aria-label="Use my current location"
            className="flex items-center justify-center w-11 h-11 bg-white/90 backdrop-blur-md rounded-xl shadow-lg ring-1 ring-black/5 text-green-700 hover:bg-green-50 disabled:opacity-50 transition"
          >
            <svg viewBox="0 0 24 24" className={`w-5 h-5 ${locating ? "animate-spin" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="12" cy="12" r="3.5" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
              <circle cx="12" cy="12" r="7.5" />
            </svg>
          </button>
        </div>

        {/* ---- Selected location / hint (bottom) ---- */}
        <div className="absolute bottom-3 left-3 right-16 sm:right-auto sm:max-w-md z-[1000]">
          {position ? (
            <div className="flex items-start gap-3 p-3.5 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg ring-1 ring-black/5">
              <span className="flex items-center justify-center w-10 h-10 shrink-0 rounded-xl bg-green-100 text-xl" aria-hidden="true">
                🌾
              </span>
              <div className="min-w-0">
                <p className="text-[11px] font-semibold tracking-wide text-green-700 uppercase">
                  Selected farm location
                </p>
                <p className="text-sm font-medium text-slate-900 truncate" title={selectedPlace}>
                  {selectedPlace}
                </p>
                <p className="mt-0.5 font-mono text-xs text-slate-500">
                  {position[0].toFixed(5)}, {position[1].toFixed(5)}
                </p>
              </div>
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-white bg-slate-900/75 backdrop-blur rounded-full shadow">
              <span aria-hidden="true">👆</span>
              Search, use GPS, or click on the map to pick your farm
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
