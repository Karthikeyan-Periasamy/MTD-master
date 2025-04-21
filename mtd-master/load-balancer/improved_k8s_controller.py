import datetime
import logging
import os
import random
import signal
import uuid
from flask import Flask, request, Response
from typing import List, Dict
from markupsafe import escape
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from pytimeparse.timeparse import timeparse
from kubernetes import client, config
import utils
import dns_updater 

class KubernetesApp:
    def __init__(self, pod_name: str, pod_ip: str):
        self.pod_name = pod_name
        self.pod_ip = pod_ip
        self.hostname = pod_name
        self.initialized = datetime.datetime.now()
        self.logger = utils.create_stdout_logger(logging.DEBUG, pod_name)
        self.logger.info(f"tracking pod {pod_name} at IP {pod_ip}")


class KubernetesController:
    LIVE_APPS = int(os.environ.get("REPLICAS", 3))
    TIME_TO_LIVE = datetime.timedelta(seconds=timeparse(os.environ.get("APP_TTL", "3000s")))
    DECOMMISSION_PERIOD = datetime.timedelta(seconds=timeparse(os.environ.get("APP_DECOMMISSION_PERIOD", "1500s")))
    APP_NAMESPACE = os.environ.get("APP_NAMESPACE", "default")
    APP_LABEL_SELECTOR = os.environ.get("APP_LABEL_SELECTOR", "app=webapp")
    IP_SHUFFLE_ENABLED = os.environ.get("IP_SHUFFLE_ENABLED", "true").lower() == "true"
    GRACEFUL_ROTATION = os.environ.get("GRACEFUL_ROTATION", "true").lower() == "true"

    def __init__(self):

        """ Load kubeconfig """

        if os.path.exists(os.path.expanduser("~/.kube/config")):
            config.load_kube_config()
        else:
            config.load_incluster_config()  # In-cluster configuration
        
        self.k8s_api = client.CoreV1Api()
        self.k8s_apps_api = client.AppsV1Api()
        
        self.logger = utils.create_stdout_logger(logging.DEBUG, "k8s-controller")
        
        """Track active pods"""

        self.active_pods: List[KubernetesApp] = []
        self.next_pods: List[KubernetesApp] = []
        
        """ Initialize pods """
        self.active_pods = self.get_current_pods()
        self.next_pods = self.create_new_pods()

        """ Setup scheduler for pod rotation """
        self.scheduler: BackgroundScheduler = BackgroundScheduler()
        self.rotation_job: Job = self.scheduler.add_job(
            func=lambda: self.rotate_pods(),
            trigger="interval",
            seconds=self.TIME_TO_LIVE.seconds,
            max_instances=1,
            replace_existing=False
        )
        self.scheduler.start()
        
        # Handle shutdown
        signal.signal(signal.SIGTERM, lambda signum, frame: self.shutdown())
        signal.signal(signal.SIGINT, lambda signum, frame: self.shutdown())

    def get_current_pods(self) -> List[KubernetesApp]:
        """Get list of currently running pods with the webapp label"""
        pods = []
        try:
            pod_list = self.k8s_api.list_namespaced_pod(
                namespace=self.APP_NAMESPACE,
                label_selector=self.APP_LABEL_SELECTOR
            )
            
            for pod in pod_list.items:
                if pod.status.phase == 'Running' and pod.status.pod_ip:
                    pods.append(KubernetesApp(pod.metadata.name, pod.status.pod_ip))
            
            honeypot_pods = self.k8s_api.list_namespaced_pod(
                namespace=self.APP_NAMESPACE,
                label_selector="app=opencanary"
            )
            for pod in honeypot_pods.items:
                if pod.status.phase == 'Running' and pod.status.pod_ip:
                   self.logger.info(f"Honeypot running at IP: {pod.status.pod_ip}")

            self.logger.info(f"Found {len(pods)} running pods")
            return pods
        except Exception as e:
            self.logger.error(f"Error getting current pods: {e}")
            return []

    def create_new_pods(self) -> List[KubernetesApp]:
        """Create a new set of pods for the next rotation"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        deployment_name = f"webapp-{timestamp}"
        
        try:
            deployment = self.k8s_apps_api.read_namespaced_deployment(
                name="webapp",
                namespace=self.APP_NAMESPACE
            )
            
            # Modify the deployment for the new instance
            deployment.metadata.name = deployment_name
            deployment.metadata.resource_version = None
            deployment.spec.template.metadata.labels["mtd-rotation"] = timestamp
            deployment.spec.selector.match_labels["mtd-rotation"] = timestamp
            
            self.k8s_apps_api.create_namespaced_deployment(
                namespace=self.APP_NAMESPACE,
                body=deployment
            )
            
            self.logger.info(f"Created new deployment {deployment_name}")
            
            # Wait for the pods to be get ready
            ready_pods = []
            retry_count = 0
            max_retries = 30
            
            while len(ready_pods) < self.LIVE_APPS and retry_count < max_retries:
                pod_list = self.k8s_api.list_namespaced_pod(
                    namespace=self.APP_NAMESPACE,
                    label_selector=f"mtd-rotation={timestamp}"
                )
                
                ready_pods = []
                for pod in pod_list.items:
                    if pod.status.phase == 'Running' and pod.status.pod_ip:
                        ready_pods.append(KubernetesApp(pod.metadata.name, pod.status.pod_ip))
                
                if len(ready_pods) < self.LIVE_APPS:
                    import time
                    time.sleep(1)
                    retry_count += 1
            
            if len(ready_pods) < self.LIVE_APPS:
                self.logger.warning(f"Only {len(ready_pods)} pods are ready after max retries")
            
            return ready_pods
            
        except Exception as e:
            self.logger.error(f"Error creating new pods: {e}")
            return []

    def rotate_pods(self):
        """Rotate active pods with the next set of pods"""
        self.logger.info("Rotating pods")
        
        # Store old pods for later cleanup
        old_pods = self.active_pods
        old_pod_labels = {}
        
        # Extract mtd-rotation labels from old pods
        try:
            for pod in old_pods:
                pod_details = self.k8s_api.read_namespaced_pod(
                    name=pod.pod_name, 
                    namespace=self.APP_NAMESPACE
                )
                if 'mtd-rotation' in pod_details.metadata.labels:
                    old_pod_labels[pod_details.metadata.labels['mtd-rotation']] = True
        except Exception as e:
            self.logger.error(f"Error getting pod labels: {e}")
        
        # Update service selector to point to new pods
        if self.next_pods:
            try:
                # Get first pod to extract the rotation label
                pod_details = self.k8s_api.read_namespaced_pod(
                    name=self.next_pods[0].pod_name, 
                    namespace=self.APP_NAMESPACE
                )
                new_rotation_label = pod_details.metadata.labels.get('mtd-rotation')
                
                if new_rotation_label:
                    """ Update service to new rotation label """ 
                    
                    service = self.k8s_api.read_namespaced_service(
                        name="webapp-service",
                        namespace=self.APP_NAMESPACE
                    )
                    service.spec.selector['mtd-rotation'] = new_rotation_label
                    
                    self.k8s_api.patch_namespaced_service(
                        name="webapp-service",
                        namespace=self.APP_NAMESPACE,
                        body=service
                    )
                    self.logger.info(f"Updated service selector to mtd-rotation={new_rotation_label}")
                    
                    # Update DNS with the new pod IPs
                    new_ip = self.next_pods[0].pod_ip  
                    dns_updater.update_dns_record(new_ip)
            
            except Exception as e:
                self.logger.error(f"Error updating service selector: {e}")
        
        
        self.active_pods = self.next_pods
        
        # cleanup of old pods
        def cleanup_old_deployments():
            try:
                for label in old_pod_labels:
                    self.logger.info(f"Deleting deployment with label mtd-rotation={label}")
                    self.k8s_apps_api.delete_collection_namespaced_deployment(
                        namespace=self.APP_NAMESPACE,
                        label_selector=f"mtd-rotation={label}"
                    )
            except Exception as e:
                self.logger.error(f"Error cleaning up old deployments: {e}")
        
        self.scheduler.add_job(
            func=cleanup_old_deployments,
            trigger="date",
            run_date=datetime.datetime.now() + self.DECOMMISSION_PERIOD
        )
        
        """ Create new set of pods for next rotation """



        self.next_pods = self.create_new_pods()

    def random_app(self) -> KubernetesApp:
        """Return a random app from the active pool"""
        if not self.active_pods:
            self.logger.warning("No active pods available, getting current pods")
            self.active_pods = self.get_current_pods()
            
        if self.active_pods:
            return random.choice(self.active_pods)
        else:
            raise Exception("No active pods available for routing")

    def shutdown(self):
        """ shutdown the controller"""
        self.logger.info("Shutting down controller")
        if self.rotation_job:
            self.rotation_job.remove()
        
        self.scheduler.shutdown(wait=False)
        exit(0)
