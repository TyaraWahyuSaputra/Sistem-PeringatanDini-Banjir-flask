"""
Artificial Neural Network Model for Flood Prediction
Compatible with existing realtime_data_controller.py
"""

import numpy as np
import pandas as pd
from datetime import datetime
import json
import os
import warnings
warnings.filterwarnings('ignore')

class FloodANN:
    def __init__(self):
        self.model_params = self._load_model_params()
        print("✅ Flood ANN Model initialized")
    
    def _load_model_params(self):
        """Load ANN model parameters (simulated trained model)"""
        # In a real application, this would load a trained model file
        # For now, we use simulated parameters based on typical flood prediction
        return {
            'weights_input': np.random.randn(5, 8) * 0.1,
            'weights_hidden': np.random.randn(8, 4) * 0.1,
            'weights_output': np.random.randn(4, 1) * 0.1,
            'bias_hidden': np.zeros((1, 8)),
            'bias_output': np.zeros((1, 4)),
            'feature_means': [50.0, 100.0, 70.0, 25.0, 30.0],  # rainfall, water_level, humidity, temp_min, temp_max
            'feature_stds': [30.0, 20.0, 15.0, 5.0, 5.0],
            'risk_thresholds': {
                'low': 0.3,
                'medium': 0.6,
                'high': 0.8
            }
        }
    
    def _sigmoid(self, x):
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-x))
    
    def _normalize_features(self, features):
        """Normalize input features"""
        features_np = np.array(features)
        means = np.array(self.model_params['feature_means'])
        stds = np.array(self.model_params['feature_stds'])
        
        # Avoid division by zero
        stds = np.where(stds == 0, 1, stds)
        
        normalized = (features_np - means) / stds
        return normalized.reshape(1, -1)  # Reshape to 2D array
    
    def predict(self, rainfall, water_level, humidity, temp_min, temp_max):
        """Predict flood risk using ANN"""
        try:
            # Prepare features
            features = [rainfall, water_level, humidity, temp_min, temp_max]
            X_normalized = self._normalize_features(features)
            
            # Get model parameters
            W1 = self.model_params['weights_input']
            W2 = self.model_params['weights_hidden']
            W3 = self.model_params['weights_output']
            b1 = self.model_params['bias_hidden']
            b2 = self.model_params['bias_output']
            
            # Forward propagation
            # Layer 1: Input to Hidden
            Z1 = np.dot(X_normalized, W1) + b1
            A1 = self._sigmoid(Z1)
            
            # Layer 2: Hidden to Hidden
            Z2 = np.dot(A1, W2) + b2
            A2 = self._sigmoid(Z2)
            
            # Layer 3: Hidden to Output
            Z3 = np.dot(A2, W3)
            risk_score = self._sigmoid(Z3)[0][0]
            
            # Determine risk level
            risk_level, status, message = self._interpret_risk(risk_score, rainfall, water_level)
            
            return {
                'risk_score': round(risk_score, 3),
                'risk_level': risk_level,
                'status': status,
                'message': message,
                'features': {
                    'rainfall': rainfall,
                    'water_level': water_level,
                    'humidity': humidity,
                    'temp_min': temp_min,
                    'temp_max': temp_max
                },
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"❌ ANN Prediction error: {e}")
            return self._get_fallback_prediction(rainfall, water_level)
    
    def _interpret_risk(self, risk_score, rainfall, water_level):
        """Interpret the risk score into categories"""
        thresholds = self.model_params['risk_thresholds']
        
        if risk_score < thresholds['low']:
            level = 'RENDAH'
            status = 'RENDAH'
            message = "Aman: Kondisi normal, tetap waspada"
        elif risk_score < thresholds['medium']:
            level = 'MENENGAH'
            status = 'MENENGAH'
            
            # Customize message based on conditions
            if rainfall > 100:
                message = "Siaga: Curah hujan tinggi, pantau terus"
            elif water_level > 120:
                message = "Siaga: Ketinggian air meningkat"
            else:
                message = "Siaga: Kondisi perlu pemantauan"
        else:
            level = 'TINGGI'
            status = 'TINGGI'
            
            if rainfall > 150 and water_level > 130:
                message = "WASPADA: Potensi banjir tinggi!"
            elif rainfall > 200:
                message = "WASPADA: Curah hujan ekstrem!"
            elif water_level > 140:
                message = "WASPADA: Ketinggian air kritis!"
            else:
                message = "WASPADA: Kondisi berbahaya!"
        
        return level, status, message
    
    def _get_fallback_prediction(self, rainfall, water_level):
        """Fallback prediction if ANN fails"""
        # Simple heuristic-based fallback
        risk_score = min(1.0, (rainfall * 0.003 + water_level * 0.005))
        
        if risk_score < 0.3:
            level, status, message = 'RENDAH', 'RENDAH', 'Prediksi fallback: Kondisi normal'
        elif risk_score < 0.6:
            level, status, message = 'MENENGAH', 'MENENGAH', 'Prediksi fallback: Siaga'
        else:
            level, status, message = 'TINGGI', 'TINGGI', 'Prediksi fallback: Waspada'
        
        return {
            'risk_score': round(risk_score, 3),
            'risk_level': level,
            'status': status,
            'message': message,
            'features': {
                'rainfall': rainfall,
                'water_level': water_level,
                'humidity': 75.0,
                'temp_min': 25.0,
                'temp_max': 30.0
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'is_fallback': True
        }


def predict_flood_ann(rainfall, water_level, humidity, temperature):
    """
    Simplified prediction function for realtime_data_controller.py
    """
    try:
        ann = FloodANN()
        result = ann.predict(rainfall, water_level, humidity, temperature, temperature + 2)
        return result
    except Exception as e:
        print(f"❌ Error in predict_flood_ann: {e}")
        return {
            'risk_score': 0.5,
            'risk_level': 'MENENGAH',
            'status': 'MENENGAH',
            'message': 'Error dalam prediksi ANN',
            'features': {
                'rainfall': rainfall,
                'water_level': water_level,
                'humidity': humidity,
                'temp_min': temperature,
                'temp_max': temperature + 2
            }
        }


def predict_flood_ann_with_temp_range(rainfall, water_level, humidity, temp_min, temp_max):
    """
    Extended prediction function for simulasi page
    """
    try:
        ann = FloodANN()
        result = ann.predict(rainfall, water_level, humidity, temp_min, temp_max)
        return result
    except Exception as e:
        print(f"❌ Error in predict_flood_ann_with_temp_range: {e}")
        return {
            'risk_score': 0.5,
            'risk_level': 'MENENGAH',
            'status': 'MENENGAH',
            'message': 'Error dalam prediksi ANN',
            'features': {
                'rainfall': rainfall,
                'water_level': water_level,
                'humidity': humidity,
                'temp_min': temp_min,
                'temp_max': temp_max
            }
        }


if __name__ == "__main__":
    # Test the model
    ann = FloodANN()
    
    # Test case 1: Normal conditions
    test1 = ann.predict(50, 100, 70, 25, 30)
    print("Test 1 (Normal):", test1['risk_level'], test1['risk_score'])
    
    # Test case 2: High rainfall
    test2 = ann.predict(150, 110, 80, 24, 29)
    print("Test 2 (High Rain):", test2['risk_level'], test2['risk_score'])
    
    # Test case 3: Extreme conditions
    test3 = ann.predict(250, 140, 90, 23, 28)
    print("Test 3 (Extreme):", test3['risk_level'], test3['risk_score'])