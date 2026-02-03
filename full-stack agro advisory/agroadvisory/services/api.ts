// Define your interface to match the backend response exactly
interface AdvisoryResult {
  recommended_crop: string;
  location: string;
  message: string;
  coordinates: [number, number];
  alerts: string[];
  risk_level: 'low' | 'medium' | 'high';
}

interface FarmerInput {
  lat: number;
  lon: number;
  soil_type: string;
  n: number;
  p: number;
  k: number;
  ph: number;
  user_crop?: string;
}

export const fetchAdvisory = async (formData: FarmerInput): Promise<AdvisoryResult | null> => {
  try {
    const response = await fetch('http://127.0.0.1:8000/predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.statusText}`);
    }

    const data: AdvisoryResult = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to fetch advisory:", error);
    return null;
  }
};