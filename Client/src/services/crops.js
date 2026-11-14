// Crop + analysis calls. Implementation lives in ./api.js (shared base URL, errors).
export {
  getCrops as getCropsInfo,
  analyzeFarm as analyze,
  explainAnalysis as explain,
} from './api';
