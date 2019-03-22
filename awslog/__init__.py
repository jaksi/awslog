from __future__ import print_function, unicode_literals

import json
import re
from argparse import ArgumentParser
from difflib import unified_diff

import boto3
import crayons
import dateparser
from six import string_types
from six.moves.urllib.parse import unquote as urlunquote


SUPPORTED_RESOURCE_TYPES = [
    'AWS::ACM::Certificate',
    'AWS::AutoScaling::AutoScalingGroup',
    'AWS::AutoScaling::LaunchConfiguration',
    'AWS::AutoScaling::ScalingPolicy',
    'AWS::AutoScaling::ScheduledAction',
    'AWS::CloudFormation::Stack',
    'AWS::CloudFront::Distribution',
    'AWS::CloudFront::StreamingDistribution',
    'AWS::CloudTrail::Trail',
    'AWS::CloudWatch::Alarm',
    'AWS::CodeBuild::Project',
    'AWS::DynamoDB::Table',
    'AWS::EC2::CustomerGateway',
    'AWS::EC2::EIP',
    'AWS::EC2::Host',
    'AWS::EC2::Instance',
    'AWS::EC2::InternetGateway',
    'AWS::EC2::NetworkAcl',
    'AWS::EC2::NetworkInterface',
    'AWS::EC2::RouteTable',
    'AWS::EC2::SecurityGroup',
    'AWS::EC2::Subnet',
    'AWS::EC2::VPC',
    'AWS::EC2::VPNConnection',
    'AWS::EC2::VPNGateway',
    'AWS::EC2::Volume',
    'AWS::ElasticBeanstalk::Application',
    'AWS::ElasticBeanstalk::ApplicationVersion',
    'AWS::ElasticBeanstalk::Environment',
    'AWS::ElasticLoadBalancing::LoadBalancer',
    'AWS::ElasticLoadBalancingV2::LoadBalancer',
    'AWS::IAM::Group',
    'AWS::IAM::Policy',
    'AWS::IAM::Role',
    'AWS::IAM::User',
    'AWS::Lambda::Function',
    'AWS::RDS::DBInstance',
    'AWS::RDS::DBSecurityGroup',
    'AWS::RDS::DBSnapshot',
    'AWS::RDS::DBSubnetGroup',
    'AWS::RDS::EventSubscription',
    'AWS::Redshift::Cluster',
    'AWS::Redshift::ClusterParameterGroup',
    'AWS::Redshift::ClusterSecurityGroup',
    'AWS::Redshift::ClusterSnapshot',
    'AWS::Redshift::ClusterSubnetGroup',
    'AWS::Redshift::EventSubscription',
    'AWS::S3::Bucket',
    'AWS::SSM::ManagedInstanceInventory',
    'AWS::WAF::RateBasedRule',
    'AWS::WAF::Rule',
    'AWS::WAF::RuleGroup',
    'AWS::WAF::WebACL',
    'AWS::WAFRegional::RateBasedRule',
    'AWS::WAFRegional::Rule',
    'AWS::WAFRegional::RuleGroup',
    'AWS::WAFRegional::WebACL',
    'AWS::XRay::EncryptionConfig',
]

RESOURCE_TYPE_PATTERNS = {
    re.compile('i-'): 'AWS::EC2::Instance',
    re.compile('eni-'): 'AWS::EC2::NetworkInterface',
    re.compile('sg-'): 'AWS::EC2::SecurityGroup',
    re.compile('vol-'): 'AWS::EC2::Volume',
    re.compile('igw-'): 'AWS::EC2::InternetGateway',
    re.compile('acl-'): 'AWS::EC2::NetworkAcl',
    re.compile('rtb-'): 'AWS::EC2::RouteTable',
    re.compile('subnet-'): 'AWS::EC2::Subnet',
    re.compile('vpc-'): 'AWS::EC2::VPC',
    re.compile('vgw-'): 'AWS::EC2::VPNGateway',
    re.compile('e-'): 'AWS::ElasticBeanstalk::Environment',
    re.compile('db-'): 'AWS::RDS::DBInstance',
}


def main():
    config = boto3.client('config')

    parser = ArgumentParser()
    parser.add_argument('name', help="name or ID of the resource to query")
    parser.add_argument('--type', '-t', help=(
        "the type of the resource to query\n"
        "list of supported resource types: "
        "https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html"
    ))
    parser.add_argument('--number', '-n', type=int, default=1, help="number of history items to show")
    parser.add_argument('--before', '-b', help="show changes more recent than the specified date and time")
    parser.add_argument('--after', '-a', help="show changes older than the specified date and time")
    parser.add_argument('--deleted', '-d', action='store_true', help="include deleted resources")
    parser.add_argument('--context', '-c', type=int, default=10, help="number of context lines in the diffs")
    parser.add_argument('--no-color', '-o', action='store_true', help="disable colored output")
    args = parser.parse_args()
    resource_type = None
    if args.type:
        resource_type = args.type
    else:
        for pattern, matching_type in RESOURCE_TYPE_PATTERNS.items():
            if pattern.match(args.name):
                resource_type = matching_type
                break

    if not resource_type:
        raise ValueError("No type selected and the name {} could not be used to infer one".format(args.name))
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise ValueError("{} isn't a supported resource type.".format(resource_type))
    if args.before:
        before = dateparser.parse(args.before, settings={'TO_TIMEZONE': 'UTC'})
    else:
        before = None
    if args.after:
        after = dateparser.parse(args.after)
    else:
        after = None

    history = list(get_config_history(config, resource_type, args.name,
                                      limit=args.number + 1, before=before, after=after,
                                      include_deleted=args.deleted))
    for i in range(len(history) - 1):
        old, new = history[i + 1], history[i]
        print('\n'.join(create_diff(new, old, args.context, not args.no_color)))
        print()


def colordiff(a, b, fromfile='', tofile='', fromfiledate='', tofiledate='', n=3, lineterm='\n'):
    for i, diff in enumerate(unified_diff(a, b, fromfile, tofile, fromfiledate, tofiledate, n, lineterm)):
        if i < 2:
            yield str(crayons.white(diff, bold=True))
        elif diff.startswith("@"):
            yield str(crayons.blue(diff))
        elif diff.startswith("+"):
            yield str(crayons.green(diff))
        elif diff.startswith("-"):
            yield str(crayons.red(diff))
        else:
            yield diff


def create_diff(new, old, context=10, color=False):
    if not color:
        crayons.disable()

    fromfiledate = old['time'].strftime("%Y-%m-%d %H:%M:%S")
    tofiledate = new['time'].strftime("%Y-%m-%d %H:%M:%S")

    for diff in colordiff(json.dumps(old['configuration'], indent=2).splitlines(),
                          json.dumps(new['configuration'], indent=2).splitlines(),
                          fromfile='{}/configuration'.format(old['arn']),
                          tofile='{}/configuration'.format(new['arn']),
                          fromfiledate=fromfiledate,
                          tofiledate=tofiledate,
                          n=context, lineterm=''):
        yield diff

    for diff in colordiff(json.dumps(old['relationships'], indent=2).splitlines(),
                          json.dumps(new['relationships'], indent=2).splitlines(),
                          fromfile='{}/relationships'.format(old['arn']),
                          tofile='{}/relationships'.format(new['arn']),
                          fromfiledate=fromfiledate,
                          tofiledate=tofiledate,
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
        return [prettify(i) for i in value]

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
                   'configuration': prettify(result['configuration']),
                   'relationships': result['relationships']}


if __name__ == '__main__':
    main()
