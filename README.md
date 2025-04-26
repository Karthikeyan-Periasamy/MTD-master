# MTD-master


# Moving Target Defense

A project implementing Moving Target Defense (MTD) strategies using Docker and Python to enhance network security.

## Installation

### Prerequisites
Ensure you have **Python** , **Docker** , **minikube**, **Kuberentes** installed.

#### Python
Install Python:

pip install python

#### Docker
Install Docker by following instructions at Docker's official site.

#### Kuberentes 
Install Kuberentes or use the Docker Kuberenetes - Settings - Kuberentes - Enable & setup the cluster node

#### minikube
Once docker installed, login to the docker. 
Then open the Terminal & install the minikube

Download the Files from the Github

Open a terminal and navigate to the folder containing the files.

use command to navigate to the file "cd <file_path>"

#### Docker Setup

Build the Docker Image 

- Navigate Load balancer create the docker image
- NAvigate to Session manager create the docker image
- Navigate to Webapp1 create the docker image

Run the following command to build the Docker image:
```
docker build -t "your_image_name" . 
``` 
Verify the image build:
```
docker images
```
Run the Docker Image

To start the Docker container, use:
```
docker run "your_image_name"
```
If the above command doesn’t work, try running it with elevated privileges:
```
docker run --privileged -it "your_image_name"
```
Access the Running Container

Open another terminal.

List running containers to find the container ID and port:
```
docker ps
```
Use the container port to enter the running container:
```
docker exec -it "container_id" /bin/bash
```

Open a new Terminall , start the minikube
```
minikube start
```
check miniokube is runing or not 
```
minikube cluster info
```
Navigate to the Kube Folder, deploy all the yaml files or do it separately - Make sure docker images are build & check the docker image names in the yaml file as well
```
kubectl apply -f./
```
once it done, the conatiner will start creating it will took 4-5 min, you can check with these command
```
kubectl get pods
```
You can able to modfiy the replica sets in the webap.yml file to increase or derease of the webapp pod service

once the conatiner is created and started to run, then navigate to the webapp by the following link
```
localhost:30001
```
it will show the app is runing and pod changes and pod ip changes in the webapp...
for the frontend, i ahve implemented with the javascript where if we put the ui at the end of the link, it will show the complete webapp
```
localhost:30001/ui
```

IF this is not working, check the webapp pods are runing correctly, then uase give below commands to get the webapp service url - where it will handles all the webapp service related pods
```
minikube service webapp-service --url
```
This is will so the url , copy paste that in the web-browser, the app will be running.





