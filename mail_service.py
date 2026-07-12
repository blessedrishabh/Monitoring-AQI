"""
Email generation service for AQI authority reporting.
Uses LangChain + Google Gemini to generate formal complaint emails,
then builds mailto: links so users can send from their own email client.
"""
import os
import json
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# ── Load Contact Directory ────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONTACTS_PATH = os.path.join(APP_DIR, 'data', 'india_aqi_report_contacts.json')

def load_contacts():
    """Load the AQI authority contact directory."""
    try:
        with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def find_authority_for_state(state_name: str) -> dict | None:
    """
    Find the most relevant pollution control authority for a given state.
    Returns a dict with name, email, phone, website, etc.
    """
    contacts = load_contacts()
    state_lower = state_name.lower().strip()

    # Search state pollution control boards
    for board in contacts.get('state_pollution_control_boards', []):
        if board.get('state_ut', '').lower() == state_lower:
            # Extract the best email
            email = board.get('email')
            if isinstance(email, dict):
                # Pick the first available email from the dict
                email = next(iter(email.values()), None)
            return {
                'board_name': board.get('board_name', ''),
                'acronym': board.get('acronym', ''),
                'state': board.get('state_ut', ''),
                'email': email,
                'phone': board.get('phone') or board.get('toll_free', ''),
                'website': board.get('website', ''),
                'complaint_app': board.get('complaint_app', ''),
            }

    # Fallback to CPCB (national body)
    for body in contacts.get('national_bodies', []):
        if body.get('acronym') == 'CPCB':
            email = body.get('email', {})
            if isinstance(email, dict):
                email = email.get('member_secretary_office') or next(iter(email.values()), None)
            return {
                'board_name': body.get('name', ''),
                'acronym': 'CPCB',
                'state': 'National',
                'email': email,
                'phone': body.get('phone', ''),
                'website': body.get('website', ''),
                'complaint_app': body.get('complaint_app', ''),
            }

    return None

def find_municipal_corp(city_name: str) -> dict | None:
    """Find municipal corporation contact for a city."""
    contacts = load_contacts()
    city_lower = city_name.lower().strip()

    for corp in contacts.get('municipal_corporations', []):
        if city_lower in corp.get('city', '').lower():
            return {
                'corp_name': corp.get('corporation_name', ''),
                'acronym': corp.get('acronym', ''),
                'email': corp.get('email'),
                'phone': corp.get('phone', ''),
                'website': corp.get('website', ''),
            }
    return None


# ── LLM Email Generation ─────────────────────────────────────────────
def _get_llm():
    """Get a Gemini LLM instance with key rotation."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    keys = [
        os.getenv("GOOGLE_API_KEY_1"),
        os.getenv("GOOGLE_API_KEY_2"),
    ]

    for key in keys:
        if key:
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=key,
                    temperature=0.3,
                )
                # Test with a minimal call
                llm.invoke("test")
                return llm
            except Exception:
                continue

    raise RuntimeError("All Gemini API keys failed. Please check your .env file.")


def generate_complaint_email(
    city: str,
    state: str,
    area: str,
    aqi: int,
    pm25: float,
    category: str,
    authority_name: str,
    authority_email: str,
    nearby_factories: list[dict] = None,
    station_count: int = 0,
    user_name: str = "Concerned Citizen",
    user_email: str = "",
) -> dict:
    """
    Generate a formal AQI complaint email using LangChain + Gemini.

    Returns:
        dict with keys: 'to', 'subject', 'body', 'mailto_link'
    """
    # Build factory context
    factory_context = ""
    if nearby_factories:
        top_emitters = sorted(
            [f for f in nearby_factories if f.get('emissions_tonnes') and f['emissions_tonnes'] > 0],
            key=lambda x: x['emissions_tonnes'],
            reverse=True
        )[:5]
        if top_emitters:
            factory_lines = []
            for f in top_emitters:
                factory_lines.append(
                    f"  - {f['name']} ({f['sector']}): {f['emissions_tonnes']:,.2f} tonnes emissions"
                )
            factory_context = "\n".join(factory_lines)

    prompt = f"""You are a professional environmental advocate. Write a formal complaint email 
to an Indian pollution control authority about dangerously high air pollution levels.

INSTRUCTIONS:
- Write in a formal, respectful but urgent tone
- Include ALL data provided below — do not omit any numbers
- Compare the AQI reading to India's NAQI safe limit (0-50 = Good)
- If factory data is provided, mention the top industrial polluters by name, but explicitly state that this is historical/baseline emissions data being correlated with the real-time AQI spike.
- Request specific actions: investigation, real-time monitoring, enforcement
- Keep the email concise but data-rich (300-400 words max)
- Do NOT include any subject line — only write the body
- Start the body directly with "Respected Sir/Madam," (no greeting before that)
- End with "Yours sincerely,\\n{user_name}"

DATA FOR THE EMAIL:
- Location: {city}, {area}, {state}
- Current AQI: {aqi} (Category: {category})
- PM2.5 Concentration: {pm25:.2f} µg/m³
- WHO 24-hour guideline for PM2.5: 15 µg/m³
- India NAAQS annual limit for PM2.5: 40 µg/m³
- Number of monitoring stations in area: {station_count}
- Authority being addressed: {authority_name}
{"- Historical baseline industrial emitters nearby (Climate TRACE/GEM estimates):" + chr(10) + factory_context if factory_context else "- No major historical industrial emitters identified in the immediate vicinity."}

Write ONLY the email body text. No subject line, no metadata."""

    try:
        llm = _get_llm()
        response = llm.invoke(prompt)
        body = response.content.strip()
    except Exception as e:
        # Fallback template if LLM fails
        body = f"""Respected Sir/Madam,

I am writing to bring to your urgent attention the alarming air quality levels recorded in {city}, {area}, {state}.

The current Air Quality Index (AQI) in this area stands at {aqi}, classified as "{category}". The PM2.5 concentration has been measured at {pm25:.2f} µg/m³, which significantly exceeds the WHO 24-hour guideline of 15 µg/m³ and India's NAAQS annual limit of 40 µg/m³.

This data has been recorded across {station_count} monitoring station(s) in the vicinity in real-time.

{('Based on historical baseline data from Climate TRACE and Global Energy Monitor, the following industrial facilities in the area are historically recorded as top emitters:' + chr(10) + factory_context) if factory_context else ''}

I respectfully request that your office:
1. Conduct an immediate investigation into the sources of air pollution in this area
2. Ensure real-time air quality monitoring is maintained and made publicly accessible
3. Take enforcement action against any violations of emission standards

The health of residents in this area is at serious risk. I trust that the {authority_name} will take swift action.

Yours sincerely,
{user_name}"""

    subject = f"Urgent: Hazardous Air Quality in {city}, {state} — AQI {aqi} ({category})"

    # Build mailto link
    mailto_params = urllib.parse.urlencode({
        'subject': subject,
        'body': body,
    }, quote_via=urllib.parse.quote)
    mailto_link = f"mailto:{authority_email}?{mailto_params}"

    return {
        'to': authority_email,
        'to_name': authority_name,
        'from_name': user_name,
        'from_email': user_email,
        'subject': subject,
        'body': body,
        'mailto_link': mailto_link,
    }
