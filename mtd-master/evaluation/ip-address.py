import math
from collections import Counter

def analyze_ip_entropy(log_file_path):
    pod_ips = []
    
    with open(log_file_path, 'r') as f:
        for line in f:
            # Extract IP addresses from log entries
            if "at IP" in line:
                ip = re.search(r"at IP ([\d\.]+)", line).group(1)
                pod_ips.append(ip)
    
    # Count occurrences of each IP
    ip_counts = Counter(pod_ips)
    
    # Calculate entropy (randomness measure)
    total_ips = len(pod_ips)
    entropy = 0
    for ip, count in ip_counts.items():
        probability = count / total_ips
        entropy -= probability * math.log2(probability)
    
    # Normalized entropy (0-1 scale)
    max_entropy = math.log2(len(ip_counts)) if len(ip_counts) > 0 else 0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    
    return {
        "unique_ips": len(ip_counts),
        "total_ip_observations": total_ips,
        "ip_reuse_percentage": 100 * (1 - (len(ip_counts) / total_ips)) if total_ips > 0 else 0,
        "entropy": entropy,
        "normalized_entropy": normalized_entropy,
        "predictability_score": 1 - normalized_entropy  # Lower is less predictable
    }

# Run this against your logs
ip_results = analyze_ip_entropy("/path/to/your/logs.txt")
print(f"Unique IPs observed: {ip_results['unique_ips']}")
print(f"IP address predictability: {ip_results['predictability_score']:.4f} (lower is better)")