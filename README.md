# 🌿 India AQI Dashboard

A comprehensive, real-time Air Quality Index monitoring and reporting platform for cities across India. It features interactive maps with 5x5km AQI grids, industrial facility tracking, detailed emissions analytics, and an AI-powered authority reporting system.

## 🌟 Key Features

- **Professional UI & Landing Page** — A modern, responsive design using glassmorphism, dynamic hover effects, and a global navigation header.
- **User Authentication** — Secure login and sign-up powered by a Neon PostgreSQL database and bcrypt hashing.
- **Real-time AQI Monitoring** — Live air quality data from 500+ monitoring stations across India via the OpenAQ API.
- **Interactive City Maps** — Click any city tile to view a detailed Folium map overlaid with a high-resolution 5x5km AQI grid.
- **Industrial Facility Tracking** — Pin-points 3,900+ factories and industries using **historical baseline estimates** from two datasets:
  - **Climate TRACE** — 2,391 facilities (power plants, manufacturing, mining, waste sites)
  - **Global Energy Monitor (GEM)** — 1,603 facilities (coal plants, solar farms, cement plants, iron ore mines, etc.)
- **AI-Powered Authority Reporting** — Uses **Google Gemini** (via LangChain) to automatically generate highly contextual, formal complaint emails based on local AQI and industrial data. The app provides a 1-click "Copy to Clipboard" feature and **automatically logs all generated emails** in the database to prevent false claims and maintain a historical audit trail.
- **Emissions Analytics** — Identifies the top contributors to PM2.5 pollution and plots monthly emission trends.
- **Factory Leaderboard** — Top 10 biggest industrial polluters in any selected area.

## 📂 Project Structure

```
ET hackathon/
├── app.py                  # Main Streamlit app (Routing & Global UI)
├── pages/                  # Multi-page application structure
│   ├── landing.py          # Public landing page with hero & metrics
│   ├── auth.py             # Login and Sign-up logic
│   ├── dashboard.py        # Main AQI search and tiles dashboard
│   └── city_detail.py      # Detailed city analytics, maps, and reporting
├── db.py                   # Neon PostgreSQL connection & User Auth (CRUD)
├── mail_service.py         # Google Gemini LLM email generation logic
├── requirements.txt        # Python dependencies
├── .env                    # Secrets (Database URL, Gemini API Keys)
├── data/                   # Pre-processed Runtime JSON data files
├── scripts/                # Data fetching & preprocessing scripts
└── raw_data/               # Raw source data (Climate TRACE, GEM)
```

## 🚀 Quick Start

### 1. Install Dependencies

Ensure you have Python installed, then set up your environment:

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory and add your credentials:

```env
DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>?sslmode=require
GEMINI_API_KEY_1=your_gemini_api_key_1
GEMINI_API_KEY_2=your_gemini_api_key_2
```
*(Note: The system supports key rotation between multiple Gemini API keys for high availability).*

### 3. Run the Application

```bash
python -m streamlit run app.py
```

The app will launch your browser at [http://localhost:8501](http://localhost:8501).

> **Note:** The `data/` directory already contains pre-processed JSON files for immediate use.

### 4. (Optional) Refresh Live Data & Preprocessing

To fetch the latest AQI readings from OpenAQ or re-process industrial datasets:

```bash
python scripts/fetch_aqi_data.py             # Fetches live AQI data
python scripts/preprocess_factories.py       # Climate TRACE → JSON
python scripts/preprocess_gem_data.py        # GEM → JSON
python scripts/preprocess_city_emissions.py  # Emissions → JSON
```

## 🛠️ Tech Stack

- **Frontend & Routing:** [Streamlit](https://streamlit.io) (Multi-page Architecture)
- **Database:** [Neon (Serverless PostgreSQL)](https://neon.tech/) + `psycopg2`
- **Authentication:** `bcrypt` for password hashing
- **AI / LLM:** [Google Gemini](https://ai.google.dev/) + [LangChain](https://www.langchain.com/)
- **Maps:** [Folium](https://python-visualization.github.io/folium/) + `streamlit-folium`
- **Charts:** [Altair](https://altair-viz.github.io/)
- **Data Processing:** [Pandas](https://pandas.pydata.org/)
- **APIs:** [OpenAQ v3 API](https://docs.openaq.org/)

## 🚥 AQI Categories (India NAQI)

| Category | AQI Range | Color |
|----------|-----------|-------|
| Good | 0–50 | 🟢 Green |
| Satisfactory | 51–100 | 🟡 Yellow-Green |
| Moderate | 101–200 | 🟡 Yellow |
| Poor | 201–300 | 🟠 Orange |
| Very Poor | 301–400 | 🔴 Red |
| Severe | 400+ | 🟤 Maroon |
