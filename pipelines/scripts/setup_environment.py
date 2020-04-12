import requests
import subprocess
import yaml
import os
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--override', action='store_true')
args = parser.parse_args()

if args.override is True:
 for var in os.environ:
  if var.split('_')[-1] == 'OVERRIDE' and var not in ('SYSTEM_OVERRIDE', 'ENV_OVERRIDE', 'OVERRIDE'):
   orig_var = var.rsplit('_', 1)[0].replace('_', '.').lower()
   subprocess.Popen('echo "' + '##vso[task.setvariable variable='
                    + orig_var + ']'
                    + os.environ[var]
                    + '"',
                    shell=True, stdout=subprocess.PIPE)
 sys.exit(0)

proj = 'sample'
feed_name = 'sample'
apiuser = os.environ['APIUSER']
apipass = os.environ['APIPASS']

if 'TARGET' not in os.environ:
 target_environment = 'dev'
else:
 target_environment = os.environ['TARGET']

envdir = 'pipelines/vars/'
packages_info_file = envdir + 'packages_info.yaml'
environemnt_info_file = envdir + 'env/' + target_environment + '-env.yaml'
pipeline_env_file = envdir + 'pipeline.env'
jar_mapping_file = envdir + 'jar-mapping.yaml'
jar_config_dir = envdir + 'jars/'
jobs_config_dir = envdir + 'jobs/'

with open(packages_info_file, 'r') as packf:
 packages_data = yaml.safe_load(packf)

feed_data = requests.get('https://feeds.dev.azure.com/' +
                         proj +
                         '/_apis/packaging/Feeds/' +
                         feed_name +
                         '/packages?api-version=5.1-preview.1',
                         auth=(apiuser, apipass)).json()

# Fetch data from artifacts feed
for feed in feed_data['value']:
 for package in packages_data['packages']:
  if feed['normalizedName'] == package['name']:
   package['package_version'] = feed['versions'][0]['normalizedVersion']
   package['packageid'] = feed['id']

with open(packages_info_file, 'w') as packf:
 yaml.dump(packages_data, packf)
 packf.close()

with open(jar_mapping_file, 'r') as jarf:
 jar_mapping = yaml.safe_load(jarf)
 jarf.close()

# All all variables to envfile
with open(pipeline_env_file, 'w') as envfile:
 for item in packages_data['packages']:
  envfile.write('echo "' + '##vso[task.setvariable variable=' + item['name'].split(':')[1] + '.packageid]' + item['packageid'] + '"\n')
  envfile.write('echo "' + '##vso[task.setvariable variable=' + item['name'].split(':')[1] + '.package.version]' + item['package_version'] + '"\n')

 # Extract jar variables
 for jarfile in jar_mapping['jarfiles']:
  kind = jarfile['kind']
  with open(jar_config_dir + jarfile['jar_config_name'], 'r') as jarconfig_file:
   jarconfig_data = yaml.safe_load(jarconfig_file)
  jarconfig_file.close()

  for variable in jarconfig_data['variables']:
   envfile.write(
    'echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n')

  # Extract jobs variables
  for job in jarfile['jobs']:
   with open(jobs_config_dir + kind + '/' + job['job_config_name'], 'r') as jobconfig_file:
    jobconfig_data = yaml.safe_load(jobconfig_file)
   jobconfig_file.close()
   for variable in jobconfig_data['variables']:
    envfile.write(
     'echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n')

 with open(environemnt_info_file, 'r') as envf:
  environemnt_parameters = yaml.safe_load(envf)
  for variable in environemnt_parameters['variables']:
   envfile.write('echo "' + '##vso[task.setvariable variable=' + variable['name'] + ']' + variable['value'] + '"\n')

envfile.close()

# Copy configuration files to deployment dir

configuration_templates_dir = 'configuration/src/main/resources/'

for jarfile in jar_mapping['jarfiles']:
 kind = jarfile['kind']
 for job in jarfile['jobs']:
  os.popen('cp -r ' + configuration_templates_dir + kind + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
  os.popen('cp -r ' + configuration_templates_dir + kind + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
  # os.popen('cp ' + configuration_templates_dir + kind + '/' + job['job_jar_config_template_name'] + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
  # os.popen('cp ' + configuration_templates_dir + kind + '/' + job['job_jar_deployment_template_name'] + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
