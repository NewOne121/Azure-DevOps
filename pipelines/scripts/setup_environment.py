import requests
import subprocess
import yaml
import os
import sys
import argparse
import re

parser=argparse.ArgumentParser()
parser.add_argument('--override', action='store_true')
parser.add_argument('--validate', action='store_true')
parser.add_argument('--microservice', action='store_true')
parser.add_argument('--envconfig', action='store')
parser.add_argument('--project', action='store')
args=parser.parse_args()

proj = 'sample/sample_proj'
feed_name = 'sample'
apiuser = os.environ['APIUSER']
apipass = os.environ['APIPASS']
target_environment = os.environ['TARGET']
source_branches=''
repo_workdir='/sample'

if target_environment == 'dev':
 source_branches = ['develop', 'feature']
elif target_environment == 'stage':
 source_branches = 'qa'
elif target_environment == 'prod':
 source_branches = 'master'

branchpacks=[]

if args.project == 'sample1':
 envdir = repo_workdir + '/sample1/deployment/vars/'
 packages_info_file = envdir + 'packages_info.yaml'
 environment_info_file = envdir + 'env/' + target_environment +'-env.yaml'
 pipeline_env_file = envdir + 'pipeline.env'
 jar_mapping_file = envdir + "jar-mapping.yaml"
 jar_config_dir = envdir + 'jars/'
 jobs_config_dir = envdir + 'jobs/'
 common_vars_file = repo_workdir + '/sample1/pipelines/vars/common.yaml'
 configuration_templates_dir = repo_workdir + '/sample1/deployment/config/'
elif args.project == 'sample2':
 envdir = repo_workdir + '/sample2/deployment/vars/'
 packages_info_file = envdir + 'packages_info.yaml'
 environment_info_file = envdir + 'env/' + target_environment +'-env.yaml'
 pipeline_env_file = envdir + 'pipeline.env'
 jar_mapping_file = envdir + "jar-mapping.yaml"
 jar_config_dir = envdir + 'jars/'
 jobs_config_dir = envdir + 'jobs/'
 common_vars_file = repo_workdir + '/sample2/pipelines/vars/common.yaml'
 configuration_templates_dir = repo_workdir + '/sample2/deployment/config/'
else:
 envdir = 'pipelines/vars/'
 packages_info_file = envdir + 'packages_info.yaml'
 environment_info_file = envdir + 'env/' + target_environment +'-env.yaml'
 pipeline_env_file = envdir + 'pipeline.env'
 jar_mapping_file = envdir + "jar-mapping.yaml"
 jar_config_dir = envdir + 'jars/'
 jobs_config_dir = envdir + 'jobs/'
 common_vars_file = envdir + 'common.yaml'
 configuration_templates_dir = repo_workdir + 'configuration/src/main/resources/'

if args.microservice is not True and args.override is not True and args.validate is not True:
 with open(packages_info_file, 'r') as packf:
  packages_data = yaml.load(packf, Loader=yaml.Loader)

 feed_data = requests.get('https://feeds.dev.azure.com/' +
                          proj +
                          '/_apis/packaging/Feeds/' +
                          feed_name +
                          '/packages?api-version=5.1-preview.1',
                          auth=(apiuser, apipass)).json()

#Fetch data from artifacts feed
#exclude common packages
 common_packages=[
                  'sample.common:deployment',
                  'sample.common:applications',
                  'sample:configuration',
                  'common:logging'
                  ]

 for feed in feed_data['value']:
  for package in packages_data['packages']:
   if feed['normalizedName'] == package['name']:
    package['packageid'] = feed['id']
    if package['name'] not in common_packages:
     package_versions_metadata=requests.get('https://feeds.dev.azure.com/' +
                                            proj +
                                            '/_apis/packaging/Feeds/' +
                                            feed_name +
                                            '/packages/' +
                                            feed['id'] +
                                            '/versions?api-version=5.1-preview.1',
                                            auth=(apiuser, apipass)).json()
     for packv in package_versions_metadata['value']:
      try:
       if packv['version'].split('-')[-1] in source_branches:
        if 'isDeleted' not in packv:
         branchpacks.append(packv['version'])
      except IndexError:
       continue
     try:
      package['package_version'] = sorted(branchpacks)[-1].lower()
     except IndexError:
      print("No artifacts were found for package: " + package['name'] + " for " + target_environment + " environment!")
      continue
    elif package['name'] in common_packages:
     package['package_version'] = feed['versions'][0]['normalizedVersion'].lower()
    branchpacks=[]

