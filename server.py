# server.py - Flask tracking server for Render.com
from flask import Flask, request, redirect, jsonify
from datetime import datetime
import json
import os
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variable or default
TRACKING_FILE = os.environ.get('TRACKING_FILE', 'tracking_data.json')

def load_tracking_data():
    """Load tracking data from file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tracking_data(data):
    """Save tracking data to file"""
    try:
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        return False

@app.route('/')
def home():
    """Home page with stats"""
    data = load_tracking_data()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Email Tracking Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stats { display: flex; gap: 20px; flex-wrap: wrap; }
            .stat-box { background: #e3f2fd; padding: 15px 25px; border-radius: 8px; }
            .stat-box h3 { margin: 0; color: #1565C0; }
            .stat-box p { margin: 5px 0 0; font-size: 24px; font-weight: bold; }
            .campaign { border-left: 4px solid #4CAF50; }
            .open { color: #4CAF50; }
            .click { color: #FF9800; }
        </style>
    </head>
    <body>
        <h1>📊 Email Tracking Dashboard</h1>
        <div class="card">
            <div class="stats">
                <div class="stat-box"><h3>📧 Tracked</h3><p>""" + str(len(data)) + """</p></div>
                <div class="stat-box"><h3>👁️ Opens</h3><p>""" + str(sum(len(d.get('opens', [])) for d in data.values())) + """</p></div>
                <div class="stat-box"><h3>🔗 Clicks</h3><p>""" + str(sum(len(d.get('clicks', [])) for d in data.values())) + """</p></div>
            </div>
        </div>
    """
    
    for tracking_id, d in data.items():
        html += f"""
        <div class="card campaign">
            <h3>📧 {d.get('email', 'Unknown')}</h3>
            <p><strong>Campaign:</strong> {d.get('campaign', 'General')}</p>
            <p><strong>Sent:</strong> {d.get('sent_at', 'Unknown')}</p>
            <p><span class="open">✅ Opens: {len(d.get('opens', []))}</span></p>
            <p><span class="click">🔗 Clicks: {len(d.get('clicks', []))}</span></p>
        </div>
        """
    
    html += "</body></html>"
    return html

@app.route('/stats')
def stats():
    """JSON endpoint for statistics"""
    data = load_tracking_data()
    
    total_opens = 0
    total_clicks = 0
    campaigns = {}
    
    for tracking_id, d in data.items():
        campaign = d.get('campaign', 'General')
        opens = len(d.get('opens', []))
        clicks = len(d.get('clicks', []))
        
        total_opens += opens
        total_clicks += clicks
        
        if campaign not in campaigns:
            campaigns[campaign] = {'sent': 0, 'opens': 0, 'clicks': 0}
        campaigns[campaign]['sent'] += 1
        campaigns[campaign]['opens'] += opens
        campaigns[campaign]['clicks'] += clicks
    
    return jsonify({
        'total_tracked': len(data),
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'campaigns': campaigns
    })

@app.route('/open/<tracking_id>')
def track_open(tracking_id):
    """Track email open"""
    data = load_tracking_data()
    
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': []
        }
    
    if 'opens' not in data[tracking_id]:
        data[tracking_id]['opens'] = []
    
    data[tracking_id]['opens'].append({
        'timestamp': datetime.now().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    })
    data[tracking_id]['last_open'] = datetime.now().isoformat()
    save_tracking_data(data)
    logger.info(f"✅ Open: {tracking_id}")
    
    # Return 1x1 transparent GIF
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;'
    return pixel, 200, {'Content-Type': 'image/gif'}

@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    """Track link click"""
    data = load_tracking_data()
    url = request.args.get('url', 'https://dantelabs.us')
    
    try:
        url = urllib.parse.unquote(url)
    except:
        pass
    
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': []
        }
    
    if 'clicks' not in data[tracking_id]:
        data[tracking_id]['clicks'] = []
    
    data[tracking_id]['clicks'].append({
        'timestamp': datetime.now().isoformat(),
        'url': url,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    })
    data[tracking_id]['last_click'] = datetime.now().isoformat()
    save_tracking_data(data)
    logger.info(f"✅ Click: {tracking_id}")
    
    return redirect(url, 302)

@app.route('/ping')
def ping():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/save_tracking', methods=['POST'])
def save_tracking():
    """Save tracking data from client"""
    try:
        data = request.get_json()
        if data:
            # Merge with existing data
            existing = load_tracking_data()
            for tracking_id, tracking_info in data.items():
                if tracking_id not in existing:
                    existing[tracking_id] = tracking_info
                else:
                    # Merge opens and clicks
                    if 'opens' in tracking_info:
                        existing[tracking_id]['opens'] = tracking_info['opens']
                    if 'clicks' in tracking_info:
                        existing[tracking_id]['clicks'] = tracking_info['clicks']
                    if 'last_open' in tracking_info:
                        existing[tracking_id]['last_open'] = tracking_info['last_open']
                    if 'last_click' in tracking_info:
                        existing[tracking_id]['last_click'] = tracking_info['last_click']
            
            save_tracking_data(existing)
            return jsonify({'status': 'ok', 'message': 'Tracking data saved'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'ok'})

# Add to server.py
@app.route('/logo/<tracking_id>')
def serve_logo(tracking_id):
    """Serve logo and track open"""
    logger.info(f"🖼️ Logo loaded for tracking: {tracking_id}")
    
    data = load_tracking_data()
    
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': []
        }
    
    data[tracking_id]['opens'].append({
        'timestamp': datetime.now().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'source': 'logo'
    })
    data[tracking_id]['last_open'] = datetime.now().isoformat()
    save_tracking_data(data)
    
    # Redirect to the actual logo
    return redirect("https://i.ibb.co/3YYQXPHr/dantelabs-Logo.jpg", 302)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)