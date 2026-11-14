
import { useState } from "react";

const initialForm = {
  farmArea: "",
  areaUnit: "acre",

  soilType: "",
  soilPH: "",
  nitrogen: "",
  phosphorus: "",
  potassium: "",
  organicCarbon: "",
  salinity: "",

  currentCrop: "",
  previousCrop1: "",
  previousCrop2: "",
  previousCrop3: "",
  growingSeason: "",
  previousYield: "",

  fertilizerType: "",
  fertilizerQuantity: "",
  organicFertilizer: "",
  tillageMethod: "",
  residueManagement: "",

  irrigationAvailable: "",
  irrigationMethod: "",
  waterSource: "",
  waterAvailability: "",

  primaryGoal: "",
  preferredCrops: "",
  budget: "",
  planningDuration: "3",
};

const inputClass =
  "w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500";

const labelClass =
  "block text-sm font-medium text-gray-700 mb-1.5";

function Section({ title, description, children }) {
  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-gray-900">
          {title}
        </h3>
        <p className="text-sm text-gray-500 mt-1">
          {description}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {children}
      </div>
    </section>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      {children}
    </div>
  );
}

export default function FarmerInputForm({
  location,
  onSubmit,
}) {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");

    if (!location?.latitude || !location?.longitude) {
      setError("Please select your farm location first.");
      return;
    }

    if (
      !form.farmArea ||
      !form.currentCrop ||
      !form.previousCrop1 ||
      !form.irrigationAvailable ||
      !form.primaryGoal
    ) {
      setError("Please complete all required fields.");
      return;
    }

    const payload = {
      location: {
        latitude: location.latitude,
        longitude: location.longitude,
        placeName: location.placeName,
      },

      farm: {
        area: Number(form.farmArea),
        areaUnit: form.areaUnit,
        soilType: form.soilType || null,
      },

      soil: {
        pH: form.soilPH ? Number(form.soilPH) : null,
        nitrogen: form.nitrogen ? Number(form.nitrogen) : null,
        phosphorus: form.phosphorus ? Number(form.phosphorus) : null,
        potassium: form.potassium ? Number(form.potassium) : null,
        organicCarbon: form.organicCarbon
          ? Number(form.organicCarbon)
          : null,
        salinity: form.salinity ? Number(form.salinity) : null,
      },

      cropHistory: {
        currentCrop: form.currentCrop,
        previousCrops: [
          form.previousCrop1,
          form.previousCrop2,
          form.previousCrop3,
        ].filter(Boolean),
        growingSeason: form.growingSeason || null,
        previousYield: form.previousYield
          ? Number(form.previousYield)
          : null,
      },

      farmingPractices: {
        fertilizerType: form.fertilizerType || null,
        fertilizerQuantity: form.fertilizerQuantity
          ? Number(form.fertilizerQuantity)
          : null,
        organicFertilizer: form.organicFertilizer || null,
        tillageMethod: form.tillageMethod || null,
        residueManagement: form.residueManagement || null,
      },

      irrigation: {
        available: form.irrigationAvailable,
        method: form.irrigationMethod || null,
        waterSource: form.waterSource || null,
        waterAvailability: form.waterAvailability || null,
      },

      preferences: {
        primaryGoal: form.primaryGoal,
        preferredCrops: form.preferredCrops
          .split(",")
          .map((crop) => crop.trim())
          .filter(Boolean),
        budget: form.budget || null,
        planningDuration: Number(form.planningDuration),
      },
    };

    onSubmit?.(payload);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 space-y-8"
    >
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">
          Farm & Soil Assessment
        </h2>

        <p className="text-sm text-gray-500 mt-1">
          Provide your farm information to generate personalized
          soil health and crop rotation recommendations.
        </p>
      </div>

      {/* Selected Location */}
      <div className="bg-green-50 border border-green-100 rounded-lg p-4">
        <p className="text-sm font-semibold text-green-800">
          Selected Farm Location
        </p>

        {location ? (
          <>
            <p className="text-sm text-gray-700 mt-1">
              {location.placeName || "Selected farm"}
            </p>

            <p className="text-xs text-gray-500 mt-1">
              Latitude: {location.latitude.toFixed(5)} |
              Longitude: {location.longitude.toFixed(5)}
            </p>
          </>
        ) : (
          <p className="text-sm text-red-600 mt-1">
            Please select a location on the map first.
          </p>
        )}
      </div>

      {/* 1. Farm Information */}
      <Section
        title="1. Farm Information"
        description="Tell us about your agricultural land."
      >
        <Field label="Farm Area (Required)">
          <div className="flex gap-2">
            <input
              type="number"
              min="0.01"
              step="any"
              name="farmArea"
              value={form.farmArea}
              onChange={handleChange}
              placeholder="e.g. 5"
              className={inputClass}
              required
            />

            <select
              name="areaUnit"
              value={form.areaUnit}
              onChange={handleChange}
              className={inputClass}
            >
              <option value="acre">Acres</option>
              <option value="hectare">Hectares</option>
            </select>
          </div>
        </Field>

        <Field label="Soil Type">
          <select
            name="soilType"
            value={form.soilType}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select soil type</option>
            <option value="sandy">Sandy</option>
            <option value="clay">Clay</option>
            <option value="loamy">Loamy</option>
            <option value="silty">Silty</option>
            <option value="sandy_loam">Sandy Loam</option>
            <option value="unknown">Not sure</option>
          </select>
        </Field>
      </Section>

      <hr />

      {/* 2. Soil Information */}
      <Section
        title="2. Soil Information"
        description="Enter laboratory soil test results if available. Leave unknown values empty."
      >
        <Field label="Soil pH">
          <input
            type="number"
            name="soilPH"
            min="0"
            max="14"
            step="0.1"
            value={form.soilPH}
            onChange={handleChange}
            placeholder="e.g. 6.5"
            className={inputClass}
          />
        </Field>

        <Field label="Nitrogen (mg/kg)">
          <input
            type="number"
            min="0"
            step="any"
            name="nitrogen"
            value={form.nitrogen}
            onChange={handleChange}
            placeholder="e.g. 80"
            className={inputClass}
          />
        </Field>

        <Field label="Phosphorus (mg/kg)">
          <input
            type="number"
            min="0"
            step="any"
            name="phosphorus"
            value={form.phosphorus}
            onChange={handleChange}
            placeholder="e.g. 40"
            className={inputClass}
          />
        </Field>

        <Field label="Potassium (mg/kg)">
          <input
            type="number"
            min="0"
            step="any"
            name="potassium"
            value={form.potassium}
            onChange={handleChange}
            placeholder="e.g. 50"
            className={inputClass}
          />
        </Field>

        <Field label="Organic Carbon (%)">
          <input
            type="number"
            min="0"
            step="any"
            name="organicCarbon"
            value={form.organicCarbon}
            onChange={handleChange}
            placeholder="e.g. 1.2"
            className={inputClass}
          />
        </Field>

        <Field label="Soil Salinity (dS/m)">
          <input
            type="number"
            min="0"
            step="any"
            name="salinity"
            value={form.salinity}
            onChange={handleChange}
            placeholder="e.g. 1.5"
            className={inputClass}
          />
        </Field>
      </Section>

      <hr />

      {/* 3. Crop History */}
      <Section
        title="3. Crop History"
        description="Previous crops help the model understand your crop rotation pattern."
      >
        <Field label="Currently Growing (Required)">
          <select
            name="currentCrop"
            value={form.currentCrop}
            onChange={handleChange}
            className={inputClass}
            required
          >
            <option value="">Select current crop</option>
            {["Wheat", "Rice", "Cotton", "Maize", "Sugarcane",
              "Chickpea", "Lentils", "Soybean", "Mustard",
              "Other"].map((crop) => (
              <option key={crop} value={crop}>{crop}</option>
            ))}
          </select>
        </Field>

        <Field label="Previous Crop (Required)">
          <select
            name="previousCrop1"
            value={form.previousCrop1}
            onChange={handleChange}
            className={inputClass}
            required
          >
            <option value="">Select previous crop</option>
            {["Wheat", "Rice", "Cotton", "Maize", "Sugarcane",
              "Chickpea", "Lentils", "Soybean", "Mustard",
              "Other"].map((crop) => (
              <option key={crop} value={crop}>{crop}</option>
            ))}
          </select>
        </Field>

        <Field label="Crop Before That">
          <select
            name="previousCrop2"
            value={form.previousCrop2}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select crop (optional)</option>
            {["Wheat", "Rice", "Cotton", "Maize", "Sugarcane",
              "Chickpea", "Lentils", "Soybean", "Mustard",
              "Other"].map((crop) => (
              <option key={crop} value={crop}>{crop}</option>
            ))}
          </select>
        </Field>

        <Field label="Crop Before Previous">
          <select
            name="previousCrop3"
            value={form.previousCrop3}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select crop (optional)</option>
            {["Wheat", "Rice", "Cotton", "Maize", "Sugarcane",
              "Chickpea", "Lentils", "Soybean", "Mustard",
              "Other"].map((crop) => (
              <option key={crop} value={crop}>{crop}</option>
            ))}
          </select>
        </Field>

        <Field label="Current Growing Season">
          <select
            name="growingSeason"
            value={form.growingSeason}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select season</option>
            <option value="kharif">Kharif</option>
            <option value="rabi">Rabi</option>
            <option value="zaid">Zaid</option>
          </select>
        </Field>

        <Field label="Previous Crop Yield (tons/hectare)">
          <input
            type="number"
            min="0"
            step="any"
            name="previousYield"
            value={form.previousYield}
            onChange={handleChange}
            placeholder="e.g. 3"
            className={inputClass}
          />
        </Field>
      </Section>

      <hr />

      {/* 4. Fertilizer and Practices */}
      <Section
        title="4. Fertilizer & Farming Practices"
        description="Tell us about your existing soil management practices."
      >
        <Field label="Chemical Fertilizer Used">
          <select
            name="fertilizerType"
            value={form.fertilizerType}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select fertilizer</option>
            <option value="urea">Urea</option>
            <option value="dap">DAP</option>
            <option value="npk">NPK</option>
            <option value="other">Other</option>
            <option value="none">None</option>
          </select>
        </Field>

        <Field label="Fertilizer Quantity (kg/acre/season)">
          <input
            type="number"
            min="0"
            step="any"
            name="fertilizerQuantity"
            value={form.fertilizerQuantity}
            onChange={handleChange}
            placeholder="e.g. 50"
            className={inputClass}
          />
        </Field>

        <Field label="Organic Fertilizer">
          <select
            name="organicFertilizer"
            value={form.organicFertilizer}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select option</option>
            <option value="compost">Compost</option>
            <option value="farmyard_manure">Farmyard Manure</option>
            <option value="green_manure">Green Manure</option>
            <option value="none">None</option>
          </select>
        </Field>

        <Field label="Tillage Method">
          <select
            name="tillageMethod"
            value={form.tillageMethod}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select method</option>
            <option value="conventional">Conventional</option>
            <option value="minimum">Minimum Tillage</option>
            <option value="no_till">No-Till</option>
          </select>
        </Field>

        <Field label="Crop Residue Management">
          <select
            name="residueManagement"
            value={form.residueManagement}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select practice</option>
            <option value="left_in_field">Left in Field</option>
            <option value="removed">Removed</option>
            <option value="burned">Burned</option>
            <option value="incorporated">Mixed into Soil</option>
          </select>
        </Field>
      </Section>

      <hr />

      {/* 5. Irrigation */}
      <Section
        title="5. Water & Irrigation"
        description="Water availability helps identify suitable crops for your farm."
      >
        <Field label="Irrigation Available? (Required)">
          <select
            name="irrigationAvailable"
            value={form.irrigationAvailable}
            onChange={handleChange}
            className={inputClass}
            required
          >
            <option value="">Select option</option>
            <option value="yes">Yes</option>
            <option value="no">No (Rain-fed)</option>
          </select>
        </Field>

        <Field label="Irrigation Method">
          <select
            name="irrigationMethod"
            value={form.irrigationMethod}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select method</option>
            <option value="drip">Drip</option>
            <option value="sprinkler">Sprinkler</option>
            <option value="flood">Flood</option>
            <option value="furrow">Furrow</option>
            <option value="other">Other</option>
          </select>
        </Field>

        <Field label="Main Water Source">
          <select
            name="waterSource"
            value={form.waterSource}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select source</option>
            <option value="rainwater">Rainwater</option>
            <option value="groundwater">Groundwater</option>
            <option value="canal">Canal</option>
            <option value="river">River</option>
            <option value="other">Other</option>
          </select>
        </Field>

        <Field label="Water Availability">
          <select
            name="waterAvailability"
            value={form.waterAvailability}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select availability</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </Field>
      </Section>

      <hr />

      {/* 6. Farmer Preferences */}
      <Section
        title="6. Farming Objectives"
        description="Tell us what you want to achieve with your crop rotation."
      >
        <Field label="Primary Farming Goal (Required)">
          <select
            name="primaryGoal"
            value={form.primaryGoal}
            onChange={handleChange}
            className={inputClass}
            required
          >
            <option value="">Select your goal</option>
            <option value="improve_soil_health">
              Improve Soil Health
            </option>
            <option value="increase_yield">
              Increase Crop Yield
            </option>
            <option value="conserve_water">
              Conserve Water
            </option>
            <option value="improve_soil_fertility">
              Improve Soil Fertility
            </option>
            <option value="reduce_fertilizer">
              Reduce Fertilizer Dependency
            </option>
            <option value="multiple">
              Multiple Objectives
            </option>
          </select>
        </Field>

        <Field label="Budget">
          <select
            name="budget"
            value={form.budget}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="">Select budget</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </Field>

        <Field label="Preferred Crops (Comma separated)">
          <input
            type="text"
            name="preferredCrops"
            value={form.preferredCrops}
            onChange={handleChange}
            placeholder="Wheat, Cotton, Chickpea"
            className={inputClass}
          />
        </Field>

        <Field label="Rotation Planning Duration">
          <select
            name="planningDuration"
            value={form.planningDuration}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="2">2 Years</option>
            <option value="3">3 Years</option>
            <option value="5">5 Years</option>
          </select>
        </Field>
      </Section>

      {/* Submit */}
      <div className="pt-4 border-t border-gray-200">
        {error && (
          <p className="text-sm text-red-600 mb-3">{error}</p>
        )}

        <button
          type="submit"
          className="w-full py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition"
        >
          Analyze My Farm & Generate Recommendations
        </button>

        <p className="text-xs text-gray-500 text-center mt-3">
          Your information will be combined with available
          environmental and soil datasets.
        </p>
      </div>
    </form>
  );
}
