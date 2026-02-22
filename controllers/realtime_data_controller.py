from utils.model_ann import predict_flood_ann
from utils.gumbel_distribution import predict_flood_gumbel
from datetime import datetime

class RealTimeDataController:
    def __init__(self):
        print("✅ RealTimeDataController initialized")
    
    def get_comprehensive_data(self):
        """Get comprehensive real-time data with predictions"""
        try:
            # Get location data
            locations = self.get_fallback_locations()
            
            # Add predictions for each location
            for location in locations:
                # ANN Prediction
                ann_result = predict_flood_ann(
                    rainfall=location['rainfall_mm'],
                    water_level=location['water_level_mdpl'],
                    humidity=75.0,
                    temperature=28.0
                )
                
                # Gumbel Prediction
                gumbel_result = predict_flood_gumbel(location['rainfall_mm'])
                
                # Add predictions to location data
                location.update({
                    'ann_risk': ann_result['risk_score'],
                    'ann_status': ann_result['status'],
                    'ann_message': ann_result.get('message', ''),
                    'gumbel_risk': gumbel_result['risk_score'],
                    'gumbel_status': gumbel_result['status'],
                    'gumbel_message': gumbel_result.get('message', ''),
                    'last_update': datetime.now().strftime('%H:%M')
                })
            
            return locations
            
        except Exception as e:
            print(f"❌ Error in get_comprehensive_data: {e}")
            return self.get_fallback_predictions()
    
    def get_fallback_locations(self):
        """Get fallback location data"""
        return [
            {
                'location': 'Ngadipiro (S. keduang)',
                'water_level_mdpl': 143.74,
                'rainfall_mm': 45.5,
                'water_status': 'RENDAH',
                'last_update': '06:00',
                'source': 'BBWS Bengawan Solo'
            },
            {
                'location': 'Wonogiri Dam (Spillway)',
                'water_level_mdpl': 131.43,
                'rainfall_mm': 32.0,
                'water_status': 'RENDAH',
                'last_update': '06:00',
                'source': 'BBWS Bengawan Solo'
            },
            {
                'location': 'Colo Weir (S. bengawan solo)',
                'water_level_mdpl': 108.29,
                'rainfall_mm': 28.5,
                'water_status': 'RENDAH',
                'last_update': '06:00',
                'source': 'BBWS Bengawan Solo'
            }
        ]
    
    def get_fallback_predictions(self):
        """Fallback prediction data"""
        return [
            {
                'location': 'Ngadipiro (S. keduang)',
                'water_level_mdpl': 143.74,
                'rainfall_mm': 45.5,
                'ann_risk': 0.32,
                'ann_status': 'RENDAH',
                'ann_message': 'Prediksi ANN: Aman, tetap waspada',
                'gumbel_risk': 0.28,
                'gumbel_status': 'RENDAH',
                'gumbel_message': 'Distribusi Gumbel: Prob 18.7%',
                'last_update': datetime.now().strftime('%H:%M'),
                'source': 'BBWS Bengawan Solo',
                'water_status': 'RENDAH'
            }
        ]
    
    def get_overall_risk_status(self, predictions):
        """Get overall risk status"""
        if not predictions:
            return "TIDAK ADA DATA", "gray"
        
        # Count high and medium risk locations
        high_count = sum(1 for p in predictions if p.get('ann_status') == 'TINGGI')
        medium_count = sum(1 for p in predictions if p.get('ann_status') == 'MENENGAH')
        
        if high_count > 0:
            return "TINGGI", "red"
        elif medium_count > len(predictions) * 0.5:
            return "MENENGAH", "orange"
        else:
            return "RENDAH", "green"
    
    def get_weather_forecast(self):
        """Get weather forecast data"""
        try:
            # Simulated weather data
            forecast = [
                {
                    'day': 'Hari Ini',
                    'temp_min': 25,
                    'temp_max': 32,
                    'rainfall': 45.5,
                    'humidity': 75,
                    'condition': 'Hujan Ringan'
                },
                {
                    'day': 'Besok',
                    'temp_min': 24,
                    'temp_max': 31,
                    'rainfall': 32.0,
                    'humidity': 80,
                    'condition': 'Berawan'
                },
                {
                    'day': 'Lusa',
                    'temp_min': 23,
                    'temp_max': 30,
                    'rainfall': 28.5,
                    'humidity': 85,
                    'condition': 'Hujan Sedang'
                }
            ]
            return forecast
        except Exception as e:
            print(f"❌ Error getting weather forecast: {e}")
            return []