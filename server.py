# server.py - Working Email Tracking Server for Render.com
from flask import Flask, request, redirect, jsonify, Response
from datetime import datetime
import json
import os
import urllib.parse
import logging
import base64

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
            .prefetch { color: #FF9800; font-size: 12px; }
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
        opens = len(d.get('opens', []))
        clicks = len(d.get('clicks', []))
        prefetches = d.get('prefetches', 0)
        
        html += f"""
        <div class="campaign">
            <p><span class="email">📧 {d.get('email', 'Unknown')}</span></p>
            <p><strong>Campaign:</strong> {d.get('campaign', 'General')}</p>
            <p><strong>Sent:</strong> {d.get('sent_at', 'Unknown')}</p>
            <p><span class="open">✅ Opens: {opens}</span></p>
            <p><span class="click">🔗 Clicks: {clicks}</span></p>
            {f'<p><span class="prefetch">🔄 Prefetches: {prefetches}</span></p>' if prefetches > 0 else ''}
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

# server.py - Updated track_open with pre-fetch detection

@app.route('/open/<tracking_id>')
def track_open(tracking_id):
    """Track email open with pre-fetch detection"""
    logger.info(f"📨 Open request: {tracking_id}")
    logger.info(f"   IP: {request.remote_addr}")
    logger.info(f"   User-Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}")
    
    data = load_tracking_data()
    
    # Initialize if new
    if tracking_id not in data:
        logger.warning(f"⚠️ New tracking ID: {tracking_id} - creating entry")
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': [],
            'prefetches': 0,
            'real_opens': 0
        }
    
    # Ensure lists exist
    if 'opens' not in data[tracking_id]:
        data[tracking_id]['opens'] = []
    if 'prefetches' not in data[tracking_id]:
        data[tracking_id]['prefetches'] = 0
    if 'real_opens' not in data[tracking_id]:
        data[tracking_id]['real_opens'] = 0
    
    # ========== DETECT PRE-FETCH ==========
    user_agent = request.headers.get('User-Agent', '').lower()
    ip = request.remote_addr
    
    # Check for pre-fetch patterns
    is_prefetch = False
    prefetch_reason = ""
    
    # 1. Known pre-fetch user agents
    if any(agent in user_agent for agent in [
        'googleimageproxy',      # Gmail image proxy
        'googleusercontent',     # Google cache
        'outlook',               # Outlook pre-fetch
        'prefetch',              # Generic prefetch
        'bot',                   # Search bots
        'crawler',               # Web crawlers
        'gmail',                 # Gmail internal
        'yahoo'                  # Yahoo mail
    ]):
        is_prefetch = True
        prefetch_reason = "Known email client pre-fetch"
    
    # 2. Multiple opens from same IP within 5 seconds
    existing_opens = data[tracking_id].get('opens', [])
    if existing_opens:
        last_open = existing_opens[-1].get('timestamp', '')
        if last_open:
            try:
                last_time = datetime.fromisoformat(last_open)
                if (datetime.now() - last_time).seconds < 5:
                    if ip == existing_opens[-1].get('ip', ''):
                        is_prefetch = True
                        prefetch_reason = "Duplicate open from same IP within 5 seconds"
            except:
                pass
    
    # 3. Record accordingly
    if is_prefetch:
        data[tracking_id]['prefetches'] = data[tracking_id].get('prefetches', 0) + 1
        logger.info(f"🔄 PRE-FETCH detected: {tracking_id} - {prefetch_reason}")
    else:
        # Real open
        data[tracking_id]['opens'].append({
            'timestamp': datetime.now().isoformat(),
            'ip': ip,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        })
        data[tracking_id]['last_open'] = datetime.now().isoformat()
        data[tracking_id]['real_opens'] = data[tracking_id].get('real_opens', 0) + 1
        logger.info(f"✅ REAL OPEN recorded: {tracking_id} (total: {len(data[tracking_id]['opens'])})")
    
    save_tracking_data(data)
    
    # Return 1x1 transparent GIF
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01D\x00;'
    return pixel, 200, {
        'Content-Type': 'image/gif',
        'Cache-Control': 'no-cache, no-store, must-revalidate, private',
        'Pragma': 'no-cache',
        'Expires': '0'
    }


@app.route('/logo/<tracking_id>')
def serve_logo(tracking_id):
    """Serve logo with pre-fetch detection"""
    logger.info(f"🖼️ Logo requested: {tracking_id}")
    
    data = load_tracking_data()
    
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': [],
            'prefetches': 0,
            'real_opens': 0
        }
    
    if 'opens' not in data[tracking_id]:
        data[tracking_id]['opens'] = []
    if 'prefetches' not in data[tracking_id]:
        data[tracking_id]['prefetches'] = 0
    
    # Check for pre-fetch (logo is often pre-fetched)
    user_agent = request.headers.get('User-Agent', '').lower()
    is_prefetch = any(agent in user_agent for agent in [
        'googleimageproxy', 'googleusercontent', 'outlook', 'prefetch', 'bot', 'crawler'
    ])
    
    if is_prefetch:
        data[tracking_id]['prefetches'] = data[tracking_id].get('prefetches', 0) + 1
        logger.info(f"🔄 Logo PRE-FETCH: {tracking_id}")
    else:
        data[tracking_id]['opens'].append({
            'timestamp': datetime.now().isoformat(),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'source': 'logo'
        })
        data[tracking_id]['last_open'] = datetime.now().isoformat()
        data[tracking_id]['real_opens'] = data[tracking_id].get('real_opens', 0) + 1
        logger.info(f"✅ Logo REAL OPEN: {tracking_id}")
    
    save_tracking_data(data)
    
    return redirect("https://i.ibb.co/3YYQXPHr/dantelabs-Logo.jpg", 302)

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
    
    # ALWAYS initialize if tracking_id doesn't exist
    if tracking_id not in data:
        logger.warning(f"⚠️ New tracking ID (click): {tracking_id} - creating entry")
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': [],
            'prefetches': 0
        }
    
    # Ensure clicks list exists
    if 'clicks' not in data[tracking_id]:
        data[tracking_id]['clicks'] = []
    
    # Record click
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


@app.route('/save_tracking', methods=['POST'])
def save_tracking():
    """Save tracking data from client (for backup)"""
    try:
        data = request.get_json()
        if data:
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
            logger.info(f"✅ Tracking data saved from client: {len(data)} entries")
            return jsonify({'status': 'ok', 'message': 'Tracking data saved'})
    except Exception as e:
        logger.error(f"Error saving tracking data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'ok'})

# server.py - Add these new endpoints

@app.route('/favicon/<tracking_id>')
def track_favicon(tracking_id):
    """Track favicon requests"""
    logger.info(f"🎯 Favicon requested: {tracking_id}")
    
    data = load_tracking_data()
    if tracking_id not in data:
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'opens': [],
            'clicks': [],
            'prefetches': 0,
            'favicon_hits': 0
        }
    
    if 'favicon_hits' not in data[tracking_id]:
        data[tracking_id]['favicon_hits'] = 0
    
    data[tracking_id]['favicon_hits'] += 1
    
    if 'opens' not in data[tracking_id]:
        data[tracking_id]['opens'] = []
    
    # Favicon is usually a real open (browser loads it automatically)
    data[tracking_id]['opens'].append({
        'timestamp': datetime.now().isoformat(),
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'source': 'favicon'
    })
    data[tracking_id]['last_open'] = datetime.now().isoformat()
    data[tracking_id]['real_opens'] = data[tracking_id].get('real_opens', 0) + 1
    save_tracking_data(data)
    
    # Return a transparent favicon
    # 1x1 transparent PNG
    favicon = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    )
    return favicon, 200, {'Content-Type': 'image/x-icon'}

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
    logger.info(f"🔄 Save tracking: http://localhost:{port}/save_tracking")
    app.run(host='0.0.0.0', port=port, debug=False)