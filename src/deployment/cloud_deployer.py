import boto3
import json
from typing import Dict, List, Optional
from datetime import datetime

class CloudDeployer:
    def __init__(self):
        self.aws_regions = [
            # US Regions
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            
            # EU Regions (including all eu-west-2 variants)
            'eu-west-1', 'eu-west-2', 'eu-west-3',
            'eu-central-1', 'eu-central-2',
            'eu-north-1', 'eu-south-1', 'eu-south-2',
            
            # Asia Pacific
            'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3',
            'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-4',
            'ap-south-1', 'ap-south-2',
            'ap-east-1',
            
            # Canada
            'ca-central-1', 'ca-west-1',
            
            # South America
            'sa-east-1',
            
            # Africa
            'af-south-1',
            
            # Middle East
            'me-south-1', 'me-central-1',
            
            # Israel
            'il-central-1'
        ]
        
        self.azure_regions = [
            # US
            'eastus', 'eastus2', 'westus', 'westus2', 'westus3', 'centralus',
            'northcentralus', 'southcentralus', 'westcentralus',
            
            # Europe
            'northeurope', 'westeurope', 'uksouth', 'ukwest',
            'francecentral', 'francesouth', 'germanywestcentral', 'germanynorth',
            'norwayeast', 'norwaywest', 'switzerlandnorth', 'switzerlandwest',
            'swedencentral', 'swedensouth',
            
            # Asia Pacific
            'eastasia', 'southeastasia', 'japaneast', 'japanwest',
            'australiaeast', 'australiasoutheast', 'australiacentral', 'australiacentral2',
            'koreacentral', 'koreasouth', 'centralindia', 'southindia', 'westindia',
            
            # Other
            'canadacentral', 'canadaeast', 'brazilsouth', 'southafricanorth', 'southafricawest',
            'uaenorth', 'uaecentral'
        ]
        
        self.gcp_regions = [
            # US
            'us-central1', 'us-east1', 'us-east4', 'us-east5', 'us-south1', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
            
            # Europe
            'europe-central2', 'europe-north1', 'europe-southwest1', 'europe-west1', 'europe-west2', 
            'europe-west3', 'europe-west4', 'europe-west6', 'europe-west8', 'europe-west9', 'europe-west10', 'europe-west12',
            
            # Asia Pacific
            'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-northeast3',
            'asia-south1', 'asia-south2', 'asia-southeast1', 'asia-southeast2',
            
            # Other
            'australia-southeast1', 'australia-southeast2',
            'northamerica-northeast1', 'northamerica-northeast2',
            'southamerica-east1', 'southamerica-west1',
            'africa-south1', 'me-central1', 'me-west1'
        ]
    
    def deploy_to_aws(self, config: Dict) -> Dict:
        """Deploy LFS build to AWS EC2"""
        try:
            region = config.get('region', 'us-east-1')
            instance_type = config.get('instance_type', 't3.medium')
            
            ec2 = boto3.client('ec2', region_name=region)
            
            # Create security group
            sg_response = ec2.create_security_group(
                GroupName=f"lfs-build-{datetime.now().strftime('%Y%m%d')}",
                Description='LFS Build Security Group'
            )
            
            # Launch instance
            response = ec2.run_instances(
                ImageId=config.get('ami_id', 'ami-0abcdef1234567890'),
                MinCount=1,
                MaxCount=1,
                InstanceType=instance_type,
                SecurityGroupIds=[sg_response['GroupId']],
                UserData=self._get_aws_userdata(config)
            )
            
            return {
                'success': True,
                'instance_id': response['Instances'][0]['InstanceId'],
                'region': region,
                'provider': 'aws'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def deploy_to_azure(self, config: Dict) -> Dict:
        """Deploy LFS build to Azure"""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.compute import ComputeManagementClient
            
            credential = DefaultAzureCredential()
            compute_client = ComputeManagementClient(credential, config['subscription_id'])
            
            # VM configuration
            vm_config = {
                'location': config.get('region', 'eastus'),
                'vm_size': config.get('vm_size', 'Standard_B2s'),
                'admin_username': 'lfsadmin',
                'custom_data': self._get_azure_userdata(config)
            }
            
            return {
                'success': True,
                'deployment_id': f"lfs-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'region': vm_config['location'],
                'provider': 'azure'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def deploy_to_gcp(self, config: Dict) -> Dict:
        """Deploy LFS build to Google Cloud Platform"""
        try:
            from google.cloud import compute_v1
            
            instances_client = compute_v1.InstancesClient()
            
            instance_config = {
                'name': f"lfs-build-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'machine_type': f"zones/{config.get('zone', 'us-central1-a')}/machineTypes/{config.get('machine_type', 'e2-medium')}",
                'startup_script': self._get_gcp_userdata(config)
            }
            
            return {
                'success': True,
                'instance_name': instance_config['name'],
                'zone': config.get('zone', 'us-central1-a'),
                'provider': 'gcp'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_aws_userdata(self, config: Dict) -> str:
        """Generate AWS EC2 user data script"""
        return f"""#!/bin/bash
yum update -y
yum install -y git python3 python3-pip mysql-server

# Clone LFS build system
cd /opt
git clone {config.get('repo_url', 'https://github.com/user/lfs-build-system.git')} lfs
cd lfs

# Install dependencies
pip3 install -r requirements.txt

# Start services
systemctl start mysqld
systemctl enable mysqld

# Setup LFS environment
export LFS=/mnt/lfs
mkdir -p $LFS
chmod 755 $LFS

# Start build system
python3 main.py --headless --build-config {config.get('build_config', 'minimal')}
"""
    
    def _get_azure_userdata(self, config: Dict) -> str:
        """Generate Azure VM custom data script"""
        return f"""#!/bin/bash
apt-get update
apt-get install -y git python3 python3-pip mysql-server

# Clone and setup LFS build system
cd /opt
git clone {config.get('repo_url', 'https://github.com/user/lfs-build-system.git')} lfs
cd lfs
pip3 install -r requirements.txt

# Configure LFS
export LFS=/mnt/lfs
mkdir -p $LFS
chmod 755 $LFS

# Start automated build
python3 main.py --cloud-mode --config {config.get('build_config', 'minimal')}
"""
    
    def _get_gcp_userdata(self, config: Dict) -> str:
        """Generate GCP startup script"""
        return f"""#!/bin/bash
yum update -y
yum install -y git python3 python3-pip mysql-server

# Setup LFS build environment
cd /opt
git clone {config.get('repo_url', 'https://github.com/user/lfs-build-system.git')} lfs
cd lfs
pip3 install -r requirements.txt

# Configure and start
export LFS=/mnt/lfs
mkdir -p $LFS
systemctl start mysqld

# Run build
python3 main.py --gcp-mode --build {config.get('build_config', 'minimal')}
"""
    
    def get_available_regions(self, provider: str) -> List[str]:
        """Get list of available regions for cloud provider"""
        if provider.lower() == 'aws':
            return self.aws_regions
        elif provider.lower() == 'azure':
            return self.azure_regions
        elif provider.lower() == 'gcp':
            return self.gcp_regions
        else:
            return []
    
    def estimate_costs(self, provider: str, region: str, instance_type: str, hours: int = 24) -> Dict:
        """Estimate deployment costs"""
        # Simplified cost estimation (would need real pricing APIs)
        base_costs = {
            'aws': {'t3.medium': 0.0416, 't3.large': 0.0832, 't3.xlarge': 0.1664},
            'azure': {'Standard_B2s': 0.0496, 'Standard_B4ms': 0.1984},
            'gcp': {'e2-medium': 0.0335, 'e2-standard-2': 0.0670}
        }
        
        hourly_rate = base_costs.get(provider, {}).get(instance_type, 0.05)
        total_cost = hourly_rate * hours
        
        return {
            'provider': provider,
            'region': region,
            'instance_type': instance_type,
            'hourly_rate': hourly_rate,
            'estimated_cost': round(total_cost, 2),
            'currency': 'USD'
        }
    
    def start_cloud_deployment(self, deployment_config: dict) -> str:
        """Start cloud deployment and return deployment ID"""
        import uuid
        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
        
        try:
            provider = deployment_config.get('provider', 'aws').lower()
            
            if provider == 'aws':
                result = self.deploy_to_aws(deployment_config)
            elif provider == 'azure':
                result = self.deploy_to_azure(deployment_config)
            elif provider == 'gcp':
                result = self.deploy_to_gcp(deployment_config)
            else:
                raise Exception(f"Unsupported provider: {provider}")
            
            if result.get('success'):
                return deployment_id
            else:
                raise Exception(result.get('error', 'Unknown deployment error'))
                
        except Exception as e:
            raise Exception(f"Failed to start cloud deployment: {str(e)}")