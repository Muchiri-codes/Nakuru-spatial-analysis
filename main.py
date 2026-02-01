import pandas as pd
import requests
import datetime
import joblib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional


app = FastAPI(title="Farmer Advisory API")

# Enable CORS so Next.js can communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)


try:
    df = pd.read_csv('crop_recommendation.csv')
    model = joblib.load("farmer_advisory_model.pkl")
    CROP_RANGES = df.groupby('label').agg(['min', 'max']).to_dict()
except Exception as e:
    print(f"Error loading core files: {e}")


crop_months = {
    'rice': [3, 4, 5, 10, 11], 'maize': [3, 4, 9, 10], 'chickpea': [1, 2, 11, 12],
    'kidneybeans': [5, 6], 'pigeonpeas': [6, 7], 'mothbeans': [7, 8],
    'mungbean': [8, 9], 'blackgram': [6, 7, 8], 'lentil': [1, 2, 11, 12],
    'pomegranate': list(range(1, 13)), 'banana': list(range(1, 13)),
    'mango': [1, 2, 3], 'grapes': [11, 12, 1, 2], 'watermelon': [1, 2, 3],
    'muskmelon': [1, 2, 3], 'apple': [1, 2, 11, 12], 'orange': list(range(1, 13)),
    'papaya': list(range(1, 13)), 'coconut': list(range(1, 13)),
    'cotton': [5, 6, 7, 8], 'jute': [3, 4, 5], 'coffee': list(range(1, 13))
}

# SCHEMAS For Next.js Request
class FarmerRequest(BaseModel):
    lat: float
    lon: float
    soil_type: str
    n: float
    p: float
    k: float
    ph: float
    user_crop: Optional[str] = None


#LOGIC FUNCTIONS
def get_location_name(lat, lon):
    api_key = "d16ca93ca7c89a66afa56bd31a522391"
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status() 
        return response.json().get('name', 'Unknown Location')
    except:
        return 'Unknown Location'

def risk_assessment(humidity, rainfall, temperature):
    risk_score = 0
    factors = []
    if humidity > 80 and 20 <= temperature <= 30:
        risk_score += 60
        factors.append("Heavy rainfall and warmth: Your crops are at risk of fungal blight.")
    if rainfall > 200:
        risk_score += 20
        factors.append("Heavy rainfall: Monitor for water-borne pests.")
    if rainfall < 20 and temperature > 35:
        risk_score += 70
        factors.append("Extreme heat and low rainfall: Your crops are at high risk of wilting.")
    
    level = "low"
    if risk_score > 70: level = "high"
    elif risk_score > 40: level = 'medium'
    return {"level": level, "score": risk_score, "warnings": factors}

def openmeteo_monthly_weather(lat, lon):
    today = datetime.datetime.now()
    year = today.year - 1
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
        "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation"],
        "timezone": "Africa/Nairobi"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        df_weather = pd.DataFrame({
            'time': pd.to_datetime(data['hourly']['time']),
            'temperature': data['hourly']['temperature_2m'],
            'humidity': data['hourly']['relative_humidity_2m'],
            'rainfall': data['hourly']['precipitation']
        })
        df_weather.set_index('time', inplace=True)
        monthly_data = df_weather.resample('ME').agg({'temperature': 'mean', 'humidity': 'mean', 'rainfall': 'sum'})
        latest = monthly_data.iloc[today.month - 1]
        return latest['temperature'], latest['humidity'], latest['rainfall'], "Success"
    except:
        return 25.0, 70.0, 100.0, "Fallback"

def check_crop_viability(crop_name, temperature, humidity, ph, rainfall):
    crop_name = crop_name.lower().strip()
    if crop_name not in df['label'].unique():
        return False, f"Sorry, '{crop_name}' is not in our database yet."
    
    issues = []
    def is_outside(val, col):
        low = CROP_RANGES[(col, 'min')][crop_name]
        high = CROP_RANGES[(col, 'max')][crop_name]
        if val < low: return f"too low (ideal: {low:.1f}-{high:.1f})"
        if val > high: return f"too high (ideal: {low:.1f}-{high:.1f})"
        return None

    checks = {'temperature': temperature, 'humidity': humidity, 'ph': ph, 'rainfall': rainfall}
    for label, value in checks.items():
        err = is_outside(value, label)
        if err: issues.append(f"{label.capitalize()} is {err}")

    if not issues:
        return True, f"Conditions are perfect! {crop_name.capitalize()} thrives here."
    return False, f"Warning for {crop_name}: " + " | ".join(issues)

# API ENDPOINTS

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.post("/predict")
async def get_advice(req: FarmerRequest):
    # 1. Fetch Location and Weather
    location_name = get_location_name(req.lat, req.lon)
    temp, hum, rain, _ = openmeteo_monthly_weather(req.lat, req.lon)
    
    # 2. ML Prediction
    input_data = pd.DataFrame([{
        'N': req.n, 'P': req.p, 'K': req.k,
        'temperature': temp, 'humidity': hum, 'ph': req.ph, 'rainfall': rain
    }])
    prediction = model.predict(input_data)[0]
    
    # 3. Risk and Validation
    risk_info = risk_assessment(hum, rain, temp)
    month_name = datetime.datetime.now().strftime("%B")
    
    viability_msg = ""
    if req.user_crop:
        _, viability_msg = check_crop_viability(req.user_crop, temp, hum, req.ph, rain)

    # 4. Response Construction
    return {
        "location": f"{location_name}",
        "coordinates": [req.lat, req.lon],
        "recommended_crop": prediction,
        "risk_level": risk_info["level"],
        "alerts": risk_info["warnings"],
        "weather": {"temp": round(temp, 1), "humidity": round(hum, 1), "rainfall": round(rain, 1)},
        "message": (
            f"It is {month_name} in {location_name}. "
            f"Conditions: {temp:.1f}°C, {rain:.1f}mm rain. "
            f"{viability_msg if req.user_crop else f'Our AI suggests planting {prediction}.'} "
            f"Risk level: {risk_info['level']}."
        )
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)