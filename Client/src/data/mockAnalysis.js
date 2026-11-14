// Same shape as POST /api/analyze/ (see docs/API_CONTRACT.md and docs/mock_analyze.json).
// Used by <Charts /> until the real backend response is passed in.
const baseline = {
  overall: 62,
  water_fit: 60,
  climate_risk: 58,
  soil_health: 65,
  erosion_infiltration: 64,
  pest_break: 60,
  income: 55,
};

export const mockAnalysis = {
  analysis_id: 'mock-analysis-001',
  data_quality: { status: 'mock' },
  strategies: [
    {
      key: 'current',
      name: 'Current Rotation',
      description: 'Represents the existing crop rotation.',
      scores: baseline,
      baseline_scores: null,
    },
    {
      key: 'water_saver',
      name: 'Water Saver',
      description: 'Emphasizes water conservation and drought resilience.',
      scores: {
        overall: 78,
        water_fit: 88,
        climate_risk: 76,
        soil_health: 72,
        erosion_infiltration: 75,
        pest_break: 70,
        income: 60,
      },
      baseline_scores: baseline,
    },
    {
      key: 'soil_builder',
      name: 'Soil Builder',
      description: 'Emphasizes soil health, ground cover and erosion protection.',
      scores: {
        overall: 82,
        water_fit: 75,
        climate_risk: 78,
        soil_health: 90,
        erosion_infiltration: 88,
        pest_break: 82,
        income: 58,
      },
      baseline_scores: baseline,
    },
  ],
};
