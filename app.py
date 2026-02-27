import streamlit as st
import pandas as pd
from extractor import extract_schedule
from calendar_sync import get_calendar_service, get_or_create_calendar, insert_schedule_events

st.set_page_config(page_title="University Calendar Automator", layout="wide")

@st.cache_data
def load_data():
    # Load the pre-parsed CSV database so we don't need raw PDFs on the server
    return pd.read_csv("database.csv")

def get_base64_of_bin_file(bin_file):
    import base64
    import os
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

def main():
    # Load and encode local logo
    logo_base64 = get_base64_of_bin_file("static/AITUlogo.png")
    img_tag = f'<img src="data:image/png;base64,{logo_base64}" width="80" style="margin-right: 15px;">' if logo_base64 else ""

    # Create a nice header with the logo horizontally aligned
    st.markdown(
        f"""
        <div style="display: flex; align-items: center;">
            {img_tag}
            <h1 style="margin: 0; padding: 0; font-size: 2.5rem;">Schedule Automator</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("Automate your Trimester 3 schedule sync to Google Calendar.")

    with st.spinner("Loading schedule data..."):
        try:
            df = load_data()
        except Exception as e:
            st.error(f"Failed to load PDF schedule: {e}")
            return

    programs = df['Program'].unique()
    
    def format_program_name(name):
        clean = name.replace("Schedules_", "").replace("Schedule_", "")
        clean = clean.replace("_", " ").title()
        # Replace specific abbreviations securely based on word boundaries
        import re
        clean = re.sub(r'\bM\b', 'Masters', clean)
        clean = re.sub(r'\bB\b', 'Bachelors', clean)
        clean = re.sub(r'\bTrim\b', 'Trimester', clean)
        return clean.strip()
        
    formatted_programs = {p: format_program_name(p) for p in programs}
    
    selected_program = st.selectbox(
        "Select your Program/Year", 
        options=programs,
        format_func=lambda x: formatted_programs[x]
    )

    if selected_program:
        # Filter dataframe by the selected program to only show relevant groups
        program_df = df[df['Program'] == selected_program]
        groups = program_df['Group'].unique()
        selected_group = st.selectbox("Select your Group", options=groups)

    if selected_program and selected_group:
        group_df = program_df[program_df['Group'] == selected_group].copy()
        
        st.subheader(f"Schedule for {selected_group}")
        st.dataframe(group_df)
        
        st.markdown(f"### Customize your Schedule for **{selected_group}**")
        st.markdown("Select all the subjects you are taking.")
        
        selected_events = []
        
        # Sort dataframe by day of the week and time
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        group_df = group_df.copy()
        group_df['Day'] = pd.Categorical(group_df['Day'], categories=day_order, ordered=True)
        group_df = group_df.sort_values(by=['Day', 'Time'])
        
        for day, df_day in group_df.groupby('Day', observed=False):
            if df_day.empty:
                continue
                
            st.markdown(f"#### {day}")
            for index, row in df_day.iterrows():
                if st.checkbox(f"**{row['Time']}**: {row['Discipline']} ({row['Type']})", key=f"sec_{index}"):
                    selected_events.append(row.to_dict())
        
        from calendar_sync import get_auth_url, get_credentials_from_code, get_calendar_service, get_or_create_calendar, insert_schedule_events
        import urllib.parse
        
        st.divider()
        st.markdown('#### Export Options')
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Sync to your Google Calendar** (Web Auth)")
            
            # Check if we are handling an OAuth Redirect (meaning Google sent us a code)
            query_params = st.query_params
            if "code" in query_params:
                code = query_params["code"]
                
                # Prevent reusing the same code if Streamlit reruns
                if st.session_state.get("last_used_code") == code:
                    st.warning("Calendar sync was already processed. Ready for new changes.")
                    if st.button("Clear URL & Reset"):
                        st.query_params.clear()
                        st.rerun()
                else:
                    try:
                        st.session_state["last_used_code"] = code
                        # Exchange code for creds
                        creds = get_credentials_from_code(code)
                        service = get_calendar_service(creds)
                        calendar_id = get_or_create_calendar(service)
                        
                        import json
                        import os
                        
                        state_val = query_params.get("state", None)
                        events_to_sync = []
                        cache_file = "oauth_events_cache.json"
                        
                        # Load from disk cache using the state parameter as key
                        if state_val and os.path.exists(cache_file):
                            try:
                                with open(cache_file, "r") as f:
                                    cache_data = json.load(f)
                                events_to_sync = cache_data.get(state_val, [])
                                
                                # Clean up cache
                                if state_val in cache_data:
                                    del cache_data[state_val]
                                    with open(cache_file, "w") as fw:
                                        json.dump(cache_data, fw)
                            except Exception:
                                pass
                        
                        if events_to_sync:
                            created_ids = insert_schedule_events(service, calendar_id, events_to_sync)
                            st.success(f"Successfully created {len(created_ids)} events in 'AITU Schedule - Trimester 3'!")
                            st.balloons()
                            st.query_params.clear()
                        else:
                            st.warning("Authorized successfully, but no classes were selected to sync.")
                            st.query_params.clear()
                    except Exception as e:
                        st.error(f"Failed to complete Calendar Sync: {e}")
                        st.query_params.clear()
            else:
                # Normal State: Provide a button that triggers the Google Auth Flow
                if st.button("Sync to my Google Calendar", type="primary"):
                    if not selected_events:
                        st.error("Please select at least one class before syncing.")
                    else:
                        try:
                            auth_url, state = get_auth_url()
                            
                            import json
                            import os
                            
                            # Cache the selected events to disk, keyed by OAuth 'state'
                            cache_file = "oauth_events_cache.json"
                            cache_data = {}
                            if os.path.exists(cache_file):
                                try:
                                    with open(cache_file, "r") as f:
                                        cache_data = json.load(f)
                                except Exception:
                                    pass
                                    
                            cache_data[state] = selected_events
                            with open(cache_file, "w") as f:
                                json.dump(cache_data, f)
                                
                            # Instantly redirect the user's browser to the Google Auth URL
                            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Failed to generate Auth URL. Make sure credentials_web.json is correct: {e}")
            st.markdown("**Public ICS File generation** (Shareable)")
            if selected_events:
                from ics_exporter import generate_ics_string
                ics_data = generate_ics_string(selected_events)
                st.download_button(
                    label="Download .ics Calendar File",
                    data=ics_data,
                    file_name=f"{selected_group}_Trimester_3.ics",
                    mime="text/calendar",
                    use_container_width=True,
                    type="secondary"
                )
            else:
                st.write("Select subjects to generate an ICS file.")
                
        # Footer
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
            "Made with ❤️ by Aza | Пушок"
            "</div>", 
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
