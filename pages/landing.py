import streamlit as st

def render_landing():
    """Render the professional landing page — the first page users see."""

    # --- Inject Google Font + Custom CSS ---
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        /* Reset Streamlit defaults for a clean look */
        .landing-page * { font-family: 'Inter', sans-serif; }

        /* Hero Section */
        .hero-section {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 40%, #2c5364 100%);
            border-radius: 20px;
            padding: 60px 40px;
            text-align: center;
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .hero-section::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: radial-gradient(circle at 30% 70%, rgba(34, 193, 195, 0.15) 0%, transparent 50%),
                        radial-gradient(circle at 70% 30%, rgba(253, 187, 45, 0.1) 0%, transparent 50%);
            animation: pulse 8s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.05); opacity: 1; }
        }
        .hero-title {
            font-size: 3rem;
            font-weight: 900;
            color: #ffffff;
            margin: 0 0 10px 0;
            position: relative;
            letter-spacing: -1px;
        }
        .hero-subtitle {
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.9);
            margin: 0 0 15px 0;
            position: relative;
            font-weight: 400;
            width: 100%;
            max-width: 800px;
            text-align: center;
            line-height: 1.6;
        }
        .hero-badge {
            display: inline-block;
            background: rgba(34, 193, 195, 0.2);
            border: 1px solid rgba(34, 193, 195, 0.4);
            color: #22c1c3;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 20px;
            position: relative;
        }

        /* Metrics Strip */
        .metrics-strip {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 35px;
        }
        .metric-card {
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px 16px;
            text-align: center;
            transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s;
            overflow: hidden;
            background-color: #1a1a2e; /* Fallback */
            z-index: 1;
            height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: -10px; left: -10px; right: -10px; bottom: -10px;
            background-size: cover;
            background-position: center;
            filter: blur(5px) brightness(0.6);
            z-index: -1;
            transition: filter 0.4s, transform 0.4s;
        }
        .metric-card:hover {
            transform: translateY(-8px) scale(1.03);
            box-shadow: 0 15px 45px rgba(0, 0, 0, 0.5);
            border-color: rgba(34, 193, 195, 0.5);
        }
        .metric-card:hover::before {
            filter: blur(2px) brightness(0.8);
            transform: scale(1.1);
        }
        /* Specific background images for tiles */
        .metric-card:nth-child(1)::before { background-image: url('https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?auto=format&fit=crop&q=80&w=600'); } /* Weather/stations */
        .metric-card:nth-child(2)::before { background-image: url('https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?auto=format&fit=crop&q=80&w=600'); } /* Industry/pollution */
        .metric-card:nth-child(3)::before { background-image: url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=600'); } /* Network/connections */
        .metric-card:nth-child(4)::before { background-image: url('https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&q=80&w=600'); } /* Map/grid */

        .metric-number {
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #22c1c3, #fdbb2d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            text-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }
        .metric-label {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.9);
            margin: 8px 0 0 0;
            font-weight: 600;
            text-shadow: 0 1px 4px rgba(0,0,0,0.8);
        }

        /* Feature Cards */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 35px;
        }
        .feature-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 30px 24px;
            text-align: center;
            transition: transform 0.3s, border-color 0.3s;
        }
        .feature-card:hover {
            transform: translateY(-4px);
            border-color: rgba(34, 193, 195, 0.4);
        }
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 14px;
        }
        .feature-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #e0e0e0;
            margin: 0 0 10px 0;
        }
        .feature-desc {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.55);
            margin: 0;
            line-height: 1.6;
        }

        /* Data Source Strip */
        .sources-strip {
            display: flex;
            justify-content: center;
            gap: 40px;
            padding: 20px 0;
            margin-bottom: 30px;
            opacity: 0.5;
        }
        .source-name {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.5);
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* Footer */
        .landing-footer {
            text-align: center;
            padding: 30px 0 10px 0;
            color: rgba(255, 255, 255, 0.3);
            font-size: 0.8rem;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .metrics-strip { grid-template-columns: repeat(2, 1fr); }
            .features-grid { grid-template-columns: 1fr; }
            .hero-title { font-size: 2rem; }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Full Page Body (single block so tags nest correctly and
    #     .landing-page wraps the whole page, not just the hero) ---
    st.markdown("""
<div class="landing-page">
<div class="hero-section">
<div class="hero-badge">🌿 Environmental Intelligence Platform</div>
<h1 class="hero-title">India AQI Dashboard</h1>
<p class="hero-subtitle">Real-time air quality monitoring, historical industrial emission baseline tracking, and direct authority reporting — all in one platform.</p>
</div>
<div class="metrics-strip">
<div class="metric-card">
<p class="metric-number">500+</p>
<p class="metric-label">Monitoring Stations</p>
</div>
<div class="metric-card">
<p class="metric-number">3,900+</p>
<p class="metric-label">Industrial Facilities Tracked</p>
</div>
<div class="metric-card">
<p class="metric-number">13</p>
<p class="metric-label">State Boards Connected</p>
</div>
<div class="metric-card">
<p class="metric-number">5 km</p>
<p class="metric-label">Grid Resolution</p>
</div>
</div>
<div class="features-grid">
<div class="feature-card">
<div class="feature-icon">📊</div>
<p class="feature-title">Real-Time AQI Monitoring</p>
<p class="feature-desc">Live air quality data from 500+ stations across India, with PM2.5 readings converted to India's NAQI scale. Updated every hour.</p>
</div>
<div class="feature-card">
<div class="feature-icon">🏭</div>
<p class="feature-title">Historical Emission Tracking</p>
<p class="feature-desc">Pin-point 3,900+ factories using historical baseline estimates from Climate TRACE and Global Energy Monitor datasets to identify potential polluters near real-time AQI spikes.</p>
</div>
<div class="feature-card">
<div class="feature-icon">📧</div>
<p class="feature-title">Authority Reporting</p>
<p class="feature-desc">Generate AI-powered complaint emails with real data and send them directly to the responsible State Pollution Control Board.</p>
</div>
</div>
<div class="sources-strip">
<span class="source-name">OpenAQ</span>
<span class="source-name">Climate TRACE</span>
<span class="source-name">Global Energy Monitor</span>
<span class="source-name">CPCB</span>
</div>
<div class="landing-footer">
<p>Real-time AQI sourced from OpenAQ. Historical facility estimates from Climate TRACE and Global Energy Monitor.<br>Built for the ET AI Hackathon 2026.</p>
</div>
</div>
    """, unsafe_allow_html=True)
