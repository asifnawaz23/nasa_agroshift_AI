
import { useState, useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMapEvents,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const DEFAULT_POSITION = [30.3753, 69.3451];

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setLoading(true);
    setError("");

    navigator.geolocation.getCurrentPosition(
      (location) => {
        selectPosition([
          location.coords.latitude,
          location.coords.longitude,
        ], "Current GPS location");

        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
      }
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
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">

      {/* Header */}
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-gray-900">
          Select Your Farm Location
        </h2>

        <p className="text-sm text-gray-500 mt-1">
          Search any location worldwide or select it directly on the map.
        </p>
      </div>

      {/* Search Input */}
      <form
        onSubmit={searchLocation}
        className="flex flex-col sm:flex-row gap-2 mb-3"
      >
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search city, village, country..."
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-green-500"
        />

        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Search Results */}
      {results.length > 0 && (
        <div className="border border-gray-200 rounded-lg mb-4 divide-y divide-gray-100">
          {results.map((result) => (
            <button
              key={result.place_id}
              type="button"
              onClick={() => handleResultSelect(result)}
              className="w-full text-left px-4 py-3 hover:bg-green-50 transition"
            >
              <p className="text-sm font-medium text-gray-800">
                {result.name || result.display_name}
              </p>

              <p className="text-xs text-gray-500 mt-1">
                {result.display_name}
              </p>
            </button>
          ))}
        </div>
      )}

      {/* GPS Button */}
      <button
        onClick={getMyLocation}
        disabled={loading}
        className="mb-4 px-4 py-2 text-sm font-medium border border-green-600 text-green-700 rounded-lg hover:bg-green-50 disabled:opacity-50"
      >
        📍 Use My Current Location
      </button>

      {/* Map */}
      <div className="h-[380px] w-full rounded-lg overflow-hidden">
        <MapContainer
          center={currentPosition}
          zoom={5}
          className="h-full w-full"
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapClickHandler
            onSelect={(coords) =>
              selectPosition(coords)
            }
          />

          {position && (
            <>
              <MapRecenter position={position} />

              <Marker position={position}>
                <Popup>{selectedPlace}</Popup>
              </Marker>
            </>
          )}
        </MapContainer>
      </div>

      {/* Errors */}
      {error && (
        <p className="text-sm text-red-600 mt-3">
          {error}
        </p>
      )}

      {/* Selected Location */}
      {position && (
        <div className="mt-4 p-4 bg-green-50 rounded-lg">
          <h3 className="font-semibold text-green-800">
            Selected Farm Location
          </h3>

          <p className="text-sm text-gray-700 mt-2">
            {selectedPlace}
          </p>

          <p className="text-sm text-gray-700 mt-1">
            Latitude: {position[0].toFixed(6)}
          </p>

          <p className="text-sm text-gray-700">
            Longitude: {position[1].toFixed(6)}
          </p>
        </div>
      )}

      {!position && (
        <p className="text-sm text-gray-500 mt-3">
          Search a location, use GPS, or click directly on the map.
        </p>
      )}

    </div>
  );
}
