import sys, importlib.util
spec = importlib.util.spec_from_file_location('oe', r'C:\wl\openelsewhere.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print('WIN_RM', m._win_rm(sys.argv[1]))
print('OPEN_ELSEWHERE', m.open_elsewhere(sys.argv[1]))
print('CLOSED_FILE', m.open_elsewhere(r'C:\wl\openelsewhere.py'))
