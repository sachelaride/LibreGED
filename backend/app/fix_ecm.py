with open("api_ecm.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
router_seen = False
for i, line in enumerate(lines):
    if "router = APIRouter()" in line:
        if not router_seen:
            new_lines.append(line)
            router_seen = True
        else:
            print(f"Removed duplicate router at line {i}")
    else:
        new_lines.append(line)

# Ensure router is at the top if not seen
if not router_seen:
    new_lines.insert(9, "router = APIRouter()\n")

with open("api_ecm.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
