import streamlit as st
from db import create_user, authenticate_user

def render_auth():
    """Render the Login / Sign-up page."""

    # --- Custom CSS ---
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        .auth-header {
            text-align: center;
            margin-bottom: 10px;
        }
        .auth-header h1 {
            font-family: 'Inter', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #22c1c3, #fdbb2d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }
        .auth-header p {
            font-family: 'Inter', sans-serif;
            color: rgba(255, 255, 255, 0.5);
            font-size: 0.95rem;
            margin: 8px 0 0 0;
        }
        .auth-divider {
            text-align: center;
            color: rgba(255, 255, 255, 0.3);
            font-size: 0.85rem;
            margin: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Center the form
    col1, col2, col3 = st.columns([1.5, 2, 1.5])

    with col2:
        st.markdown("""
        <div class="auth-header">
            <h1>🌿 Welcome</h1>
            <p>Sign in to access the AQI Dashboard</p>
        </div>
        """, unsafe_allow_html=True)

        # Toggle between Login and Signup
        if 'auth_mode' not in st.session_state:
            st.session_state.auth_mode = 'login'

        tab_login, tab_signup = st.tabs(["🔑 Login", "📝 Sign Up"])

        # --- LOGIN TAB ---
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", placeholder="you@example.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                submit = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submit:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        try:
                            user = authenticate_user(email, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.authenticated = True
                                st.session_state.current_page = 'dashboard'
                                st.success(f"Welcome back, {user['full_name']}!")
                                st.rerun()
                            else:
                                st.error("Invalid email or password.")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")

        # --- SIGNUP TAB ---
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                full_name = st.text_input("Full Name", placeholder="John Doe", key="signup_name")
                email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
                password = st.text_input("Password", type="password", placeholder="Min 6 characters", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password", key="signup_confirm")
                submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if submit:
                    # Validation
                    if not full_name or not email or not password or not confirm_password:
                        st.error("Please fill in all fields.")
                    elif '@' not in email or '.' not in email:
                        st.error("Please enter a valid email address.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            user = create_user(full_name, email, password)
                            if user:
                                st.session_state.user = user
                                st.session_state.authenticated = True
                                st.session_state.current_page = 'dashboard'
                                st.success(f"Account created! Welcome, {user['full_name']}!")
                                st.rerun()
                            else:
                                st.error("An account with this email already exists.")
                        except Exception as e:
                            st.error(f"Error creating account: {str(e)}")
