import os
import sys
import time
import argparse
import psutil

def format_bytes(bytes_val):
    if bytes_val < 1024:
        return f"{bytes_val:.1f} B/s"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB/s"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB/s"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.1f} GB/s"

class SimpleMonitor:
    def __init__(self):
        self.prev_io = psutil.net_io_counters()
        self.prev_time = time.time()

    def get_metrics(self):
        # CPU
        cpu_usage = int(round(psutil.cpu_percent(interval=None)))
        cpu_freq = psutil.cpu_freq()
        if cpu_freq and cpu_freq.current:
            speed_ghz = round(cpu_freq.current / 1000.0, 1)
            speed_str = f"{speed_ghz} GHz"
        else:
            speed_str = "N/A"
        
        # RAM
        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024**3), 1)
        ram_total_gb = round(ram.total / (1024**3), 1)
        ram_percent = int(round(ram.percent))
        
        # Cache / Buffers (if reported, otherwise estimate from available)
        cached_bytes = getattr(ram, 'cached', getattr(ram, 'buffers', 0))
        if cached_bytes == 0 and hasattr(ram, 'available'):
            cached_bytes = max(0, ram.available - (ram.total - ram.used))
        cached_gb = round(cached_bytes / (1024**3), 1)

        # Network Speed
        curr_io = psutil.net_io_counters()
        curr_time = time.time()
        time_delta = max(1.0, curr_time - self.prev_time)
        
        upload_speed = (curr_io.bytes_sent - self.prev_io.bytes_sent) / time_delta
        download_speed = (curr_io.bytes_recv - self.prev_io.bytes_recv) / time_delta
        
        self.prev_io = curr_io
        self.prev_time = curr_time

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_percent": cpu_usage,
            "cpu_speed": speed_str,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_percent": ram_percent,
            "cached_gb": cached_gb,
            "upload": format_bytes(upload_speed),
            "download": format_bytes(download_speed)
        }

    def export_csv(self, metrics, filename="system_metrics.csv"):
        import csv
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp",
                "CPU Utilization (%)",
                "CPU Speed",
                "RAM Memory Usage",
                "RAM Cache (GB)",
                "RAM In Use (GB)",
                "Network Upload",
                "Network Download"
            ])
            writer.writerow([
                metrics["timestamp"],
                f'{metrics["cpu_percent"]}%',
                metrics["cpu_speed"],
                f'{metrics["ram_used_gb"]}/{metrics["ram_total_gb"]} GB({metrics["ram_percent"]}%)',
                f'{metrics["cached_gb"]} GB',
                f'{metrics["ram_used_gb"]} GB',
                metrics["upload"],
                metrics["download"]
            ])
        return os.path.abspath(filename)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    parser = argparse.ArgumentParser(description="System Performance Terminal Monitor")
    parser.add_argument("--export", action="store_true", help="Export metrics snapshot to CSV and exit")
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds (default: 2.0)")
    args = parser.parse_args()

    monitor = SimpleMonitor()

    if args.export:
        time.sleep(0.5)
        metrics = monitor.get_metrics()
        saved_file = monitor.export_csv(metrics)
        print(f"Successfully exported CSV report snapshot to: {saved_file}")
        sys.exit(0)

    print("Starting System Performance Monitor... Press Ctrl+C to exit.")
    time.sleep(0.5)

    try:
        while True:
            metrics = monitor.get_metrics()
            clear_screen()
            
            output = f"""system performance:

CPU
  utilization:{metrics['cpu_percent']}%

  speed:{metrics['cpu_speed']}

RAM
  memory usage: {metrics['ram_used_gb']}/{metrics['ram_total_gb']} GB({metrics['ram_percent']}%)

  CACHE:{metrics['cached_gb']} GB

  In use(compressed) :{metrics['ram_used_gb']} GB

NETWORK
  Upload: {metrics['upload']}

  Download: {metrics['download']}
"""
            print(output)
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\nExited monitor.")

if __name__ == "__main__":
    main()
