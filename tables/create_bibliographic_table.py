# Create a latex table of the bibliographic data of the schoolbooks for the paper appendix

import csv

with open('bibliographic_data.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    data = list(reader)

data = sorted(data, key=lambda row: row.get("Kennung", ""))

idiom_order = ["Sursilvan", "Sutsilvan", "Surmiran", "Puter", "Vallader"]

# Group books by idiom
grouped = {idiom: [] for idiom in idiom_order}
for row in data:
    idiom = row.get("Rätoromanische Idiome", "").strip()
    if idiom in grouped:
        grouped[idiom].append(row)

for idiom in idiom_order:
    books = grouped[idiom]
    if books:
        print(f"\\subsection*{{{idiom}}}")
        for row in books:
            isbn = row.get('Kennung', '').replace('ISBN : ', '').strip()
            if " - " in isbn:
                isbn = isbn.split(" - ")[0]
            print(f"\\textbf{{ISBN:}} {isbn}\\\\")
            print(f"\\textbf{{Year:}} {row.get('Erscheinungsjahr', '').strip()}\\\\")
            print(f"\\textbf{{Title:}} {row.get('Titel', '').strip()}.\\\\")
            # print(f"\\textbf{{Editors:}} {row.get('Mitwirkende', '').strip()}.\\\\")
            if row.get("Permalink", "").strip():
                print(f"\\textbf{{Bibliographic record:}} \\url{{{row.get('Permalink', '').strip()}}}\\\\[1em]")
