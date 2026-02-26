import uuid
import datetime

def generate_ics_string(selected_events):
    day_mapping = {
        'Monday': '20260309',
        'Tuesday': '20260310',
        'Wednesday': '20260311',
        'Thursday': '20260312',
        'Friday': '20260313',
        'Saturday': '20260314',
        'Sunday': '20260315',
    }
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AITU Schedule Creator//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:AITU Schedule - Trimester 3",
        "X-WR-TIMEZONE:Asia/Almaty",
    ]
    
    for ev in selected_events:
        day_str = ev.get('Day', '').strip()
        time_str = ev.get('Time', '').strip()
        discipline = ev.get('Discipline', '')
        group = ev.get('Group', 'Unknown')
        type_ = ev.get('Type', '')
        lecturer = ev.get('Lecturer', '')
        location = ev.get('Classroom', '')
        
        if day_str not in day_mapping or not time_str:
            continue
            
        base_date = day_mapping[day_str]
        parts = time_str.split('-')
        if len(parts) != 2:
            continue
            
        start_time = parts[0].strip().split(':')
        end_time = parts[1].strip().split(':')
        if len(start_time) != 2 or len(end_time) != 2:
            continue
            
        start_str = start_time[0] + start_time[1] + '00'
        end_str = end_time[0] + end_time[1] + '00'
        
        uid = str(uuid.uuid4())
        dtstamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        
        description = f"Group: {group}\\nType: {type_}\\nLecturer: {lecturer}"
        
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;TZID=Asia/Almaty:{base_date}T{start_str}",
            f"DTEND;TZID=Asia/Almaty:{base_date}T{end_str}",
            "RRULE:FREQ=WEEKLY;UNTIL=20260517T180000Z",
            f"SUMMARY:{discipline}",
            f"LOCATION:{location}",
            f"DESCRIPTION:{description}",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "TRIGGER:-PT10M",
            "END:VALARM",
            "END:VEVENT"
        ])
        
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
