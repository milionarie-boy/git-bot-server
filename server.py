# server.py - Flask tracking server for Render.com
from flask import Flask, request, redirect, send_file, jsonify
from datetime import datetime
import json
import os
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Use environment variable for tracking file path
TRACKING_FILE = os.environ.get('TRACKING_FILE', 'email_logs/tracking_data.json')

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
        # Ensure directory exists
        os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save tracking data: {e}")
        return False

@app.route('/')
def home():
    """Home page with stats"""
    tracking_data = load_tracking_data()
    
    if not tracking_data:
        return """
        <h1>📊 Email Tracking Server</h1>
        <p>No tracking data yet. Send some emails to see stats!</p>
        <p>Tracking endpoints:</p>
        <ul>
            <li><code>GET /open/&lt;tracking_id&gt;</code> - Track email opens</li>
            <li><code>GET /click/&lt;tracking_id&gt;?url=...</code> - Track link clicks</li>
            <li><code>GET /stats</code> - View statistics</li>
        </ul>
        """
    
    html = "<h1>📊 Email Tracking Dashboard</h1><hr>"
    total_opens = 0
    total_clicks = 0
    
    for tracking_id, data in tracking_data.items():
        opens = len(data.get('opens', []))
        clicks = len(data.get('clicks', []))
        total_opens += opens
        total_clicks += clicks
        
        html += f"""
        <div style="border:1px solid #ccc; padding:15px; margin:10px 0; border-radius:8px;">
            <h3>📧 {data.get('email', 'Unknown')}</h3>
            <p><strong>Campaign:</strong> {data.get('campaign', 'General')}</p>
            <p><strong>Sent:</strong> {data.get('sent_at', 'Unknown')}</p>
            <p><strong>Opens:</strong> {opens} {'' if opens == 0 else '✅'}</p>
            <p><strong>Clicks:</strong> {clicks} {'' if clicks == 0 else '🔗'}</p>
        </div>
        """
    
    html += f"""
    <hr>
    <h2>📊 Summary</h2>
    <p>Total Opens: {total_opens}</p>
    <p>Total Clicks: {total_clicks}</p>
    <p>Total Tracked Emails: {len(tracking_data)}</p>
    """
    
    return html

@app.route('/stats')
def stats():
    """JSON endpoint for statistics"""
    tracking_data = load_tracking_data()
    
    stats = {
        'total_tracked': len(tracking_data),
        'total_opens': 0,
        'total_clicks': 0,
        'campaigns': {}
    }
    
    for tracking_id, data in tracking_data.items():
        campaign = data.get('campaign', 'General')
        opens = len(data.get('opens', []))
        clicks = len(data.get('clicks', []))
        
        stats['total_opens'] += opens
        stats['total_clicks'] += clicks
        
        if campaign not in stats['campaigns']:
            stats['campaigns'][campaign] = {
                'sent': 0,
                'opens': 0,
                'clicks': 0
            }
        
        stats['campaigns'][campaign]['sent'] += 1
        stats['campaigns'][campaign]['opens'] += opens
        stats['campaigns'][campaign]['clicks'] += clicks
    
    return jsonify(stats)

@app.route('/open/<tracking_id>')
def track_open(tracking_id):
    """Track email open"""
    tracking_data = load_tracking_data()
    
    if tracking_id in tracking_data:
        if 'opens' not in tracking_data[tracking_id]:
            tracking_data[tracking_id]['opens'] = []
        
        tracking_data[tracking_id]['opens'].append({
            'timestamp': datetime.now().isoformat(),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
        tracking_data[tracking_id]['last_open'] = datetime.now().isoformat()
        save_tracking_data(tracking_data)
        logger.info(f"✅ Open tracked: {tracking_id} - {tracking_data[tracking_id].get('email', 'Unknown')}")
    else:
        logger.warning(f"⚠️ Unknown tracking ID: {tracking_id}")
    
    # Return 1x1 transparent GIF
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;'
    return pixel, 200, {'Content-Type': 'image/gif', 'Cache-Control': 'no-cache, no-store, must-revalidate'}

@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    """Track link click and redirect"""
    tracking_data = load_tracking_data()
    url = request.args.get('url', 'https://dantelabs.us')
    
    # Decode URL if it was encoded
    try:
        url = urllib.parse.unquote(url)
    except:
        pass
    
    if tracking_id in tracking_data:
        if 'clicks' not in tracking_data[tracking_id]:
            tracking_data[tracking_id]['clicks'] = []
        
        tracking_data[tracking_id]['clicks'].append({
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
        tracking_data[tracking_id]['last_click'] = datetime.now().isoformat()
        save_tracking_data(tracking_data)
        logger.info(f"✅ Click tracked: {tracking_id} -> {url[:50]}")
    else:
        logger.warning(f"⚠️ Unknown tracking ID: {tracking_id}")
    
    return redirect(url, 302)

@app.route('/ping')
def ping():
    """Health check endpoint for Render"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Tracking Server Starting on port {port}")
    logger.info(f"📊 Open tracking: /open/{{tracking_id}}")
    logger.info(f"🔗 Click tracking: /click/{{tracking_id}}?url=...")
    logger.info(f"📈 Stats: /stats")
    app.run(host='0.0.0.0', port=port, debug=False)