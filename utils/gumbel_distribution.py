"""
Gumbel Distribution Analysis for Extreme Value Prediction
Compatible with existing realtime_data_controller.py
"""

import numpy as np
import math
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class GumbelDistribution:
    def __init__(self):
        self.historical_data = self._load_historical_data()
        print("✅ Gumbel Distribution Model initialized")
    
    def _load_historical_data(self):
        """Load historical rainfall data for Gumbel analysis"""
        # Simulated historical rainfall data (mm) - 10 years of monthly maxima
        # In real application, this would come from a database
        return {
            'Ngadipiro': [
                45.2, 52.1, 48.7, 55.3, 60.2, 65.8, 70.1, 68.4, 62.3, 58.9, 51.2, 47.8,
                50.3, 54.2, 49.8, 57.1, 62.8, 67.2, 72.5, 69.8, 64.1, 59.4, 53.7, 49.2,
                47.5, 51.8, 50.2, 56.3, 61.7, 66.3, 71.2, 67.9, 63.5, 57.8, 52.9, 48.5
            ],
            'Wonogiri': [
                38.5, 42.3, 40.1, 46.8, 52.4, 58.7, 63.2, 60.8, 55.3, 50.2, 44.7, 41.3,
                41.2, 44.8, 42.5, 48.9, 54.1, 59.6, 64.8, 62.1, 56.9, 51.7, 46.3, 42.8,
                39.8, 43.5, 41.8, 47.6, 53.2, 58.1, 62.9, 60.2, 54.8, 49.6, 45.2, 41.7
            ],
            'Colo Weir': [
                35.2, 38.7, 36.9, 42.5, 47.8, 53.4, 58.1, 55.7, 50.4, 46.3, 40.8, 37.5,
                37.8, 40.2, 38.5, 44.1, 49.3, 54.7, 59.3, 56.8, 51.5, 47.2, 42.6, 39.1,
                36.4, 39.8, 37.9, 43.7, 48.9, 53.8, 58.6, 56.1, 50.9, 46.7, 41.9, 38.3
            ]
        }
    
    def _calculate_gumbel_parameters(self, data):
        """Calculate Gumbel distribution parameters (μ, β) from data"""
        if not data or len(data) < 10:
            return 50.0, 10.0  # Default values if insufficient data
        
        data_array = np.array(data)
        n = len(data_array)
        
        # Calculate mean and standard deviation
        mean_val = np.mean(data_array)
        std_val = np.std(data_array)
        
        # Adjust for small sample size
        if std_val == 0:
            std_val = 1.0
        
        # Calculate reduced mean and reduced variance
        # For Gumbel distribution with n > 10, we use approximations
        if n > 10:
            # Reduced mean (y_n) and reduced variance (σ_n) approximations
            y_n = 0.5772  # Euler-Mascheroni constant
            sigma_n = math.pi / math.sqrt(6)  # Approximately 1.2825
            
            # Calculate Gumbel parameters
            beta = std_val / sigma_n
            mu = mean_val - (y_n * beta)
        else:
            # Simple approximation for small samples
            beta = std_val * 0.7797
            mu = mean_val - (0.5772 * beta)
        
        return mu, beta
    
    def _gumbel_cdf(self, x, mu, beta):
        """Gumbel Cumulative Distribution Function"""
        if beta <= 0:
            return 0.5  # Default if beta is invalid
        
        try:
            z = (x - mu) / beta
            return math.exp(-math.exp(-z))
        except:
            return 0.5
    
    def _gumbel_pdf(self, x, mu, beta):
        """Gumbel Probability Density Function"""
        if beta <= 0:
            return 0.0
        
        try:
            z = (x - mu) / beta
            return (1/beta) * math.exp(-z - math.exp(-z))
        except:
            return 0.0
    
    def _calculate_return_period(self, x, mu, beta):
        """Calculate return period for given rainfall value"""
        try:
            # Probability of exceedance
            f_x = self._gumbel_cdf(x, mu, beta)
            p_exceed = 1 - f_x
            
            if p_exceed <= 0:
                return float('inf')
            
            # Return period (years)
            return_period = 1 / p_exceed
            
            # Cap at reasonable values
            return min(return_period, 1000)
        except:
            return 10.0  # Default return period
    
    def predict(self, location, current_rainfall):
        """Predict flood probability using Gumbel distribution"""
        try:
            # Get historical data for location
            if location in self.historical_data:
                historical = self.historical_data[location]
            else:
                # Use default data if location not found
                historical = self.historical_data['Ngadipiro']
            
            # Calculate Gumbel parameters
            mu, beta = self._calculate_gumbel_parameters(historical)
            
            # Calculate probabilities
            exceedance_prob = 1 - self._gumbel_cdf(current_rainfall, mu, beta)
            return_period = self._calculate_return_period(current_rainfall, mu, beta)
            
            # Calculate risk score (0-1)
            # Normalize to 0-1 range with sigmoid-like transformation
            risk_score = 1 / (1 + math.exp(-0.1 * (current_rainfall - mu)))
            
            # Cap risk score
            risk_score = min(max(risk_score, 0.0), 1.0)
            
            # Determine risk level and message
            risk_level, status, message = self._interpret_risk(
                risk_score, exceedance_prob, return_period, current_rainfall
            )
            
            return {
                'risk_score': round(risk_score, 3),
                'risk_level': risk_level,
                'status': status,
                'message': message,
                'parameters': {
                    'mu': round(mu, 2),
                    'beta': round(beta, 2),
                    'current_rainfall': current_rainfall,
                    'exceedance_probability': round(exceedance_prob * 100, 2),
                    'return_period': round(return_period, 1)
                },
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            print(f"❌ Gumbel prediction error for {location}: {e}")
            return self._get_fallback_prediction(current_rainfall)
    
    def _interpret_risk(self, risk_score, exceedance_prob, return_period, rainfall):
        """Interpret the risk metrics into categories"""
        
        # Convert exceedance probability to percentage
        exceedance_percent = exceedance_prob * 100
        
        if risk_score < 0.3:
            level = 'RENDAH'
            status = 'RENDAH'
            message = f"Prob {exceedance_percent:.1f}%, Return {return_period:.1f} tahun"
            
        elif risk_score < 0.6:
            level = 'MENENGAH'
            status = 'MENENGAH'
            
            if exceedance_percent > 20:
                message = f"Siaga: Prob kelebihan {exceedance_percent:.1f}%"
            elif return_period < 5:
                message = f"Siaga: Return period {return_period:.1f} tahun"
            else:
                message = f"Prob {exceedance_percent:.1f}%, Return {return_period:.1f} tahun"
                
        else:
            level = 'TINGGI'
            status = 'TINGGI'
            
            if exceedance_percent > 40:
                message = f"WASPADA: Prob kelebihan {exceedance_percent:.1f}% tinggi"
            elif return_period < 2:
                message = f"WASPADA: Kejadian 2 tahunan (Return {return_period:.1f} tahun)"
            elif rainfall > 100:
                message = f"WASPADA: Curah hujan {rainfall} mm ekstrem"
            else:
                message = f"WASPADA: Prob {exceedance_percent:.1f}%, Return {return_period:.1f} tahun"
        
        return level, status, message
    
    def _get_fallback_prediction(self, rainfall):
        """Fallback prediction if Gumbel analysis fails"""
        # Simple heuristic fallback
        risk_score = min(1.0, rainfall / 200.0)  # Normalize to 0-1
        
        if risk_score < 0.3:
            level, status = 'RENDAH', 'RENDAH'
            message = "Fallback: Kondisi normal"
        elif risk_score < 0.6:
            level, status = 'MENENGAH', 'MENENGAH'
            message = "Fallback: Perlu pemantauan"
        else:
            level, status = 'TINGGI', 'TINGGI'
            message = "Fallback: Kondisi waspada"
        
        return {
            'risk_score': round(risk_score, 3),
            'risk_level': level,
            'status': status,
            'message': message,
            'parameters': {
                'mu': 50.0,
                'beta': 10.0,
                'current_rainfall': rainfall,
                'exceedance_probability': round(risk_score * 50, 2),
                'return_period': round(10 / (risk_score + 0.1), 1)
            },
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'is_fallback': True
        }
    
    def analyze_historical_trend(self, location):
        """Analyze historical trend for a location"""
        try:
            if location not in self.historical_data:
                return None
            
            data = self.historical_data[location]
            
            # Calculate basic statistics
            mean_val = np.mean(data)
            std_val = np.std(data)
            max_val = np.max(data)
            min_val = np.min(data)
            
            # Calculate trend (simple linear regression)
            x = np.arange(len(data))
            y = np.array(data)
            
            # Linear regression
            A = np.vstack([x, np.ones(len(x))]).T
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]
            
            # Trend interpretation
            if m > 0.5:
                trend = "Meningkat signifikan"
            elif m > 0.1:
                trend = "Cenderung meningkat"
            elif m < -0.5:
                trend = "Menurun signifikan"
            elif m < -0.1:
                trend = "Cenderung menurun"
            else:
                trend = "Stabil"
            
            return {
                'location': location,
                'mean': round(mean_val, 2),
                'std': round(std_val, 2),
                'max': round(max_val, 2),
                'min': round(min_val, 2),
                'trend_slope': round(m, 3),
                'trend': trend,
                'data_points': len(data)
            }
            
        except Exception as e:
            print(f"❌ Historical trend analysis error: {e}")
            return None


