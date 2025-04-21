import requests
import time
import random
import threading

def lateral_movement_test(base_url, test_count=100):
    """
    Test lateral movement success rate by attempting to connect 
    from one discovered pod IP to another
    """
    discovered_pods = set()
    lateral_attempts = []
    
    def discover_pods():
        """Thread to discover pods"""
        nonlocal discovered_pods
        while len(lateral_attempts) < test_count:
            try:
                response = requests.get(f"{base_url}/health")
                if response.status_code == 200:
                    pod_ip = response.json()["pod_info"]["pod_ip"]
                    discovered_pods.add(pod_ip)
            except:
                pass
            time.sleep(5)
    
    def attempt_lateral_movement():
        """Thread to attempt lateral movement between discovered pods"""
        nonlocal lateral_attempts
        while len(lateral_attempts) < test_count:
            if len(discovered_pods) >= 2:
                # Pick two random pods
                pod_ips = list(discovered_pods)
                source_ip = random.choice(pod_ips)
                target_ip = random.choice([ip for ip in pod_ips if ip != source_ip])
                
                # Simulate lateral movement
                attempt = {
                    "source_ip": source_ip,
                    "target_ip": target_ip,
                    "timestamp": time.time(),
                    "success": False
                }
                
                try:
                    # Try direct connection to target IP (simulating lateral movement)
                    response = requests.get(f"http://{target_ip}:8080/health", timeout=2)
                    if response.status_code == 200:
                        attempt["success"] = True
                except:
                    # Connection failed - expected with MTD
                    pass
                
                lateral_attempts.append(attempt)
                print(f"Lateral attempt {len(lateral_attempts)}/{test_count}: {'✓' if attempt['success'] else '✗'}")
            
            time.sleep(2)
    
    # Start threads
    discovery_thread = threading.Thread(target=discover_pods)
    movement_thread = threading.Thread(target=attempt_lateral_movement)
    
    discovery_thread.start()
    movement_thread.start()
    
    # Wait for completion
    movement_thread.join()
    
    # Calculate results
    success_rate = sum(1 for a in lateral_attempts if a["success"]) / len(lateral_attempts)
    
    return {
        "total_attempts": len(lateral_attempts),
        "successful_attempts": sum(1 for a in lateral_attempts if a["success"]),
        "success_rate": success_rate,
        "unique_pods_discovered": len(discovered_pods)
    }

# Run the test
lateral_results = lateral_movement_test("http://127.0.0.1:51417")
print(f"Lateral movement success rate: {lateral_results['success_rate']*100:.1f}%")
print(f"Unique pods discovered: {lateral_results['unique_pods_discovered']}")