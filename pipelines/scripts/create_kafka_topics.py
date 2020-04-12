import os
import kafka
import yaml
from kafka.admin import KafkaAdminClient, NewTopic, NewPartitions

topic_list = []
kafka_bootstrap = os.environ['KAFKA_BOOTSTRAP_SERVERS']

print(kafka_bootstrap)

admin_client = KafkaAdminClient(bootstrap_servers=kafka_bootstrap,
                                client_id='AzureDevOps')

client = kafka.KafkaClient(bootstrap_servers=kafka_bootstrap)
update = client.cluster.request_update()
client.poll(future=update)
metadata = client.cluster

with open('configuration/kafka_topics.yaml', 'r') as topicsdata:
 topics_params = yaml.safe_load(topicsdata)
topicsdata.close()

for topic in topics_params['topics']:
 if topic['name'] not in metadata.topics():
  print('Topic ' + topic['name'] + ' will be created')
  topic_list.append(NewTopic(name=topic['name'],
                             num_partitions=topic['partitions'],
                             replication_factor=topic['replication-factor'])
                    )

 if topic['name'] in metadata.topics():
  if len(metadata.partitions_for_topic(topic['name'])) < topic['partitions']:
   print('New partitions for topic: ' + topic['name'] + ' will be created')
   num_partitions=NewPartitions(topic['partitions'])
   new_partitions={topic['name']: num_partitions}
   admin_client.create_partitions(new_partitions)
   print('Additional partitions created for topic: ' + topic['name'])

if topic_list:
 admin_client.create_topics(new_topics=topic_list, validate_only=False)
 print('Topics successfully created')
else:
 print('No topics to create')
