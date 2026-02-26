import streamlit as st
import pandas as pd
from extractor import extract_schedule
from calendar_sync import get_calendar_service, get_or_create_calendar, insert_schedule_events

st.set_page_config(page_title="University Calendar Automator", layout="wide")

@st.cache_data
def load_data():
    # Use absolute or correct relative path to ensure the loader finds it locally
    pdf_path = "Schedule_1 course M_3 trim.pdf"
    return extract_schedule(pdf_path)

def main():
    st.title("🎓 University Calendar Automator")
    st.markdown("Automate your Trimester 3 schedule sync to Google Calendar.")

    with st.spinner("Loading schedule data..."):
        try:
            df = load_data()
        except Exception as e:
            st.error(f"Failed to load PDF schedule: {e}")
            return

    groups = df['Group'].unique()
    selected_group = st.selectbox("Select your Group", options=groups)

    if selected_group:
        group_df = df[df['Group'] == selected_group]
        
        st.subheader(f"Schedule for {selected_group}")
        st.dataframe(group_df)
        
        st.markdown(f"### Customize your Schedule for **{selected_group}**")
        st.markdown("Select all the subjects you are taking. Each subject has a unique color.")
        
        # Generate a distinct color palette based on unique disciplines
        unique_disciplines = group_df['Discipline'].unique()
        colors = ['#FFCDD2', '#F8BBD0', '#E1BEE7', '#D1C4E9', '#C5CAE9', '#BBDEFB', '#B3E5FC', '#B2EBF2', '#B2DFDB', '#C8E6C9', '#DCEDC8', '#F0F4C3', '#FFF9C4', '#FFECB3', '#FFE082', '#FFCC80', '#FFAB91', '#BCAAA4', '#EEEEEE']
        discipline_colors = {disc: colors[i % len(colors)] for i, disc in enumerate(unique_disciplines)}
        
        selected_events = []
        
        for index, row in group_df.iterrows():
            disc_color = discipline_colors.get(row['Discipline'], '#FFFFFF')
            
            # Use columns to put a color swatch/styled text next to the checkbox
            col1, col2 = st.columns([0.05, 0.95])
            with col1:
                st.markdown(f'<div style="width: 20px; height: 20px; background-color: {disc_color}; border-radius: 4px; margin-top: 10px;"></div>', unsafe_allow_html=True)
            with col2:
                if st.checkbox(f"**{row['Day']} {row['Time']}**: {row['Discipline']} ({row['Type']})", key=f"sec_{index}"):
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
                
        # Explanation on Links
        if selected_events:
            with st.expander("Why is there no single 'Add to Calendar' link?"):
                st.markdown(
                    "Google Calendar does not support adding **multiple distinct events** through a single web link URL. "
                    "To add all of your classes at once natively, you must rely on the **Download .ics Calendar File** button above. "
                    "\n\nIf this application were hosted on a public web server (like Heroku or AWS), we could generate a dynamic `.ics` subscription URL (e.g., `webcal://mysite.com/schedule.ics`). "
                    "However, because this is running directly on your local computer, Google's servers cannot reach it to subscribe to the link."
                )

if __name__ == "__main__":
    main()
