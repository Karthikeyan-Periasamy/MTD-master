import requests
import time
import random
import json

def test_persistence(base_url, test_duration=24*3600):
    """
    Simulate installing backdoors and measure how long they persist
    """
    backdoors = []
    start_time = time.time()
    end_time = start_time + test_duration
    
    while time.time() < end_time:
        # Get current pod info
        try:
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                pod_info = response.json()["pod_info"]
                
                # Simulate backdoor installation (just record the pod info)
                backdoor_id = f"backdoor-{random.randint(1000, 9999)}"
                backdoors.append({
                    "id": backdoor_id,
                    "pod_name": pod_info["pod_name"],
                    "pod_ip": pod_info["pod_ip"],
                    "install_time": time.time(),
                    "last_check_time": time.time(),
                    "evicted": False
                })
                
                print(f"Installed {backdoor_id} on {pod_info['pod_name']}")
        except Exception as e:
            print(f"Error installing backdoor: {e}")
        
        # Check existing backdoors
        for backdoor in backdoors:
            if not backdoor["evicted"]:
                try:
                    response = requests.get(f"{base_url}/health")
                    if response.status_code == 200:
                        current_pod = response.json()["pod_info"]
                        
                        """ Check if the pod still exists """
                        if current_pod["pod_name"] == backdoor["pod_name"]:
                            backdoor["last_check_time"] = time.time()
                        else:
                            backdoor["evicted"] = True
                            backdoor["eviction_time"] = time.time()
                            print(f"{backdoor['id']} evicted after {backdoor['eviction_time'] - backdoor['install_time']:.1f} seconds")
                except Exception:
                    
                    pass
        
        time.sleep(60)  # Check every minute
    
    # Calculate persistence 
    persistence_times = []
    for backdoor in backdoors:
        if backdoor["evicted"]:
            persistence_times.append(backdoor["eviction_time"] - backdoor["install_time"])
        else:
            persistence_times.append(time.time() - backdoor["install_time"])
    
    avg_persistence = sum(persistence_times) / len(persistence_times) if persistence_times else 0
    max_persistence = max(persistence_times) if persistence_times else 0
    eviction_rate = sum(1 for b in backdoors if b["evicted"]) / len(backdoors) if backdoors else 0
    
    return {
        "backdoors_installed": len(backdoors),
        "average_persistence_seconds": avg_persistence,
        "maximum_persistence_seconds": max_persistence,
        "eviction_rate": eviction_rate
    }
persistence_results = test_persistence("http://127.0.0.1:51417")
print(f"Average backdoor persistence: {persistence_results['average_persistence_seconds']/60:.1f} minutes")
print(f"Eviction rate: {persistence_results['eviction_rate']*100:.1f}%")
