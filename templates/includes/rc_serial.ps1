Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
cd "C:\Users\andre\OneDrive\Documents\RocrailVolt"
.\.venv\Scripts\Activate.ps1

python - << "EOF"
from apps.rc_car_core import set_serial_backend

# ?? Troca "COM5" pela porta real do teu Arduino / interface
set_serial_backend("COM5")

print("Backend do RC car trocado para SerialBackend em COM5.")
EOF
