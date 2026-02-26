import extractor
df = extractor.extract_schedule('Schedule_1 course M_3 trim.pdf')
with open('debug_out.txt', 'w', encoding='utf-8') as f:
    f.write(df[df['Group']=='AAI-2501M'].to_string())
