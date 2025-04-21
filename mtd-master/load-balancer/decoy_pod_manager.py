from kubernetes import client, config
import random
import datetime
import os

"""Create decoy pods """
def create_decoy_pods(namespace: str, num_pods: int, label: str):
    """
    Create decoy pods to confuse attackers.
    """
    try:
        decoy_pods = []
        for i in range(num_pods):
            
            """Generate decoy pod names and random IP addresses for each """

            pod_name = f"decoy-pod-{random.randint(1000, 9999)}"
            decoy_pod = client.V1Pod(
                metadata=client.V1ObjectMeta(
                    name=pod_name,
                    labels={'app': 'decoy', 'mtd-rotation': label}
                ),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(
                        name="decoy-container",
                        image="nginx",  # Use a simple decoy container like NGINX
                    )]
                )
            )
            decoy_pods.append(decoy_pod)
            api_instance = client.CoreV1Api()
            api_instance.create_namespaced_pod(namespace=namespace, body=decoy_pod)
        
        print(f"Created {num_pods} decoy pods with label {label}")
    except Exception as e:
        print(f"Error creating decoy pods: {e}")

"""Rotate decoy pods (delete old ones and create new ones)"""
def rotate_decoy_pods(namespace: str, label: str):
    """
    Rotate decoy pods periodically to confuse attackers.
    """
    try:
        """Delete existing decoy pods"""
        
        api_instance = client.CoreV1Api()
        pods = api_instance.list_namespaced_pod(namespace=namespace, label_selector=f"app=decoy,mtd-rotation={label}")
        
        for pod in pods.items:
            api_instance.delete_namespaced_pod(pod.metadata.name, namespace)
            print(f"Deleted decoy pod {pod.metadata.name}")
        
        create_decoy_pods(namespace, 3, label)  # Create 3 new decoy pods with the new label
    except Exception as e:
        print(f"Error rotating decoy pods: {e}")
