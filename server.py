# server.py - Clean Email Tracking Server for Render.com
from flask import Flask, request, redirect, jsonify
from datetime import datetime
import json
import os
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
TRACKING_FILE = os.environ.get('TRACKING_FILE', 'tracking_data.json')


def load_tracking_data():
    """Load tracking data from file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            return {}
    return {}


def save_tracking_data(data):
    """Save tracking data to file"""
    try:
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save tracking data: {e}")
        return False


@app.route('/')
def home():
    """Home page with tracking dashboard"""
    data = load_tracking_data()
    
    total_opens = sum(len(d.get('opens', [])) for d in data.values())
    total_clicks = sum(len(d.get('clicks', [])) for d in data.values())
    
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
            .campaign { border-left: 4px solid #4CAF50; margin: 10px 0; padding: 10px 15px; background: #fafafa; }
            .open { color: #4CAF50; }
            .click { color: #FF9800; }
            .email { color: #2196F3; }
    </style>
    </head>
    <body>
        <h1>📊 Email Tracking Dashboard</h1>
        <div class="card">
            <div class="stats">
                <div class="stat-box"><h3>📧 Tracked</h3><p>""" + str(len(data)) + """</p></div>
                <div class="stat-box"><h3>👁️ Opens</h3><p>""" + str(total_opens) + """</p></div>
                <div class="stat-box"><h3>🔗 Clicks</h3><p>""" + str(total_clicks) + """</p></div>
            </div>
        </div>
    """
    
    for tracking_id, d in data.items():
        html += f"""
        <div class="campaign">
            <p><span class="email">📧 {d.get('email', 'Unknown')}</span></p>
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
    logger.info(f"📨 Open request: {tracking_id}")
    
    data = load_tracking_data()
    
    # Initialize tracking if new
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': []
        }
    
    # Record open
    if 'opens' not in data[tracking_id]:
        data[tracking_id]['opens'] = []
    
    data[tracking_id]['opens'].append({
        'timestamp': datetime.now().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    })
    data[tracking_id]['last_open'] = datetime.now().isoformat()
    save_tracking_data(data)
    
    logger.info(f"✅ Open recorded: {tracking_id} (total: {len(data[tracking_id]['opens'])})")
    
    # Return 1x1 transparent GIF
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;'
    return pixel, 200, {
        'Content-Type': 'image/gif',
        'Cache-Control': 'no-cache, no-store, must-revalidate'
    }


@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    """Track link click and redirect"""
    logger.info(f"🔗 Click request: {tracking_id}")
    
    data = load_tracking_data()
    
    # Get the URL to redirect to
    url = request.args.get('url', 'https://dantelabs.us')
    try:
        url = urllib.parse.unquote(url)
    except:
        pass
    
    # Initialize tracking if new
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': []
        }
    
    # Record click
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
    
    logger.info(f"✅ Click recorded: {tracking_id} -> {url[:50]}")
    
    return redirect(url, 302)


@app.route('/ping')
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Tracking Server starting on port {port}")
    logger.info(f"📊 Dashboard: http://localhost:{port}/")
    logger.info(f"📈 Stats API: http://localhost:{port}/stats")
    logger.info(f"🖼️ Open tracking: http://localhost:{port}/open/{{tracking_id}}")
    logger.info(f"🔗 Click tracking: http://localhost:{port}/click/{{tracking_id}}")
    app.run(host='0.0.0.0', port=port, debug=False)