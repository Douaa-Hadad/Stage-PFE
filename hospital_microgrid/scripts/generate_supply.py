import sys
from pathlib import Path

# Ensure the scripts directory is in sys.path so we can import peer scripts
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.append(str(scripts_dir))

from generate_solar import generate_solar
from generate_wind import generate_wind
from generate_grid import generate_grid

def main():
    print("Generating Solar Supply Data...")
    generate_solar()
    print("Generating Wind Supply Data...")
    generate_wind()
    print("Generating Grid Supply Data...")
    generate_grid()

if __name__ == "__main__":
    main()