def predict_flood_gumbel(rainfall, location='Ngadipiro'):
    """
    Simplified prediction function for realtime_data_controller.py
    """
    try:
        gumbel = GumbelDistribution()
        result = gumbel.predict(location, rainfall)
        return result
    except Exception as e:
        print(f"❌ Error in predict_flood_gumbel: {e}")
        return {
            'risk_score': 0.5,
            'risk_level': 'MENENGAH',
            'status': 'MENENGAH',
            'message': 'Error dalam analisis Gumbel',
            'parameters': {
                'mu': 50.0,
                'beta': 10.0,
                'current_rainfall': rainfall,
                'exceedance_probability': 25.0,
                'return_period': 4.0
            }
        }


if __name__ == "__main__":
    # Test the Gumbel model
    gumbel = GumbelDistribution()
    
    # Test different rainfall scenarios
    test_rainfalls = [30, 60, 100, 150, 200]
    
    for rainfall in test_rainfalls:
        result = gumbel.predict('Ngadipiro', rainfall)
        print(f"Rainfall: {rainfall}mm -> {result['status']} (Score: {result['risk_score']})")
        print(f"  Message: {result['message']}")
    
    # Test historical trend analysis
    trend = gumbel.analyze_historical_trend('Ngadipiro')
    if trend:
        print(f"\nHistorical Trend for {trend['location']}:")
        print(f"  Mean: {trend['mean']}mm, Max: {trend['max']}mm")
        print(f"  Trend: {trend['trend']} (Slope: {trend['trend_slope']})")