import requests
import time
import threading
import os

def test_download_continuity(base_url, num_downloads=20):
    """
    Test download continuity across rotation events
    """
    download_results = []
    rotation_detected = threading.Event()
    
    def monitor_rotations():
        """Thread to detect rotation events"""
        last_pod_id = None
        while len(download_results) < num_downloads:
            try:
                response = requests.get(f"{base_url}/health")
                if response.status_code == 200:
                    current_pod = response.json()["pod_info"]["pod_name"]
                    if last_pod_id is not None and current_pod != last_pod_id:
                        print(f"Rotation detected: {last_pod_id} -> {current_pod}")
                        rotation_detected.set()
                        threading.Timer(30, rotation_detected.clear).start()
                    last_pod_id = current_pod
            except:
                pass
            time.sleep(5)
    
    def perform_downloads():
        """Thread to perform downloads"""
        for i in range(num_downloads):
            file_size = "large.txt"  # Use large file to increase chances of spanning rotation
            
            result = {
                "download_id": i,
                "start_time": time.time(),
                "completed": False,
                "bytes_received": 0,
                "expected_size": 10485760,  
                "rotation_occurred": False,
                "download_time": None,
                "error": None
            }
            
            try:
                response = requests.get(
                    f"{base_url}/download/{file_size}", 
                    stream=True, 
                    timeout=300  
                )
                
                if response.status_code == 200:

                    if 'Content-Length' in response.headers:
                        result["expected_size"] = int(response.headers['Content-Length'])
                    
                    with open(os.devnull, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                result["bytes_received"] += len(chunk)
                                
                                # Check if rotation occurred during download
                                if rotation_detected.is_set():
                                    result["rotation_occurred"] = True
                    
                    result["completed"] = True
                    result["download_time"] = time.time() - result["start_time"]
                else:
                    result["error"] = f"HTTP {response.status_code}"
            except Exception as e:
                result["error"] = str(e)
            
            download_results.append(result)
            print(f"Download {i+1}/{num_downloads}: {'✓' if result['completed'] else '✗'} " +
                  f"{'(during rotation)' if result['rotation_occurred'] else ''}")
            time.sleep(5)
    
    rotation_thread = threading.Thread(target=monitor_rotations)
    download_thread = threading.Thread(target=perform_downloads)
    
    rotation_thread.start()
    download_thread.start()
    

    download_thread.join()
    
    # Calculate metrics
    downloads_during_rotation = [d for d in download_results if d["rotation_occurred"]]
    successful_rotation_downloads = [d for d in downloads_during_rotation if d["completed"]]
    
    return {
        "total_downloads": len(download_results),
        "successful_downloads": sum(1 for d in download_results if d["completed"]),
        "downloads_during_rotation": len(downloads_during_rotation),
        "successful_rotation_downloads": len(successful_rotation_downloads),
        "rotation_download_success_rate": len(successful_rotation_downloads) / len(downloads_during_rotation) if downloads_during_rotation else 0,
        "avg_download_time": sum(d["download_time"] for d in download_results if d["completed"]) / sum(1 for d in download_results if d["completed"]) if any(d["completed"] for d in download_results) else 0,
        "avg_rotation_download_time": sum(d["download_time"] for d in successful_rotation_downloads) / len(successful_rotation_downloads) if successful_rotation_downloads else 0
    }

# Run the download test
download_results = test_download_continuity("http://127.0.0.1:51417")
print(f"Download success rate during rotation: {download_results['rotation_download_success_rate']*100:.1f}%")
print(f"Average download time during rotation: {download_results['avg_rotation_download_time']:.1f} seconds")
