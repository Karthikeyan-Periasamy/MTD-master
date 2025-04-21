import boto3
import os

# This function will update the DNS record with a new IP address
def update_dns_record(new_ip: str):
    """
    Update the DNS record for the given IP address using AWS Route 53.
    """
    try:
        # Create Route 53 client
        route53_client = boto3.client('route53')
        
        hosted_zone_id = os.getenv('ROUTE53_HOSTED_ZONE_ID')
        domain_name = os.getenv('DOMAIN_NAME')  # e.g., "app.example.com"
        
        # Prepare the DNS record change request
        change_batch = {
            'Changes': [
                {
                    'Action': 'UPSERT', 
                    'ResourceRecordSet': {
                        'Name': domain_name,
                        'Type': 'A',
                        'TTL': 60,  # Time-to-live for the DNS record
                        'ResourceRecords': [{'Value': new_ip}]
                    }
                }
            ]
        }
        
        # Update the DNS record
        route53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=change_batch
        )
        
        print(f"DNS record for {domain_name} updated to IP: {new_ip}")
    except Exception as e:
        print(f"Error updating DNS record: {e}")
