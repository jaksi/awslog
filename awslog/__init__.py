from __future__ import print_function, unicode_literals

import json
from argparse import ArgumentParser
from difflib import unified_diff

import boto3
import dateparser
from six import string_types
from six.moves.urllib.parse import unquote as urlunquote


def main():
    config = boto3.client('config')

    parser = ArgumentParser()
    parser.add_argument('type', choices=[
        'EC2::CustomerGateway',
        'EC2::EIP',
        'EC2::Host',
        'EC2::Instance',
        'EC2::InternetGateway',
        'EC2::NetworkAcl',
        'EC2::NetworkInterface',
        'EC2::RouteTable',
        'EC2::SecurityGroup',
        'EC2::Subnet',
        'CloudTrail::Trail',
        'EC2::Volume',
        'EC2::VPC',
        'EC2::VPNConnection',
        'EC2::VPNGateway',
        'IAM::Group',
        'IAM::Policy',
        'IAM::Role',
        'IAM::User',
        'ACM::Certificate',
        'RDS::DBInstance',
        'RDS::DBSubnetGroup',
        'RDS::DBSecurityGroup',
        'RDS::DBSnapshot',
        'RDS::EventSubscription',
        'ElasticLoadBalancingV2::LoadBalancer',
        'S3::Bucket',
        'SSM::ManagedInstanceInventory',
        'Redshift::Cluster',
        'Redshift::ClusterSnapshot',
        'Redshift::ClusterParameterGroup',
        'Redshift::ClusterSecurityGroup',
        'Redshift::ClusterSubnetGroup',
        'Redshift::EventSubscription',
        'CloudWatch::Alarm',
        'CloudFormation::Stack',
        'DynamoDB::Table',
        'AutoScaling::AutoScalingGroup',
        'AutoScaling::LaunchConfiguration',
        'AutoScaling::ScalingPolicy',
        'AutoScaling::ScheduledAction',
        'CodeBuild::Project',
        'WAF::RateBasedRule',
        'WAF::Rule',
        'WAF::WebACL',
        'WAFRegional::RateBasedRule',
        'WAFRegional::Rule',
        'WAFRegional::WebACL',
        'CloudFront::Distribution',
        'CloudFront::StreamingDistribution',
        'WAF::RuleGroup',
        'WAFRegional::RuleGroup',
        'Lambda::Function',
        'ElasticBeanstalk::Application',
        'ElasticBeanstalk::ApplicationVersion',
        'ElasticBeanstalk::Environment',
        'ElasticLoadBalancing::LoadBalancer',
        'XRay::EncryptionConfig',
    ])
    parser.add_argument('name')
    parser.add_argument('--number', '-n', type=int, default=1)
    parser.add_argument('--before', '-b')
    parser.add_argument('--after', '-a')
    parser.add_argument('--deleted', '-d', action='store_true')
    parser.add_argument('--context', '-c', type=int, default=10)
    args = parser.parse_args()
    if args.before:
        before = dateparser.parse(args.before, settings={'TO_TIMEZONE': 'UTC'})
    else:
        before = None
    if args.after:
        after = dateparser.parse(args.after)
    else:
        after = None

    history = list(get_config_history(config, 'AWS::{}'.format(args.type), args.name,
                                      limit=args.number + 1, before=before, after=after))
    for i in range(len(history) - 1):
        old, new = history[i + 1], history[i]
        print('\n'.join(create_diff(new, old, args.context)))
        print()


def create_diff(new, old, context=10):
    for diff in unified_diff(json.dumps(old['configuration'], indent=2).splitlines(),
                             json.dumps(new['configuration'], indent=2).splitlines(),
                             fromfile=old['arn'], tofile=new['arn'],
                             fromfiledate=old['time'].strftime("%Y-%m-%d %H:%M:%S"),
                             tofiledate=new['time'].strftime("%Y-%m-%d %H:%M:%S"),
                             n=context, lineterm=''):
        yield diff


def get_resource_ids(config_client, resource_type, resource_name, limit=1, include_deleted=False):
    paginator = config_client.get_paginator('list_discovered_resources')
    pages = paginator.paginate(
        resourceType=resource_type,
        resourceName=resource_name,
        includeDeletedResources=include_deleted,
        PaginationConfig={'MaxItems': limit},
    )
    for page in pages:
        if not page.get('resourceIdentifiers'):
            break

        for resource in page['resourceIdentifiers']:
            yield resource['resourceId']


def prettify(value):
    if isinstance(value, list):
        pretty_list = [prettify(i) for i in value]
        try:
            return sorted(pretty_list)
        except TypeError:
            return pretty_list

    if isinstance(value, dict):
        return {k: prettify(v) for k, v in sorted(value.items())}

    if isinstance(value, string_types):
        if value.startswith('%7B'):  # URL encoded {
            decoded_value = urlunquote(value)
        else:
            decoded_value = value

        try:
            json_value = json.loads(decoded_value)
        except ValueError:
            return value
        else:
            return prettify(json_value)

    return value


def get_config_history(config_client, resource_type, resource_name_or_id, **kwargs):
    limit = kwargs.pop('limit', 2)
    include_deleted = kwargs.pop('include_deleted', False)
    before = kwargs.pop('before', None)
    after = kwargs.pop('after', None)

    resource_ids = list(get_resource_ids(config_client,
                                         resource_type,
                                         resource_name_or_id,
                                         limit=2,
                                         include_deleted=include_deleted))
    if len(resource_ids) > 1:
        raise ValueError("Multiple resources found for {} with type {}".format(resource_name_or_id, resource_type))
    if not resource_ids:
        resource_id = resource_name_or_id
    else:
        resource_id = resource_ids[0]

    paginator = config_client.get_paginator('get_resource_config_history')

    arguments = {
        'resourceType': resource_type,
        'resourceId': resource_id,
        'PaginationConfig': {'MaxItems': limit},
    }
    if after:
        arguments['earlierTime'] = after
    if before:
        arguments['laterTime'] = before

    pages = paginator.paginate(**arguments)
    for page in pages:
        if not page.get('configurationItems'):
            break

        for result in page['configurationItems']:
            yield {'time': result['configurationItemCaptureTime'],
                   'arn': result['arn'],
                   'configuration': prettify(result['configuration'])}


if __name__ == '__main__':
    main()
