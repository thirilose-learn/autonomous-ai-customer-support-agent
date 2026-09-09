import csv
import glob

for path in sorted(glob.glob('processed_data/**/*.csv', recursive=True)):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        col_stats = {col: {'max_len': 0, 'has_empty': False, 'count': 0} for col in reader.fieldnames}
        for row in reader:
            for col, val in row.items():
                col_stats[col]['count'] += 1
                if val == '' or val is None:
                    col_stats[col]['has_empty'] = True
                else:
                    col_stats[col]['max_len'] = max(col_stats[col]['max_len'], len(val))
    print(f'=== {path} ===')
    for col, stat in col_stats.items():
        print(f"  {col}: count={stat['count']}, empty={stat['has_empty']}, max_len={stat['max_len']}")
