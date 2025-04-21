import requests
import time
import datetime
import threading
import csv

def monitor_service_availability(base_url, duration=24*3600):
    """
    Monitor service availability, especially during rotation events
    """
    start_time = time.time()
    end_time = start_time + duration
    
    requests_data = []
    rotation_windows = []
    current_rotation = None
    
    def detect_rotations():
        """Thread to detect rotation events from health checks"""
        nonlocal current_rotation
        last_pod_name = None
        
        while time.time() < end_time:
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    current_pod = response.json()["pod_info"]["pod_name"]
                    
                    """ Detect pod change (rotation)"""
                    if last_pod_name is not None and current_pod != last_pod_name:
                        current_rotation = {
                            "start_time": time.time(),
                            "from_pod": last_pod_name,
                            "to_pod": current_pod
                        }
                        print(f"Rotation detected: {last_pod_name} -> {current_pod}")
                    
                    last_pod_name = current_pod
                    
                    
                    if current_rotation and (time.time() - current_rotation["start_time"]) > 300:
                        current_rotation["end_time"] = time.time()
                        rotation_windows.append(current_rotation)
                        current_rotation = None
            except:
                pass
                
            time.sleep(10)
    
    def send_requests():
        """Thread to continuously send requests and record results"""
        while time.time() < end_time:
            request_data = {
                "timestamp": time.time(),
                "success": False,
                "response_time": None,
                "during_rotation": current_rotation is not None
            }
            
            try:
                start_request = time.time()
                response = requests.get(f"{base_url}/", timeout=5)
                request_data["response_time"] = time.time() - start_request
                
                if response.status_code == 200:
                    request_data["success"] = True
            except Exception as e:
                request_data["error"] = str(e)
            
            requests_data.append(request_data)
            
           
            time.sleep(1)
    
    
    rotation_thread = threading.Thread(target=detect_rotations)
    request_thread = threading.Thread(target=send_requests)
    
    rotation_thread.start()
    request_thread.start()
    request_thread.join()
    
    # Calculate metrics
    total_requests = len(requests_data)
    successful_requests = sum(1 for r in requests_data if r["success"])
    
    
    for req in requests_data:
        for rot in rotation_windows:
            if "start_time" in rot and "end_time" in rot:
                if rot["start_time"] <= req["timestamp"] <= rot["end_time"]:
                    req["during_rotation"] = True
    
    rotation_requests = [r for r in requests_data if r["during_rotation"]]
    successful_rotation_requests = sum(1 for r in rotation_requests if r["success"])
    
    # response times
    normal_response_times = [r["response_time"] for r in requests_data if r["response_time"] is not None and not r["during_rotation"]]
    rotation_response_times = [r["response_time"] for r in requests_data if r["response_time"] is not None and r["during_rotation"]]
    
    avg_normal_response = sum(normal_response_times) / len(normal_response_times) if normal_response_times else 0
    avg_rotation_response = sum(rotation_response_times) / len(rotation_response_times) if rotation_response_times else 0
    
    """Save data further analysis """

    with open('service_availability.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timestamp', 'Success', 'Response Time', 'During Rotation'])
        for req in requests_data:
            writer.writerow([
                datetime.datetime.fromtimestamp(req["timestamp"]).strftime('%Y-%m-%d %H:%M:%S'),
                req["success"],
                req["response_time"],
                req["during_rotation"]
            ])
    
    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "overall_availability": successful_requests / total_requests if total_requests > 0 else 0,
        "rotation_requests": len(rotation_requests),
        "successful_rotation_requests": successful_rotation_requests,
        "rotation_availability": successful_rotation_requests / len(rotation_requests) if len(rotation_requests) > 0 else 0,
        "avg_normal_response_time": avg_normal_response,
        "avg_rotation_response_time": avg_rotation_response,
        "response_time_increase": (avg_rotation_response / avg_normal_response - 1) if avg_normal_response > 0 else 0,
        "rotation_events": len(rotation_windows)
    }

""" monitoring """

availability_results = monitor_service_availability("http://127.0.0.1:51417", duration=60)
print(f"Overall availability: {availability_results['overall_availability']*100:.2f}%")
print(f"Availability during rotation: {availability_results['rotation_availability']*100:.2f}%")
print(f"Response time increase during rotation: {availability_results['response_time_increase']*100:.1f}%")