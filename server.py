# server.py - Optimized for PythonAnywhere
from flask import Flask, request, redirect, jsonify, render_template_string
from datetime import datetime
import json
import os
import urllib.parse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ========== PYTHONANYWHERE CONFIGURATION ==========
# Use absolute path for persistent storage
# IMPORTANT: Replace 'yourusername' with your actual PythonAnywhere username
USERNAME = os.environ.get('PYTHONANYWHERE_USERNAME', 'dantelabs')
BASE_DIR = f'/home/{USERNAME}'

# Use a persistent location for tracking data
TRACKING_FILE = os.path.join(BASE_DIR, 'click_tracking.json')

# Fallback to local directory if running locally
if not os.path.exists(BASE_DIR):
    TRACKING_FILE = 'click_tracking.json'

logger.info(f"📁 Tracking file: {TRACKING_FILE}")


# ========== DATA MANAGEMENT ==========
def load_tracking_data():
    """Load tracking data from persistent storage"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"✅ Loaded {len(data)} tracking records")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error loading tracking data: {e}")
            return {}
    else:
        logger.info("ℹ️ No tracking file found, creating new one")
        return {}


def save_tracking_data(data):
    """Save tracking data to persistent storage"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(TRACKING_FILE), exist_ok=True)
        
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved {len(data)} tracking records")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save tracking data: {e}")
        return False


def get_tracking_stats():
    """Calculate tracking statistics"""
    data = load_tracking_data()
    
    total_clicks = 0
    unique_clickers = set()
    campaigns = {}
    
    for tracking_id, record in data.items():
        clicks = record.get('clicks', [])
        total_clicks += len(clicks)
        
        email = record.get('email', '')
        if email and email != 'Unknown':
            unique_clickers.add(email)
        
        campaign = record.get('campaign', 'General')
        if campaign not in campaigns:
            campaigns[campaign] = {'clicks': 0, 'users': set()}
        campaigns[campaign]['clicks'] += len(clicks)
        if email and email != 'Unknown':
            campaigns[campaign]['users'].add(email)
    
    # Convert sets to counts for JSON
    campaign_summary = {}
    for campaign, stats in campaigns.items():
        campaign_summary[campaign] = {
            'clicks': stats['clicks'],
            'unique_users': len(stats['users'])
        }
    
    return {
        'total_clicks': total_clicks,
        'unique_clickers': len(unique_clickers),
        'campaigns': campaign_summary,
        'total_tracked': len(data)
    }


# ========== ROUTES ==========

