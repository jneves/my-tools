#! /usr/bin/env python

import boto3
from configparser import ConfigParser
import logging
import sys
from multiprocessing import Pool


log = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
log.addHandler(ch)


def validate_deploy_service(region, cluster, service):
    client = boto3.client('ecs', region_name=region)

    response = client.describe_services(
        cluster=cluster,
        services=[
            service,
        ]
    )

    task_definition = response['services'][0]['taskDefinition']

    response = client.list_tasks(
        cluster=cluster,
        serviceName=service,
    )

    if not response['taskArns']:
        log.error('No tasks for service {}.'.format(service))
        return False

    response = client.describe_tasks(
        cluster=cluster,
        tasks=response['taskArns']
    )

    for task in response['tasks']:
        if task['taskDefinitionArn'] != task_definition:
            log.error('Old task definition {} in place when {} expected for task {}.'.format(task['taskDefinitionArn'], task_definition, task['taskArn']))
            return False
        if task['desiredStatus'] != task['lastStatus']:
            log.error('Status {} found when expected {} for task {}.'.format(task['desiredStatus'], task['lastStatus'], task['taskArn']))
            return False

    return True


def validate_deploy(region, cluster, services):
    for service in services:
        if not validate_deploy_service(region, cluster, service):
            return False
    return True

if __name__ == '__main__':
    config = ConfigParser()
    config.read('config.ini')

    if len(sys.argv) == 2 and sys.argv[1] == '--wait':
        failed = True
        while failed:
            failed = False
            for cluster in config.sections():
                conf = config[cluster]
                
                services = map(lambda x: x.strip(), conf['services'].split(','))
                if not validate_deploy(conf['region'], conf['cluster'], services):
                    print('Failed {}.'.format(cluster))
                    failed = True
    else:
        failed = False
        for cluster in config.sections():
            conf = config[cluster]
                
            services = map(lambda x: x.strip(), conf['services'].split(','))
            if not validate_deploy(conf['region'], conf['cluster'], services):
                print('Failed {}.'.format(cluster))
                failed = True

        if failed:
            sys.exit(1)
