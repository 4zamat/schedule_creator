import os
import pandas as pd
from extractor import extract_schedule

def build_database(schedules_dir="schedules", output_csv="database.csv"):
    if not os.path.exists(schedules_dir):
        print(f"Directory '{schedules_dir}' does not exist.")
        return

    all_dfs = []
    
    for filename in os.listdir(schedules_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(schedules_dir, filename)
            program_name = os.path.splitext(filename)[0] # e.g. "Schedule_1 course M_3 trim" -> "Schedule_1 course M_3 trim"
            
            print(f"Parsing: {filename}...")
            try:
                df = extract_schedule(pdf_path)
                if not df.empty:
                    df['Program'] = program_name
                    all_dfs.append(df)
            except Exception as e:
                print(f"Failed to parse {filename}: {e}")
                
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_csv(output_csv, index=False)
        print(f"\nSuccess! Built {output_csv} with {len(final_df)} extracted classes across {len(all_dfs)} programs.")
    else:
        print("\nNo valid schedule data found.")

if __name__ == "__main__":
    build_database()