@app.route('/')
def dashboard():
    """Interactive tracking dashboard with clicker information"""
    data = load_tracking_data()
    stats = get_tracking_stats()
    
    # Build the HTML dashboard
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>📊 Click Tracking Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0d0d2b 100%);
                min-height: 100vh;
                padding: 30px;
                color: #e0e0e0;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                flex-wrap: wrap;
                gap: 15px;
            }
            .header h1 {
                font-size: 28px;
                background: linear-gradient(135deg, #818cf8, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .header .badge {
                background: rgba(99, 102, 241, 0.2);
                padding: 8px 16px;
                border-radius: 50px;
                font-size: 13px;
                border: 1px solid rgba(99, 102, 241, 0.3);
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 20px 24px;
                transition: transform 0.2s;
            }
            .stat-card:hover { transform: translateY(-2px); }
            .stat-card .number {
                font-size: 32px;
                font-weight: 700;
                color: #818cf8;
                margin-bottom: 4px;
            }
            .stat-card .label {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.5);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 24px;
            }
            .card h2 {
                font-size: 18px;
                color: #fff;
                margin-bottom: 16px;
            }
            
            .campaign-list {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
            }
            .campaign-tag {
                background: rgba(99, 102, 241, 0.15);
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
                border: 1px solid rgba(99, 102, 241, 0.15);
            }
            .campaign-tag strong { color: #a78bfa; }
            
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }
            th {
                text-align: left;
                padding: 12px 12px;
                color: rgba(255, 255, 255, 0.4);
                font-weight: 500;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            td {
                padding: 12px 12px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
            tr:hover td { background: rgba(255, 255, 255, 0.02); }
            
            .email { color: #a78bfa; font-weight: 500; }
            .username { color: #34d399; }
            .role { color: #fbbf24; font-size: 12px; }
            .click-count {
                background: rgba(251, 191, 36, 0.15);
                padding: 2px 10px;
                border-radius: 12px;
                font-size: 12px;
                color: #fbbf24;
            }
            .time { color: rgba(255, 255, 255, 0.3); font-size: 12px; }
            .url-link {
                color: #818cf8;
                text-decoration: none;
                font-size: 12px;
            }
            .url-link:hover { text-decoration: underline; }
            
            .empty-state {
                text-align: center;
                padding: 40px 20px;
                color: rgba(255, 255, 255, 0.3);
            }
            .empty-state .icon { font-size: 48px; margin-bottom: 12px; }
            
            .refresh-btn {
                background: rgba(99, 102, 241, 0.2);
                border: 1px solid rgba(99, 102, 241, 0.3);
                color: #818cf8;
                padding: 8px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }
            .refresh-btn:hover {
                background: rgba(99, 102, 241, 0.3);
            }
            
            @media (max-width: 768px) {
                body { padding: 16px; }
                .stats-grid { grid-template-columns: repeat(2, 1fr); }
                table { font-size: 12px; }
                td, th { padding: 8px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Click Tracking Dashboard</h1>
                <div class="badge">🔗 Always On</div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{stats['total_clicks']}</div>
                    <div class="label">Total Clicks</div>
                </div>
                <div class="stat-card">
                    <div class="number">{stats['unique_clickers']}</div>
                    <div class="label">Unique Clickers</div>
                </div>
                <div class="stat-card">
                    <div class="number">{stats['total_tracked']}</div>
                    <div class="label">Tracked Links</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(stats['campaigns'])}</div>
                    <div class="label">Campaigns</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📋 Campaign Summary</h2>
                <div class="campaign-list">
    """
    
    if stats['campaigns']:
        for campaign, s in stats['campaigns'].items():
            html += f'''
                <div class="campaign-tag">
                    <strong>{campaign}</strong>: {s['clicks']} clicks · {s['unique_users']} users
                </div>
            '''
    else:
        html += '<div class="empty-state">No campaigns yet</div>'
    
    html += """
                </div>
            </div>
            
            <div class="card">
                <h2>👤 Recent Clickers</h2>
                <table>
                    <tr>
                        <th>Email</th>
                        <th>Username</th>
                        <th>Campaign</th>
                        <th>Clicks</th>
                        <th>Last Click</th>
                    </tr>
    """
    
    # Sort by most recent click
    sorted_items = sorted(
        data.items(),
        key=lambda x: x[1].get('last_click', ''),
        reverse=True
    )
    
    displayed = 0
    for tracking_id, record in sorted_items:
        if displayed >= 100:  # Limit display
            break
        
        email = record.get('email', 'Unknown')
        if email == 'Unknown' and not record.get('clicks'):
            continue
            
        username = record.get('username', '')
        campaign = record.get('campaign', 'General')
        clicks = record.get('clicks', [])
        last_click = clicks[-1].get('timestamp', '') if clicks else ''
        
        html += f'''
            <tr>
                <td class="email">{email}</td>
                <td class="username">@{username if username else 'N/A'}</td>
                <td>{campaign}</td>
                <td><span class="click-count">{len(clicks)}</span></td>
                <td class="time">{last_click[:19] if last_click else 'Never'}</td>
            </tr>
        '''
        displayed += 1
    
    if displayed == 0:
        html += '''
            <tr><td colspan="5" class="empty-state">
                <div class="icon">🕊️</div>
                No clicks tracked yet. Send your first campaign!
            </td></tr>
        '''
    
    html += """
                </table>
            </div>
            
            <div style="text-align: center; padding: 20px; color: rgba(255,255,255,0.2); font-size: 12px;">
                Powered by PythonAnywhere · Updated in real-time
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html)


@app.route('/stats')
def stats_json():
    """JSON endpoint for click statistics"""
    stats = get_tracking_stats()
    stats['timestamp'] = datetime.now().isoformat()
    return jsonify(stats)


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
            'username': 'Unknown',
            'role': 'Unknown',
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
        'url': url[:200],
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')[:100]
    })
    data[tracking_id]['last_click'] = datetime.now().isoformat()
    
    save_tracking_data(data)
    logger.info(f"✅ Click recorded: {tracking_id}")
    
    return redirect(url, 302)


@app.route('/ping')
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'tracking_file': TRACKING_FILE,
        'records': len(load_tracking_data())
    })


@app.route('/debug')
def debug():
    """Debug endpoint to check data"""
    data = load_tracking_data()
    return jsonify({
        'total_records': len(data),
        'sample': list(data.items())[:3] if data else [],
        'tracking_file': TRACKING_FILE
    })


# ========== MAIN ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Click Tracking Server starting on port {port}")
    logger.info(f"📁 Data file: {TRACKING_FILE}")
    logger.info(f"📊 Dashboard: http://localhost:{port}/")
    logger.info(f"📈 Stats API: http://localhost:{port}/stats")
    app.run(host='0.0.0.0', port=port, debug=False)