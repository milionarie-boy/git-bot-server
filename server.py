# server.py - Clean Click Tracking Only
from flask import Flask, request, redirect, jsonify
from datetime import datetime
import json
import os
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
TRACKING_FILE = os.environ.get('TRACKING_FILE', 'click_tracking.json')


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
    """Dashboard showing click statistics"""
    data = load_tracking_data()
    
    total_clicks = 0
    unique_clicks = 0
    unique_emails = set()
    
    for tracking_id, d in data.items():
        clicks = d.get('clicks', [])
        total_clicks += len(clicks)
        email = d.get('email', '')
        if email:
            unique_emails.add(email)
        # Count unique clicks per tracking ID
        unique_ips = set()
        for click in clicks:
            unique_ips.add(click.get('ip', ''))
        unique_clicks += len(unique_ips)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dante Labs - Click Tracking</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stats { display: flex; gap: 20px; flex-wrap: wrap; }
            .stat-box { background: #e3f2fd; padding: 15px 25px; border-radius: 8px; }
            .stat-box h3 { margin: 0; color: #1565C0; }
            .stat-box p { margin: 5px 0 0; font-size: 24px; font-weight: bold; }
            .click-item { border-left: 4px solid #4CAF50; margin: 10px 0; padding: 10px 15px; background: #fafafa; }
            .click-email { color: #2196F3; font-weight: bold; }
            .click-url { color: #FF9800; }
            .click-time { color: #666; font-size: 12px; }
    </style>
    </head>
    <body>
        <h1>🔗 Dante Labs - Click Tracking Dashboard</h1>
        <div class="card">
            <div class="stats">
                <div class="stat-box"><h3>📧 Clicked Users</h3><p>""" + str(len(unique_emails)) + """</p></div>
                <div class="stat-box"><h3>🖱️ Total Clicks</h3><p>""" + str(total_clicks) + """</p></div>
                <div class="stat-box"><h3>🔄 Unique Clicks</h3><p>""" + str(unique_clicks) + """</p></div>
            </div>
        </div>
    """
    
    for tracking_id, d in data.items():
        email = d.get('email', 'Unknown')
        campaign = d.get('campaign', 'General')
        clicks = d.get('clicks', [])
        
        if clicks:
            html += f"""
            <div class="card click-item">
                <p><span class="click-email">📧 {email}</span></p>
                <p><strong>Campaign:</strong> {campaign}</p>
                <p><strong>Total Clicks:</strong> {len(clicks)}</p>
                <p><strong>Last Click:</strong> {clicks[-1].get('timestamp', 'Unknown')}</p>
                <details>
                    <summary>Click Details</summary>
            """
            for click in clicks[-5:]:  # Show last 5 clicks
                html += f"""
                    <p style="margin: 5px 0; font-size: 13px;">
                        <span class="click-time">{click.get('timestamp', '')[:19]}</span> → 
                        <span class="click-url">{click.get('url', '')[:60]}</span>
                    </p>
                """
            html += "</details></div>"
    
    html += "</body></html>"
    return html


@app.route('/stats')
def stats():
    """JSON endpoint for click statistics"""
    data = load_tracking_data()
    
    total_clicks = 0
    unique_emails = set()
    campaigns = {}
    
    for tracking_id, d in data.items():
        clicks = d.get('clicks', [])
        total_clicks += len(clicks)
        email = d.get('email', '')
        if email:
            unique_emails.add(email)
        
        campaign = d.get('campaign', 'General')
        if campaign not in campaigns:
            campaigns[campaign] = {'clicks': 0, 'unique_users': 0, 'users': set()}
        campaigns[campaign]['clicks'] += len(clicks)
        if email:
            campaigns[campaign]['users'].add(email)
    
    # Convert sets to counts
    for campaign in campaigns:
        campaigns[campaign]['unique_users'] = len(campaigns[campaign]['users'])
        del campaigns[campaign]['users']
    
    return jsonify({
        'total_clicks': total_clicks,
        'unique_users': len(unique_emails),
        'campaigns': campaigns
    })


@app.route('/click/<tracking_id>')
def track_click(tracking_id):
    """Track link click and redirect"""
    logger.info(f"🔗 Click: {tracking_id}")
    
    data = load_tracking_data()
    
    # Get the URL to redirect to
    url = request.args.get('url', 'https://dantelabs.us')
    try:
        url = urllib.parse.unquote(url)
    except:
        pass
    
    # Initialize if new
    if tracking_id not in data:
        logger.warning(f"⚠️ New tracking ID: {tracking_id}")
        data[tracking_id] = {
            'email': 'Unknown',
            'campaign': 'General',
            'sent_at': datetime.now().isoformat(),
            'clicks': []
        }
    
    # Ensure clicks list exists
    if 'clicks' not in data[tracking_id]:
        data[tracking_id]['clicks'] = []
    
    # Record click
    data[tracking_id]['clicks'].append({
        'timestamp': datetime.now().isoformat(),
        'url': url,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')[:100]
    })
    data[tracking_id]['last_click'] = datetime.now().isoformat()
    
    # Try to get email from tracking data if not set
    if data[tracking_id].get('email') == 'Unknown':
        # Check if we have it stored elsewhere
        pass
    
    save_tracking_data(data)
    logger.info(f"✅ Click recorded: {tracking_id} -> {url[:50]}")
    
    return redirect(url, 302)


@app.route('/ping')
def ping():
    """Health check"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Click Tracking Server starting on port {port}")
    logger.info(f"📊 Dashboard: http://localhost:{port}/")
    logger.info(f"📈 Stats API: http://localhost:{port}/stats")
    app.run(host='0.0.0.0', port=port, debug=False)