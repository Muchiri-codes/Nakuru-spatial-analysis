"use client";
import React, { useState } from 'react';

interface AdvisoryResult {
  recommended_crop: string;
  location: string;
  message: string;
  coordinates: [number, number];
  alerts: string[];
  risk_level: 'low' | 'medium' | 'high';
}

export default function AgriApp() {
  const [formData, setFormData] = useState({
    n: 0, p: 0, k: 0, ph: 6.5, user_crop: ''
  });
  
  const [result, setResult] = useState<AdvisoryResult | null>(null);
  const [loading, setLoading] = useState(false);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          lat: -0.42, 
          lon: 36.95,
          soil_type: "loamy"
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      }
    } catch (error) {
      console.error("Connection failed:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4 mb-8">
        <input type="number" placeholder="N" onChange={e => setFormData({...formData, n: +e.target.value})} className="border p-2" />
        <input type="number" placeholder="P" onChange={e => setFormData({...formData, p: +e.target.value})} className="border p-2" />
        <input type="number" placeholder="K" onChange={e => setFormData({...formData, k: +e.target.value})} className="border p-2" />
        <input type="float" placeholder="pH" onChange={e => setFormData({...formData, ph: +e.target.value})} className="border p-2" />
        <input type="text" placeholder="Specific crop (optional)" onChange={e => setFormData({...formData, user_crop: e.target.value})} className="col-span-2 border p-2" />
        
        <button type="submit" className="col-span-2 bg-green-600 text-white p-3 rounded">
          {loading ? "Analyzing..." : "Get Advisory"}
        </button>
      </form>
      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      
          <div className="p-6 bg-white shadow rounded-xl border-l-4 border-green-500">
            <h3 className="text-gray-500 text-sm uppercase">AI Suggestion</h3>
            <p className="text-2xl font-bold">{result.recommended_crop}</p>
            <p className="text-gray-600 mt-2 text-sm">{result.location}</p>
          </div>

         
          <div className={`p-6 shadow rounded-xl border-l-4 ${result.risk_level === 'high' ? 'border-red-500' : 'border-blue-500'}`}>
            <h3 className="text-gray-500 text-sm uppercase">Viability Check</h3>
            <p className="text-sm mt-2 font-medium">{result.message}</p>
            <ul className="mt-3">
              {result.alerts.map((alert, i) => (
                <li key={i} className="text-xs text-red-600 flex items-center gap-1">
                  ⚠️ {alert}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}