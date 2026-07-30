import os
import time
import csv
import io
from flask import Flask, render_template, jsonify, Response, send_file
from flask_cors import CORS
import psutil

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Global variables for network speed calculations
prev_net_io = None
prev_net_time = None

def get_network_speed():
    global prev_net_io, prev_net_time
    
    current_io = psutil.net_io_counters()
    current_time = time.time()
    
    if prev_net_io is None or prev_net_time is None:
        upload_speed = 0.0
        download_speed = 0.0
    else:
        time_delta = current_time - prev_net_time
        if time_delta <= 0:
            time_delta = 1.0
            
        bytes_sent_delta = current_io.bytes_sent - prev_net_io.bytes_sent
        bytes_recv_delta = current_io.bytes_recv - prev_net_io.bytes_recv
        
        upload_speed = max(0.0, bytes_sent_delta / time_delta)
        download_speed = max(0.0, bytes_recv_delta / time_delta)
        
    prev_net_io = current_io
    prev_net_time = current_time
    
    return {
        "upload_speed_bps": upload_speed,
        "download_speed_bps": download_speed,
        "total_sent_bytes": current_io.bytes_sent,
        "total_recv_bytes": current_io.bytes_recv
    }

def format_bytes(bytes_val):
    if bytes_val < 1024:
        return f"{bytes_val:.1f} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

def get_system_metrics():
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores_percent = psutil.cpu_percent(interval=None, percpu=True)
    cpu_freq = psutil.cpu_freq()
    cpu_freq_current = round(cpu_freq.current / 1000.0, 2) if (cpu_freq and cpu_freq.current) else 0.0
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False) or cpu_count_logical

    # Memory / RAM
    ram = psutil.virtual_memory()
    
    # Disk Usage (Primary disk)
    drive_path = 'C:\\' if os.name == 'nt' else '/'
    try:
        disk = psutil.disk_usage(drive_path)
    except Exception:
        disk = psutil.disk_usage('/')

    # Network Speed
    net_speed = get_network_speed()

    metrics = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": {
            "usage_percent": round(cpu_percent, 1),
            "cores_percent": [round(c, 1) for c in cpu_cores_percent],
            "frequency_ghz": cpu_freq_current,
            "logical_cores": cpu_count_logical,
            "physical_cores": cpu_count_physical
        },
        "ram": {
            "usage_percent": round(ram.percent, 1),
            "total_gb": round(ram.total / (1024**3), 2),
            "used_gb": round(ram.used / (1024**3), 2),
            "available_gb": round(ram.available / (1024**3), 2)
        },
        "disk": {
            "usage_percent": round(disk.percent, 1),
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "mount_point": drive_path
        },
        "network": {
            "upload_formatted": f"{format_bytes(net_speed['upload_speed_bps'])}/s",
            "download_formatted": f"{format_bytes(net_speed['download_speed_bps'])}/s",
            "upload_bps": net_speed['upload_speed_bps'],
            "download_bps": net_speed['download_speed_bps'],
            "total_sent_formatted": format_bytes(net_speed['total_sent_bytes']),
            "total_recv_formatted": format_bytes(net_speed['total_recv_bytes'])
        }
    }
    return metrics

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metrics')
def api_metrics():
    return jsonify(get_system_metrics())

@app.route('/api/export-csv')
def export_csv():
    metrics = get_system_metrics()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Timestamp",
        "CPU Usage (%)",
        "CPU Frequency (GHz)",
        "CPU Cores (Logical)",
        "RAM Usage (%)",
        "RAM Used (GB)",
        "RAM Total (GB)",
        "Disk Usage (%)",
        "Disk Used (GB)",
        "Disk Total (GB)",
        "Network Upload Speed",
        "Network Download Speed"
    ])
    
    # Write row data
    writer.writerow([
        metrics["timestamp"],
        f'{metrics["cpu"]["usage_percent"]}%',
        f'{metrics["cpu"]["frequency_ghz"]} GHz',
        metrics["cpu"]["logical_cores"],
        f'{metrics["ram"]["usage_percent"]}%',
        f'{metrics["ram"]["used_gb"]} GB',
        f'{metrics["ram"]["total_gb"]} GB',
        f'{metrics["disk"]["usage_percent"]}%',
        f'{metrics["disk"]["used_gb"]} GB',
        f'{metrics["disk"]["total_gb"]} GB',
        metrics["network"]["upload_formatted"],
        metrics["network"]["download_formatted"]
    ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=system_metrics_{int(time.time())}.csv"}
    )

if __name__ == '__main__':
    get_network_speed()
    print("Starting System Resource Monitor on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
