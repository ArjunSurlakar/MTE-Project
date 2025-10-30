import streamlit as st
import pyrebase
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

firebaseConfig = {
    'apiKey': "AIzaSyAzXYx4LsVfV7I5E7tL35rVUdzlFGQqLKU",
    'authDomain': "mte-website-best.firebaseapp.com",
    'databaseURL': "https://mte-website-best-default-rtdb.asia-southeast1.firebasedatabase.app",
    'projectId': "mte-website-best",
    'storageBucket': "mte-website-best.appspot.com",
    'messagingSenderId': "680810824940",
    'appId': "1:680810824940:web:70f8311fda11c3981211c9",
    'measurementId': "G-XYEN19L1EL"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_data" not in st.session_state:
    st.session_state.user_data = None

def cleanemail(email):
    return email.replace(".", "_")

def get_last_1000(email):
    cleaned_email = cleanemail(email)
    data = db.child("users").child(cleaned_email).child("sensor_data").order_by_key().limit_to_last(1000).get()
    df = pd.DataFrame([d.val() for d in data.each()]) if data.each() else pd.DataFrame()
    return df

def filter_data(df, period):
    if df.empty:
        return df
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    now = datetime.now()
    if period == "Today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "1 Month":
        start = now - timedelta(days=30)
    elif period == "6 Months":
        start = now - timedelta(days=180)
    elif period == "8 Months":
        start = now - timedelta(days=240)
    else:
        return df
    return df[df["Timestamp"] >= start]

def signup():
    st.header("Sign Up")
    email = st.text_input("Enter your email", key="signup_email").strip()
    password = st.text_input("Enter your password", type="password", key="signup_pass").strip()
    if st.button("Sign Up"):
        try:
            user = auth.create_user_with_email_and_password(email, password)
            cleaned_email = cleanemail(email)
            user_data = {"username": email, "password": password}
            db.child("users").child(cleaned_email).child(user["localId"]).set(user_data)
            st.success("Account created successfully.")
        except Exception as e:
            st.error(f"Error in signup: {e}")

def login():
    st.header("Login")
    email = st.text_input("Enter your email", key="login_email").strip()
    password = st.text_input("Enter your password", type="password", key="login_pass").strip()
    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.user_data = user
            st.success("Login Successful.")
        except Exception as e:
            st.error(f"Error in login: {e}")

def user_page():
    st.set_page_config(page_title="MTE Dashboard", layout="wide")
    user_email = st.session_state.user_email
    username = cleanemail(user_email)

    st.sidebar.markdown("<h2 style='color:#5BC0DE;'>MTE Dashboard</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<b>User:</b> {username}", unsafe_allow_html=True)
    page = st.sidebar.radio("Navigation", ["Home", "Live Sensor Data", "Historical Plots", "Logout"])

    st.markdown(
        """
        <style>
        body {
            background-color: #0B0C10;
            color: #C5C6C7;
        }
        .stButton>button {
            background-color: #45A29E;
            color: white;
            border-radius: 8px;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if page == "Home":
        st.title(f"Welcome, {user_email}")
        st.write("Use the sidebar to navigate through your dashboard.")

    elif page == "Logout":
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.session_state.user_data = None
            st.success("Logged out successfully.")

    elif page == "Live Sensor Data":
        st.title("Live Sensor Data")
        st_autorefresh(interval=5000, key="data_refresh_live")
        df = get_last_1000(user_email)
        if not df.empty:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            
            fig_live = go.Figure()
            fig_live.add_trace(go.Scatter(x=df["Timestamp"], y=df["Temperature"], mode='lines+markers',
                                          name="Temperature (°C)", line=dict(color="#FF6B6B")))
            fig_live.add_trace(go.Scatter(x=df["Timestamp"], y=df["Humidity"], mode='lines+markers',
                                          name="Humidity (%)", line=dict(color="#4FC3F7")))
            fig_live.update_layout(template="plotly_dark", xaxis_title="Time", yaxis_title="Value", height=400)
            st.plotly_chart(fig_live, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                gauge_temp = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=df["Temperature"].iloc[-1],
                    title={'text': "Current Temperature (°C)"},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#FF6B6B"}}
                ))
                gauge_temp.update_layout(height=300, template="plotly_dark")
                st.plotly_chart(gauge_temp, use_container_width=True)

            with col2:
                gauge_hum = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=df["Humidity"].iloc[-1],
                    title={'text': "Current Humidity (%)"},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#4FC3F7"}}
                ))
                gauge_hum.update_layout(height=300, template="plotly_dark")
                st.plotly_chart(gauge_hum, use_container_width=True)

            st.subheader("Recent Data")
            st.dataframe(df.tail(15))
        else:
            st.info("No live sensor data available.")

    elif page == "Historical Plots":
        st.title("Sensor Data Insights")
        df = get_last_1000(user_email)
        if not df.empty:
            st.subheader("Select Time Range")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("Today"):
                    st.session_state.time_range = "Today"
            with col2:
                if st.button("1 Month"):
                    st.session_state.time_range = "1 Month"
            with col3:
                if st.button("6 Months"):
                    st.session_state.time_range = "6 Months"
            with col4:
                if st.button("8 Months"):
                    st.session_state.time_range = "8 Months"
            with col5:
                if st.button("All Time"):
                    st.session_state.time_range = "All Time"

            if "time_range" not in st.session_state:
                st.session_state.time_range = "All Time"

            filtered_df = filter_data(df, st.session_state.time_range)
            st.subheader(f"Showing Data for: {st.session_state.time_range}")

            fig = px.line(filtered_df, x="Timestamp", y=["Temperature", "Humidity"],
                          title=f"Temperature & Humidity ({st.session_state.time_range})",
                          template="plotly_dark", labels={'value': 'Reading', 'Timestamp': 'Time'})
            st.plotly_chart(fig, use_container_width=True)

            filtered_df["Temp_avg"] = filtered_df["Temperature"].rolling(window=10).mean()
            filtered_df["Hum_avg"] = filtered_df["Humidity"].rolling(window=10).mean()
            trend_fig = px.line(filtered_df, x="Timestamp", y=["Temp_avg", "Hum_avg"],
                                title="Rolling Average Trends", template="plotly_dark")
            st.plotly_chart(trend_fig, use_container_width=True)

            corr = filtered_df[["Temperature", "Humidity"]].corr()
            heatmap = px.imshow(corr, text_auto=True, title="Temperature vs Humidity Correlation",
                                color_continuous_scale="Tealrose", template="plotly_dark")
            st.plotly_chart(heatmap, use_container_width=True)

            st.subheader("Summary Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Temperature (°C)", f"{filtered_df['Temperature'].mean():.2f}")
                st.metric("Max Temperature (°C)", f"{filtered_df['Temperature'].max():.2f}")
                st.metric("Min Temperature (°C)", f"{filtered_df['Temperature'].min():.2f}")
            with col2:
                st.metric("Avg Humidity (%)", f"{filtered_df['Humidity'].mean():.2f}")
                st.metric("Max Humidity (%)", f"{filtered_df['Humidity'].max():.2f}")
                st.metric("Min Humidity (%)", f"{filtered_df['Humidity'].min():.2f}")
        else:
            st.info("No data available to display.")

st.set_page_config(page_title="MTE Dashboard", layout="wide")
st.title("MTE Project Dashboard")

if st.session_state.logged_in:
    user_page()
else:
    auth_choice = st.selectbox("Select Action", ["Login", "Sign Up"])
    if auth_choice == "Sign Up":
        signup()
    else:
        login()
