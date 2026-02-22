#!/usr/bin/env python3
"""
VIEW GEOCODING RESULTS
======================

Script untuk melihat hasil geocoding dengan tampilan yang bagus.

Usage:
  python view_geocoded.py                  # Show all geocoded reports
  python view_geocoded.py --all            # Show all reports (incl non-geocoded)
  python view_geocoded.py --stats          # Show statistics only
  python view_geocoded.py --failed         # Show only failed geocoding
  python view_geocoded.py --map            # Generate HTML map preview
"""

import sqlite3
import sys
import argparse
from datetime import datetime


class GeocodeViewer:
    """Viewer untuk hasil geocoding"""
    
    def __init__(self, db_path='flood_system.db'):
        self.db_path = db_path
    
    def get_all_reports(self):
        """Get all reports"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flood_reports ORDER BY id")
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return reports
    
    def show_stats(self):
        """Show geocoding statistics"""
        reports = self.get_all_reports()
        
        total = len(reports)
        geocoded = sum(1 for r in reports if r.get('latitude') and r.get('longitude'))
        not_geocoded = total - geocoded
        
        # Confidence breakdown
        high = sum(1 for r in reports if r.get('geocode_confidence') == 'HIGH')
        medium = sum(1 for r in reports if r.get('geocode_confidence') == 'MEDIUM')
        low = sum(1 for r in reports if r.get('geocode_confidence') == 'LOW')
        
        print("\n" + "="*70)
        print("  GEOCODING STATISTICS")
        print("="*70 + "\n")
        
        print(f"📊 Total Reports:           {total}")
        print(f"✅ Geocoded:                {geocoded} ({geocoded/total*100 if total > 0 else 0:.1f}%)")
        print(f"❌ Not Geocoded:            {not_geocoded} ({not_geocoded/total*100 if total > 0 else 0:.1f}%)")
        
        if geocoded > 0:
            print(f"\n🎯 Confidence Breakdown:")
            print(f"   HIGH:                    {high} ({high/geocoded*100:.1f}%)")
            print(f"   MEDIUM:                  {medium} ({medium/geocoded*100:.1f}%)")
            print(f"   LOW:                     {low} ({low/geocoded*100:.1f}%)")
        
        print("\n" + "="*70 + "\n")
    
    def show_geocoded(self):
        """Show geocoded reports"""
        reports = self.get_all_reports()
        geocoded = [r for r in reports if r.get('latitude') and r.get('longitude')]
        
        if not geocoded:
            print("\nℹ️  No geocoded reports found\n")
            return
        
        print("\n" + "="*70)
        print(f"  GEOCODED REPORTS ({len(geocoded)})")
        print("="*70 + "\n")
        
        for report in geocoded:
            self._print_report(report)
    
    def show_failed(self):
        """Show non-geocoded reports"""
        reports = self.get_all_reports()
        failed = [r for r in reports if not r.get('latitude') or not r.get('longitude')]
        
        if not failed:
            print("\n✅ All reports are geocoded!\n")
            return
        
        print("\n" + "="*70)
        print(f"  NON-GEOCODED REPORTS ({len(failed)})")
        print("="*70 + "\n")
        
        for report in failed:
            print(f"ID: {report['id']}")
            print(f"Address: {report.get('Alamat', 'N/A')}")
            print(f"Date: {report.get('Timestamp', 'N/A')}")
            print(f"Status: ❌ No coordinates")
            print("-" * 70)
    
    def show_all(self):
        """Show all reports"""
        reports = self.get_all_reports()
        
        print("\n" + "="*70)
        print(f"  ALL REPORTS ({len(reports)})")
        print("="*70 + "\n")
        
        for report in reports:
            self._print_report(report)
    
    def _print_report(self, report):
        """Print single report"""
        has_coords = report.get('latitude') and report.get('longitude')
        
        print(f"{'='*70}")
        print(f"ID: {report['id']}")
        print(f"Address: {report.get('Alamat', 'N/A')[:60]}")
        print(f"Reporter: {report.get('Nama Pelapor', 'N/A')}")
        print(f"Date: {report.get('Timestamp', 'N/A')}")
        
        if has_coords:
            lat = report['latitude']
            lng = report['longitude']
            conf = report.get('geocode_confidence', 'N/A')
            
            print(f"✅ Geocoded: YES")
            print(f"   📌 Coordinates: {lat:.6f}, {lng:.6f}")
            print(f"   🎯 Confidence: {conf}")
            print(f"   🗺️  Google Maps: https://www.google.com/maps?q={lat},{lng}")
        else:
            print(f"❌ Geocoded: NO")
        
        print()
    
    def generate_map_html(self, output_file='geocoded_map.html'):
        """Generate HTML map with all geocoded reports"""
        reports = self.get_all_reports()
        geocoded = [r for r in reports if r.get('latitude') and r.get('longitude')]
        
        if not geocoded:
            print("\n❌ No geocoded reports to map\n")
            return
        
        # Calculate center
        avg_lat = sum(r['latitude'] for r in geocoded) / len(geocoded)
        avg_lng = sum(r['longitude'] for r in geocoded) / len(geocoded)
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Geocoded Flood Reports Map</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 100vh; }}
        .info-box {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div class="info-box">
        <h3>Geocoded Flood Reports</h3>
        <p>Total: <strong>{len(geocoded)}</strong></p>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div id="map"></div>
    
    <script>
        var map = L.map('map').setView([{avg_lat}, {avg_lng}], 12);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }}).addTo(map);
        
        var markers = [];
"""
        
        # Add markers
        for report in geocoded:
            lat = report['latitude']
            lng = report['longitude']
            address = report.get('Alamat', 'N/A').replace("'", "\\'")
            reporter = report.get('Nama Pelapor', 'N/A').replace("'", "\\'")
            flood_height = report.get('Tinggi Banjir', 'N/A')
            timestamp = report.get('Timestamp', 'N/A')
            confidence = report.get('geocode_confidence', 'N/A')
            
            # Color based on confidence
            color = {
                'HIGH': '#10b981',
                'MEDIUM': '#f59e0b',
                'LOW': '#ef4444'
            }.get(confidence, '#6b7280')
            
            html += f"""
        var marker{report['id']} = L.circleMarker([{lat}, {lng}], {{
            radius: 8,
            fillColor: '{color}',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }}).addTo(map);
        
        marker{report['id']}.bindPopup(`
            <div style="min-width: 200px;">
                <h4>Report #{report['id']}</h4>
                <p><strong>Address:</strong><br>{address}</p>
                <p><strong>Reporter:</strong> {reporter}</p>
                <p><strong>Flood Height:</strong> {flood_height}</p>
                <p><strong>Date:</strong> {timestamp}</p>
                <p><strong>Confidence:</strong> <span style="color: {color};">{confidence}</span></p>
                <p><strong>Coordinates:</strong><br>{lat:.6f}, {lng:.6f}</p>
            </div>
        `);
        
        markers.push(marker{report['id']});
"""
        
        html += """
        // Fit bounds to show all markers
        if (markers.length > 0) {
            var group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.1));
        }
    </script>
</body>
</html>
"""
        
        # Save file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Map generated: {output_file}")
        print(f"   Total markers: {len(geocoded)}")
        print(f"   Center: {avg_lat:.6f}, {avg_lng:.6f}")
        print(f"\n   Open in browser to view the map\n")


def main():
    parser = argparse.ArgumentParser(description='View geocoding results')
    
    parser.add_argument('--all', action='store_true', help='Show all reports')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    parser.add_argument('--failed', action='store_true', help='Show non-geocoded reports')
    parser.add_argument('--map', action='store_true', help='Generate HTML map')
    parser.add_argument('--db', type=str, default='flood_system.db', help='Database path')
    
    args = parser.parse_args()
    
    viewer = GeocodeViewer(args.db)
    
    if args.stats:
        viewer.show_stats()
    elif args.failed:
        viewer.show_failed()
    elif args.map:
        viewer.generate_map_html()
    elif args.all:
        viewer.show_all()
    else:
        # Default: show geocoded reports
        viewer.show_geocoded()


if __name__ == "__main__":
    main()