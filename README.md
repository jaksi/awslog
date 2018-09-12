# awslog

Show the history and changes between configuration versions of AWS resources

Uses AWS Config to fetch the configuration history of resources, only works on [resources supported by AWS Config](https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html).

# Installation

`pip install awslog`

# Usage

Make sure your [AWS credentials are properly configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).
You can test it using the AWS CLI by issuing `aws sts get-caller-identity`. It should report information about your current CLI session and not raise any errors.

Make sure [AWS Config](https://aws.amazon.com/config/) is set up to record configuration changes of your resources.

## CLI

```
usage: awslog [-h] [--type TYPE] [--number NUMBER] [--before BEFORE]
              [--after AFTER] [--deleted] [--context CONTEXT]
              name

positional arguments:
  name                  name or ID of the resource to query

optional arguments:
  -h, --help            show this help message and exit
  --type TYPE, -t TYPE  the type of the resource to query list of supported
                        resource types: https://docs.aws.amazon.com/config/lat
                        est/developerguide/resource-config-reference.html
  --number NUMBER, -n NUMBER
                        number of history items to show
  --before BEFORE, -b BEFORE
                        show changes more recent than the specified date and
                        time
  --after AFTER, -a AFTER
                        show changes older than the specified date and time
  --deleted, -d         include deleted resources
  --context CONTEXT, -c CONTEXT
                        number of context lines in the diffs
```

Examples:
```shellsession
$ awslog sg-12345678
--- arn:aws:ec2:us-east-1:123456789012:security-group/sg-12345678/configuration	2018-05-16 11:19:12
+++ arn:aws:ec2:us-east-1:123456789012:security-group/sg-12345678/configuration	2018-05-16 21:48:48
@@ -36,35 +36,25 @@
     {
       "fromPort": 1234,
       "ipProtocol": "tcp",
       "ipRanges": [],
       "ipv4Ranges": [],
       "ipv6Ranges": [],
       "prefixListIds": [],
       "toPort": 1234,
       "userIdGroupPairs": [
         {
-          "description": "my fancy security group",
-          "groupId": "sg-9abcdef0",
-          "userId": 123456789012
-        },
-        {
           "groupId": "sg-fedcba98",
           "userId": 123456789012
         },
         {
           "groupId": "sg-76543210",
-          "userId": 123456789012
-        },
-        {
-          "description": "the best security group",
-          "groupId": "sg-13579bdf",
           "userId": 123456789012
         }
       ]
     }
   ],
   "ipPermissionsEgress": [
     {
       "ipProtocol": -1,
       "ipRanges": [
         "0.0.0.0/0"
```

```shellsession
$ awslog --type AWS::DynamoDB::Table \
>        --number 2 \
>        --before '10 days ago' \
>        --after 2016-01-01 \
>        --deleted \
>        --context 1 \
>        some-random-table-name
--- arn:aws:dynamodb:us-east-1:123456789012:table/some-random-table-name/configuration	2017-08-31 13:39:51
+++ arn:aws:dynamodb:us-east-1:123456789012:table/some-random-table-name/configuration	2018-01-23 01:39:41
@@ -21,2 +21,3 @@
   "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/some-random-table-name",
+  "tableId": "some-random-uuid",
   "tableName": "some-random-table-name",

--- arn:aws:dynamodb:us-east-1:123456789012:table/some-random-table-name/configuration	2017-08-30 13:39:52
+++ arn:aws:dynamodb:us-east-1:123456789012:table/some-random-table-name/configuration	2017-08-31 13:39:51
@@ -8,3 +8,2 @@
   "creationDateTime": some-unix-timestamp,
-  "itemCount": 1234,
   "keySchema": [
@@ -23,3 +22,2 @@
   "tableName": "some-random-table-name",
-  "tableSizeBytes": 123456,
   "tableStatus": "ACTIVE"
```

## Python module

```python console
>>> import boto3
>>> import awslog
>>> config = boto3.client('config')
>>> after, before = list(awslog.get_config_history(config, 'AWS::EC2::SecurityGroup', 'sg-12345678'))
>>> print('\n'.join(awslog.create_diff(after, before)))
```

```
--- arn:aws:ec2:us-east-1:123456789012:security-group/sg-12345678/configuration	2018-05-16 11:19:12
+++ arn:aws:ec2:us-east-1:123456789012:security-group/sg-12345678/configuration	2018-05-16 21:48:48
@@ -36,35 +36,25 @@
     {
       "fromPort": 1234,
       "ipProtocol": "tcp",
       "ipRanges": [],
       "ipv4Ranges": [],
       "ipv6Ranges": [],
       "prefixListIds": [],
       "toPort": 1234,
       "userIdGroupPairs": [
         {
-          "description": "my fancy security group",
-          "groupId": "sg-9abcdef0",
-          "userId": 123456789012
-        },
-        {
           "groupId": "sg-fedcba98",
           "userId": 123456789012
         },
         {
           "groupId": "sg-76543210",
-          "userId": 123456789012
-        },
-        {
-          "description": "the best security group",
-          "groupId": "sg-13579bdf",
           "userId": 123456789012
         }
       ]
     }
   ],
   "ipPermissionsEgress": [
     {
       "ipProtocol": -1,
       "ipRanges": [
         "0.0.0.0/0"
```
