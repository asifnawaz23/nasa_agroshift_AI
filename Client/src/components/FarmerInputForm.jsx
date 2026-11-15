import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { yupResolver } from "@hookform/resolvers/yup";
import * as yup from "yup";
import { getCrops } from "../services/api";

/*
  Simple farmer input form.
  - Location comes from <FarmMap /> via the `location` prop (Dashboard passes it).
  - On submit it calls onSubmit(payload); the payload follows
    POST /api/analyze/ in docs/API_CONTRACT.md.
*/

const PRIORITY_OPTIONS = [
  { value: "water", label: "Save water" },
  { value: "soil", label: "Improve soil health" },
  { value: "income", label: "Increase income" },
  { value: "erosion", label: "Prevent erosion" },
  { value: "pest", label: "Reduce pests & disease" },
];

const inputSchema = yup.object({
  location: yup
    .object({
      latitude: yup.number().required(),
      longitude: yup.number().required(),
      placeName: yup.string(),
    })
    .nullable()
    .required("Please select your farm location on the map."),

  farmArea: yup
    .number()
    .transform((value, original) => (original === "" ? undefined : value))
    .typeError("Enter a number")
    .positive("Area must be greater than 0")
    .required("Farm area is required"),
  areaUnit: yup.string().oneOf(["acre", "hectare"]).required(),

  soilType: yup.string(), // optional — backend uses soil data if empty
  currentCrop: yup.string().trim().required("Current crop is required"),

  waterAvailability: yup
    .string()
    .oneOf(["rainfed", "limited_irrigation", "irrigated"], "Select water availability")
    .required("Select water availability"),

  farmerPriorities: yup
    .array()
    .of(yup.string())
    .min(1, "Select at least one priority")
    .required("Select at least one priority"),
});

const defaultValues = {
  location: null,
  farmArea: "",
  areaUnit: "acre",
  soilType: "",
  currentCrop: "",
  waterAvailability: "",
  farmerPriorities: [],
};

const inputClass =
  "mt-1.5 block w-full px-3.5 py-2.5 text-sm text-gray-900 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500";
const labelClass = "block text-sm font-medium text-gray-700";
const errorClass = "mt-1 text-xs text-red-600";

// Convert form values to the backend request body
function toApiPayload(data) {
  // Selected priorities get top priority (5), unselected stay baseline (2)
  const priorities = { water: 2, soil: 2, income: 2, erosion: 2, pest: 2 };
  const selected = Array.isArray(data.farmerPriorities) ? data.farmerPriorities : [];
  selected.forEach((key) => {
    if (key in priorities) {
      priorities[key] = 5;
    }
  });

  return {
    lat: data.location.latitude,
    lon: data.location.longitude,
    // The backend expects { cycle_years, steps: [...] } or null.
    // null = use the typical rotation for this climate zone.
    current_rotation: null,
    // Extra info for the backend team (currently ignored by /api/analyze/)
    current_crop: data.currentCrop,
    priorities,
    constraints: {
      water_availability: data.waterAvailability,
      equipment: "standard",
      market_pref: "balanced",
    },
    overrides: { soil_texture: data.soilType || null },
    scenario: { rain_pct: 0, temp_c: 0 },
    lang: "en",
    // Not in the API contract yet — agree with backend before relying on it
    farm_area: { value: data.farmArea, unit: data.areaUnit },
  };
}

