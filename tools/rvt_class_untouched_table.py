"""usage: rvt_class_untouched_table.py LOG... : markdown table (class, elements, result, untouched element pct, verify diffs, refused ops) from rvt_class_pass.py logs. Aggregates only, no file names."""
import sys, ast
print('| class | elements | result | untouched elements % | verify diffs | refused ops |\n|---|---|---|---|---|---|')
for p in sys.argv[1:]:
    for l in open(p):
        try: r = ast.literal_eval(l)
        except Exception: continue
        if not isinstance(r, dict) or 'class' not in r: continue
        print('| %s | %s | %s | %s | %s | %s |' % (r['class'], r.get('class_elements'), r['result'], r.get('elements_untouched_pct', ''), r.get('verify_diffs', ''), ','.join(r.get('refused', {}))))
