# 🌿 India AQI Dashboard

A comprehensive, real-time Air Quality Index monitoring and reporting platform that goes beyond the numbers. By combining live IoT sensor data with geospatial industrial emissions, we empower citizens and policymakers to identify exact pollution sources and take immediate AI-driven action.

## 🏆 Hackathon Evaluation Mapping

This project was built specifically to address the core problem statement. Here is how our solution aligns with the judging criteria:

### 1. Innovation & Technical Excellence (45%)
- **Real-Time IoT Sensor Data (CAAQMS):** Live PM2.5 data ingestion from 500+ government stations across India (via OpenAQ).
- **Geospatial Intelligence & Remote Sensing:** Pinpoints 3,900+ industrial facilities using satellite-derived data from Climate TRACE and Global Energy Monitor (GEM), mapped on a 5x5km high-resolution grid.
- **LLMs for Multi-Language Citizen Communication:** Integrates Google Gemini via LangChain to dynamically  generate formal, data-backed complaint emails to local authorities. This demonstrates a massive reduction in response time from signal to intervention.
- **Predictive Analytics (Roadmap):** While current analytics focus on historical seasonal emission trends and precise source attribution, the backend architecture is prepared to ingest ARIMA/LSTM models for hyperlocal AQI forecasting in Phase 2.

### 2. Business Impact & Scalability (40%)
- **Actionable Enforcement Recommendations:** Bridges the gap between open environmental data and regulatory enforcement by providing domain experts and citizens with a 1-click, evidence-based reporting tool.
- **Serverless & Scalable:** Built on a stateless Streamlit frontend with a Neon Serverless PostgreSQL database for secure user authentication and audit logging. The data pipeline preprocesses heavy datasets into lightweight JSON artifacts to ensure zero latency.

### 3. User Experience (15%)
- **Professional UI:** A modern, responsive design using
glassmorphism, dynamic hover effects, and a global navigation header.
- **Data Accessibility:** Transforms complex atmospheric and emissions data into a simple "Top 10 Polluters Leaderboard" and intuitive pie charts for the average citizen.

## 📁 Expected Deliverables Included
- **Working Prototype:** Fully functional via Streamlit
- **Architecture Diagram:** Available in `docs/architecture_diagram.pdf`
- **Presentation Deck:** Available in `docs/presentation_deck.pdf`
- **Demo Video:** `[INSERT YOUTUBE LINK TO DEMO VIDEO HERE]`


## 📂 Project Structure

```
Monitoring-AQI-main/
├── app.py                 # Main App (Contains Dashboard routing & City Detail map logic)
├── pages/
│   ├── landing.py         # Public landing page with hero &
metrics
│   └── auth.py            # Login and Sign-up logic
├── db.py                  # Neon PostgreSQL connection & User
Auth (CRUD)
├── mail_service.py        # Google Gemini LLM email
generation logic
├── requirements.txt       # Python dependencies
├── .env                   # Secrets (Database URL, Gemini API Keys)
├── data/                  # Pre-processed Runtime JSON data
files
├── scripts/               # Data fetching & preprocessing
scripts
├── docs/                  # Hackathon deliverables (Diagrams,
Decks, PDFs)
└── roadmap.md             # Detailed project walkthrough &
decisions
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

**Option A: Use the Live Hosted Version (Recommended)**

Simply visit the deployed app:
👉 https://rishabh-b-4pycdnmzfry8dih5z2jby5.streamlit.app/

**Option B: Run Locally**

```bash
streamlit run app.py

The app will launch your browser at http://localhost:8501.


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