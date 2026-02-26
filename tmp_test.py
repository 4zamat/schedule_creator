import pdfplumber
import pprint
import sys

path = r"d:\Projects\Schedule Creator\Schedule_1 course M_3 trim.pdf"
with open("tmp_out.txt", "w", encoding="utf-8") as f:
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            f.write(f"--- Page {i+1} ---\n")
            
            text = page.extract_text()
            f.write("TEXT:\n")
            f.write(text[:500] + "\n...\n")
            
            f.write("\nTABLES:\n")
            tables = page.extract_tables()
            if tables:
                for r in tables[0][:15]:
                    f.write(str(r) + "\n")
            else:
                f.write("NO TABLES FOUND\n")
                
            f.write("======================\n\n")
            if i >= 1:
                break
