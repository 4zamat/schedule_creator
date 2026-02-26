import pdfplumber
import re
import pandas as pd

def clean_time(t_str):
    if not t_str: return ""
    
    t_str = t_str.replace('::', ':')
    
    if '-' in t_str:
        parts = t_str.split('-')
        if len(parts) == 2:
            s, e = parts[0].strip(), parts[1].strip()
            # Fix cases like "1900" without colon
            if len(s) == 4 and ':' not in s and s.isdigit(): 
                s = f"{s[:2]}:{s[2:]}"
            if len(e) == 4 and ':' not in e and e.isdigit():
                e = f"{e[:2]}:{e[2:]}"
            t_str = f"{s}-{e}"
            
    # Cleanup any lingering extra colons or strange chars
    # Wait, simple regex replacement just in case
    t_str = re.sub(r'[^\d:\-]', '', t_str)
    return t_str

def extract_schedule(pdf_path):
    data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            match = re.search(r'Group\s+([\w\-]+)', text, re.IGNORECASE)
            group_name = match.group(1) if match else "Unknown"
            
            tables = page.extract_tables()
            if not tables:
                continue
                
            table = tables[0]
            current_day = None
            
            for row in table[1:]:
                # If row is shorter than 6, pad it
                row += [None] * (6 - len(row))
                
                day_cell = row[0] if row[0] is not None else ""
                day_cell = str(day_cell).strip()
                if day_cell:
                    current_day = day_cell
                
                day = current_day
                time_str = str(row[1] if row[1] is not None else "").strip()
                time_str = clean_time(time_str)
                if not time_str:
                    continue
                
                discipline = str(row[2] if row[2] is not None else "").strip()
                classroom = str(row[3] if row[3] is not None else "").strip()
                type_ = str(row[4] if row[4] is not None else "").strip()
                lecturer = str(row[5] if row[5] is not None else "").strip()
                
                # Split disciplines
                disciplines = [d.strip() for d in re.split(r'\n', discipline) if d.strip()]
                classrooms = [c.strip() for c in classroom.split('\n')]
                types = [t.strip() for t in type_.split('\n')]
                lecturers = [l.strip() for l in lecturer.split('\n')]
                
                for i, disc in enumerate(disciplines):
                    data.append({
                        "Group": group_name,
                        "Day": day,
                        "Time": time_str,
                        "Discipline": disc,
                        "Classroom": classrooms[i] if i < len(classrooms) else (classrooms[-1] if classrooms else ""),
                        "Type": types[i] if i < len(types) else (types[-1] if types else ""),
                        "Lecturer": lecturers[i] if i < len(lecturers) else (lecturers[-1] if lecturers else "")
                    })
                    
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = extract_schedule(r"d:\Projects\Schedule Creator\Schedule_1 course M_3 trim.pdf")
    print("Parsed Data Head:")
    print(df.head(10))
    print("\nElective Detection Check:")
    print(df[df['Group'] == 'AAI-2501M']['Discipline'].value_counts())