export default function FarmerInputForm({ location, onSubmit }) {
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(inputSchema),
    defaultValues,
  });

  // GET /api/crops/ -> options for the "Current crop" dropdown
  const [crops, setCrops] = useState([]);
  const [cropsError, setCropsError] = useState(false);
  useEffect(() => {
    getCrops()
      .then((data) => setCrops(data.results ?? []))
      .catch(() => setCropsError(true)); // fall back to a text box
  }, []);

  // When a location is picked on the map, put it into the form
  useEffect(() => {
    if (location) setValue("location", location, { shouldValidate: true });
  }, [location, setValue]);

  const submit = async (data) => {
    await onSubmit?.(toApiPayload(data));
  };

  return (
    <form
      onSubmit={handleSubmit(submit)}
      noValidate
      className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm space-y-5"
    >
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Farm Details</h2>
        <p className="text-sm text-gray-500 mt-1">
          Tell us about your farm to get crop rotation recommendations.
        </p>
      </div>

      {/* Location from the map */}
      <div
        className={`p-4 rounded-lg ${
          location ? "bg-green-50" : "bg-amber-50 border border-amber-200"
        }`}
      >
        {location ? (
          <>
            <p className="text-sm font-semibold text-green-800">
              📍 {location.placeName || "Selected farm"}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              Lat {location.latitude.toFixed(5)}, Lon {location.longitude.toFixed(5)}
            </p>
          </>
        ) : (
          <p className="text-sm text-amber-800">
            Select your farm location on the map above first.
          </p>
        )}
        {errors.location && <p className={errorClass}>{errors.location.message}</p>}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Farm area + unit */}
        <div>
          <label htmlFor="farmArea" className={labelClass}>
            Farm area
          </label>
          <div className="flex gap-2">
            <input
              id="farmArea"
              type="number"
              min="0"
              step="any"
              placeholder="e.g. 10"
              className={inputClass}
              aria-invalid={!!errors.farmArea}
              {...register("farmArea")}
            />
            <select
              aria-label="Area unit"
              className={`${inputClass} w-32`}
              {...register("areaUnit")}
            >
              <option value="acre">Acres</option>
              <option value="hectare">Hectares</option>
            </select>
          </div>
          {errors.farmArea && <p className={errorClass}>{errors.farmArea.message}</p>}
        </div>

        {/* Current crop */}
        <div>
          <label htmlFor="currentCrop" className={labelClass}>
            Current crop
          </label>
          {crops.length > 0 ? (
            <select
              id="currentCrop"
              className={inputClass}
              aria-invalid={!!errors.currentCrop}
              {...register("currentCrop")}
            >
              <option value="">Select a crop…</option>
              {crops.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="currentCrop"
              placeholder={cropsError ? "e.g. Wheat" : "Loading crops…"}
              className={inputClass}
              aria-invalid={!!errors.currentCrop}
              {...register("currentCrop")}
            />
          )}
          {errors.currentCrop && <p className={errorClass}>{errors.currentCrop.message}</p>}
        </div>

        {/* Soil type */}
        <div>
          <label htmlFor="soilType" className={labelClass}>
            Soil type <span className="text-gray-400">(optional)</span>
          </label>
          <select id="soilType" className={inputClass} {...register("soilType")}>
            <option value="">I don&apos;t know — use soil data</option>
            <option value="sandy">Sandy</option>
            <option value="loam">Loam</option>
            <option value="clay">Clay</option>
            <option value="silt">Silt</option>
          </select>
        </div>

        {/* Water availability */}
        <div>
          <label htmlFor="waterAvailability" className={labelClass}>
            Water availability
          </label>
          <select
            id="waterAvailability"
            className={inputClass}
            aria-invalid={!!errors.waterAvailability}
            {...register("waterAvailability")}
          >
            <option value="">Select…</option>
            <option value="rainfed">Rainfed only</option>
            <option value="limited_irrigation">Limited irrigation</option>
            <option value="irrigated">Fully irrigated</option>
          </select>
          {errors.waterAvailability && (
            <p className={errorClass}>{errors.waterAvailability.message}</p>
          )}
        </div>
      </div>

      {/* Priorities */}
      <fieldset>
        <legend className={labelClass}>
          What are your priorities? <span className="text-gray-400 font-normal">(select one or more)</span>
        </legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {PRIORITY_OPTIONS.map((p) => (
            <label
              key={p.value}
              className="cursor-pointer has-[:checked]:bg-green-600 has-[:checked]:text-white has-[:checked]:border-green-600 px-3.5 py-2 text-sm border border-gray-300 rounded-full text-gray-700 hover:border-green-500 transition"
            >
              <input
                type="checkbox"
                value={p.value}
                className="sr-only"
                {...register("farmerPriorities")}
              />
              {p.label}
            </label>
          ))}
        </div>
        {errors.farmerPriorities && (
          <p className={errorClass}>{errors.farmerPriorities.message}</p>
        )}
      </fieldset>

      {/* Buttons */}
      <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
        <button
          type="button"
          onClick={() => reset({ ...defaultValues, location: location ?? null })}
          className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
        >
          Reset
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2.5 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {isSubmitting ? "Analyzing…" : "Analyze my farm"}
        </button>
      </div>
    </form>
  );
}