if args.override is True:
 for var in os.environ:
  if var.split('_')[-1] == 'OVERRIDE' and var not in ('SYSTEM_OVERRIDE', 'ENV_OVERRIDE', 'OVERRIDE'):
   print(var)
   orig_var=var.rsplit('_', 1)[0].replace('_','.').lower()
   print(orig_var)
   print(os.environ[var])
   cmd_exec = subprocess.Popen('echo "' + '##vso[task.setvariable variable='
                                 + orig_var + ']'
                                 + os.environ[var].lower()
                                 + '"',
                                 shell=True, stdout=subprocess.PIPE, bufsize=0)
   subprocess_return = cmd_exec.stdout.read()
   print(subprocess_return)
   cmd_exec.wait()

if args.validate:
 findpackvars=re.compile('.*package_deploy.*', flags=re.IGNORECASE)
 deploy_packs=[]

 for item, value in os.environ.items():
  if findpackvars.match(item) and value == "true":
   deploy_packs.append(re.split('_package_deploy', item, flags=re.IGNORECASE)[0])

 for item, value in os.environ.items():
  for package in deploy_packs:
   if item == (package + '_PACKAGE_VERSION') and package != "APPLICATIONS":
    if value.split('-')[-1] not in source_branches:
     print("This version of package can't be deployed to this environment, exiting.")
     sys.exit(1)

if args.override:
 sys.exit(0)

if args.microservice is not True and args.validate is not True:
 with open(packages_info_file, 'w') as packf:
  yaml.dump(packages_data, packf)
  packf.close()

 with open(jar_mapping_file, 'r') as jarf:
  jar_mapping = yaml.safe_load(jarf)
  jarf.close()

#All all variables to envfile
 with open(pipeline_env_file, 'w') as envfile:
  for item in packages_data['packages']:
   envfile.write('echo "' +'##vso[task.setvariable variable=' + item['name'].split(':')[1] + '.packageid]' + item['packageid'] + '"\n')
   envfile.write('echo "' + '##vso[task.setvariable variable=' + item['name'].split(':')[1] + '.package.version]' + item['package_version'] + '"\n')

  #Extract jar variables
  for jarfile in jar_mapping['jarfiles']:
   kind = jarfile['kind']
   with open(jar_config_dir + jarfile['jar_config_name'], 'r') as jarconfig_file:
    jarconfig_data = yaml.safe_load(jarconfig_file)
   jarconfig_file.close()

   for variable in jarconfig_data['variables']:
    envfile.write('echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n' )

   #Extract jobs variables
   for job in jarfile['jobs']:
    with open(jobs_config_dir + kind + '/' + job['job_config_name'], 'r') as jobconfig_file:
     jobconfig_data = yaml.safe_load(jobconfig_file)
    jobconfig_file.close()
    for variable in jobconfig_data['variables']:
     envfile.write('echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n' )


  with open(environment_info_file, 'r') as envf:
   environemnt_parameters = yaml.safe_load(envf)
   for variable in environemnt_parameters['variables']:
    envfile.write('echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n' )

  with open(common_vars_file, 'r') as commonenvf:
   common_environemnt_parameters = yaml.safe_load(commonenvf)
   for variable in common_environemnt_parameters['variables']:
    envfile.write('echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n' )

 envfile.close()

# Copy configuration files to deployment dir

 for jarfile in jar_mapping['jarfiles']:
  kind = jarfile['kind']
  for job in jarfile['jobs']:
   sub_kind = job.get('kind')
   if sub_kind:
    os.popen('cp -r ' + configuration_templates_dir + kind + "/" + sub_kind + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
    print('Files with subkind copied to: ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
   else:
    os.popen('cp -r ' + configuration_templates_dir + kind + ' ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')
    print('Files without subkind copied to: ' + os.getenv('AGENT_WORKFOLDER') + '/_temp')

if args.microservice is True:
 print('args.microservice is TRUE')
 msvardir='configuration/k8s/microservices/vars/'
 msconfig_path=msvardir + args.envconfig
 with open(pipeline_env_file, 'w') as envfile:
  with open(msconfig_path, 'r') as msconf:
   msenv = yaml.safe_load(msconf)
   for variable in msenv['variables']:
    envfile.write('echo "' + '##vso[task.setvariable variable=' + str(variable['name']) + ']' + str(variable['value']) + '"\n' )

 envfile.close()