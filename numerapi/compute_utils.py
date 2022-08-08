import boto3
import botocore.config
import json
import os
import tempfile
import urllib.request
import collections
import pathlib
import sys
import time
import zipfile


def maybe_create_bucket(aws_account_id):
    # use aws account id to create unique bucket name
    bucket_name = f'numerai-compute-{aws_account_id}'

    # create_bucket is idempotent, so it will create or return the existing bucket
    # if this step fails, an exception will be raised
    location = {'LocationConstraint': 'us-west-2'}
    try:
        boto3.client('s3').create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except Exception as ex:
        pass
    return bucket_name


def upload_to_s3(bucket_name, model_id, file_path):
    s3 = boto3.session.Session().client("s3")
    s3.upload_file(file_path, bucket_name, f'{model_id}/{file_path}')


def maybe_create_zip_file(model_id, bucket_name):
    # ideally we would only do this step if the requirements.txt changes. but until then
    # this will just run every time
    orig_dir = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:

            key = f"codebuild-container-{model_id}.zip"
            os.chdir(td)

            # TODO: need way to support user modified Dockerfile?

            # download dockerfile and buildspec from git
            dockerfile_url = 'https://raw.githubusercontent.com/numerai/compute-lite/master/Dockerfile'
            buildspec_url = 'https://raw.githubusercontent.com/numerai/compute-lite/master/buildspec.yml'
            entrysh_url = 'https://raw.githubusercontent.com/numerai/compute-lite/master/entry.sh'

            urllib.request.urlretrieve(dockerfile_url, 'Dockerfile')
            urllib.request.urlretrieve(buildspec_url, 'buildspec.yml')
            urllib.request.urlretrieve(entrysh_url, 'entry.sh')

            with tempfile.TemporaryFile() as tmp:
                with zipfile.ZipFile(tmp, "w") as zip:
                    for dirname, _, filelist in os.walk("."):
                        for file in filelist:
                            if file == 'Dockerfile' or file == 'buildspec.yml' or file == 'entry.sh':
                                zip.write(f"{dirname}/{file}")

                    # TODO: need to error loudly if any of these files arent found!

                    for dirname, _, filelist in os.walk(orig_dir):
                        for file in filelist:
                            if file == 'requirements.txt':
                                print('found requirements.txt')
                                zip.write(f"{dirname}/{file}", file)

                    for dirname, _, filelist in os.walk(pathlib.Path(__file__).parent.resolve()):
                        for file in filelist:
                            if file == 'lambda_handler.py':
                                print('found lambda_handler')
                                zip.write(f"{dirname}/{file}", file)
                tmp.seek(0)
                s3 = boto3.session.Session().client("s3")
                s3.upload_fileobj(tmp, bucket_name, key)
                print(f'Uploaded codebuild zip file: s3://{bucket_name}/{key}')
    finally:
        os.chdir(orig_dir)
    return key


def maybe_create_ecr_repo():
    repo_name = 'numerai-compute-lambda-image'

    client = boto3.client('ecr')
    try:
        ecr_resp = client.create_repository(
            repositoryName=repo_name
        )
        print('created repository')
    except Exception as ex:
        print(f'Repository already exists: {repo_name}. Retrieving..')
        ecr_resp = client.describe_repositories(repositoryNames=[repo_name])
        ecr_resp['repository'] = ecr_resp['repositories'][0]

    # TODO: would be nice to dataclass this response
    return ecr_resp['repository']


def maybe_create_codebuild_project(aws_account_id, bucket_name, zip_file_key, repo_name, model_id):
    role_name = 'codebuild-numerai-container-role'
    assume_role_policy_doc = '''{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "codebuild.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    '''
    description = 'Codebuild role created for Numerai Compute'
    codebuild_role = create_or_get_role(role_name, assume_role_policy_doc, description)

    cb_project_name = f"build-{repo_name}"

    policy_name = 'codebuild-numerai-container-policy'
    policy_document = f'''{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Action": [
                "codebuild:UpdateProjectVisibility",
                "codebuild:StopBuild",
                "ecr:DescribeImageReplicationStatus",
                "ecr:ListTagsForResource",
                "ecr:ListImages",
                "ecr:BatchGetRepositoryScanningConfiguration",
                "codebuild:RetryBuild",
                "codebuild:UpdateProject",
                "codebuild:StopBuildBatch",
                "codebuild:CreateReport",
                "logs:CreateLogStream",
                "codebuild:UpdateReport",
                "codebuild:BatchPutCodeCoverages",
                "ecr:TagResource",
                "ecr:DescribeRepositories",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetLifecyclePolicy",
                "codebuild:DeleteBuildBatch",
                "codebuild:RetryBuildBatch",
                "ecr:DescribeImageScanFindings",
                "ecr:GetLifecyclePolicyPreview",
                "ecr:GetDownloadUrlForLayer",
                "logs:CreateLogGroup",
                "logs:PutLogEvents",
                "codebuild:CreateProject",
                "s3:GetObject",
                "codebuild:CreateReportGroup",
                "ecr:UntagResource",
                "codebuild:StartBuildBatch",
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "codebuild:StartBuild",
                "codebuild:BatchPutTestCases",
                "s3:GetObjectVersion",
                "ecr:GetRepositoryPolicy",
                "ecr:GetAuthorizationToken",
                "ecr:CreateRepository"
            ],
            "Resource": [
                "arn:aws:s3:::numerai-compute-{aws_account_id}/codebuild-container-{model_id}.zip",
                "arn:aws:s3:::numerai-compute-{aws_account_id}/codebuild-container-{model_id}.zip/*",
                "arn:aws:ecr:us-west-2:{aws_account_id}:repository/*",
                "arn:aws:codebuild:us-west-2:{aws_account_id}:build/build-numerai-compute-lambda-image",
                "arn:aws:codebuild:us-west-2:{aws_account_id}:build/build-numerai-compute-lambda-image:*",
                "arn:aws:logs:us-west-2:{aws_account_id}:log-group:/aws/codebuild/{cb_project_name}",
                "arn:aws:logs:us-west-2:{aws_account_id}:log-group:/aws/codebuild/{cb_project_name}:*"
            ]
        }},
        {{
            "Effect": "Allow",
            "Resource": [
                "arn:aws:s3:::numerai-compute-{aws_account_id}"
            ],
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketAcl",
                "s3:GetBucketLocation"
            ]
        }},
        {{
            "Effect": "Allow",
            "Action": [
                "ecr:GetRegistryPolicy",
                "ecr:DescribeImageScanFindings",
                "ecr:GetLifecyclePolicyPreview",
                "ecr:GetDownloadUrlForLayer",
                "ecr:DescribeRegistry",
                "ecr:DescribePullThroughCacheRules",
                "ecr:DescribeImageReplicationStatus",
                "ecr:GetAuthorizationToken",
                "ecr:ListTagsForResource",
                "ecr:ListImages",
                "ecr:BatchGetRepositoryScanningConfiguration",
                "ecr:GetRegistryScanningConfiguration",
                "ecr:UntagResource",
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "ecr:TagResource",
                "ecr:DescribeRepositories",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetRepositoryPolicy",
                "ecr:GetLifecyclePolicy",
                "ecr:CreateRepository"
            ],
            "Resource": "arn:aws:ecr:us-west-2:{aws_account_id}:repository/*"
        }},
        {{
            "Effect": "Allow",
            "Action": [
                "ecr:*"
            ],
            "Resource": "*"
        }},
        {{
            "Effect": "Allow",
            "Action": [
                "lambda:*"
            ],
            "Resource": "*"
        }},
        {{
            "Effect": "Allow",
            "Action": [
                "sts:*"
            ],
            "Resource": "*"
        }}
    ]
}}
    '''
    maybe_create_policy_and_attach_role(policy_name, policy_document, aws_account_id, codebuild_role)

    session = boto3.session.Session()
    region = session.region_name
    client = session.client("codebuild")
    codebuild_zipfile = f'{bucket_name}/{zip_file_key}'

    base_image = 'public.ecr.aws/lambda/python:3.9'

    args = {
        "name": cb_project_name,
        "description": f"Build the container {repo_name} for running notebooks in SageMaker",
        "source": {"type": "S3", "location": codebuild_zipfile},
        "artifacts": {"type": "NO_ARTIFACTS"},
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:4.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "environmentVariables": [
                {"name": "AWS_DEFAULT_REGION", "value": region},
                {"name": "AWS_ACCOUNT_ID", "value": aws_account_id},
                {"name": "IMAGE_REPO_NAME", "value": repo_name},
                {"name": "IMAGE_TAG", "value": "latest"},
                {"name": "BASE_IMAGE", "value": base_image},
            ],
            "privilegedMode": True,
        },
        "serviceRole": codebuild_role['Arn'],
    }

    try:
        response = client.create_project(**args)
    except Exception as ex:
        print('Unable to create project, trying delete and recreate..')
        client.delete_project(name=cb_project_name)
        response = client.create_project(**args)
        print('Project recreated')

    return cb_project_name


def create_or_get_role(role_name, assume_role_policy_document, description):
    try:
        iam_response = boto3.client('iam').create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=assume_role_policy_document,
            Description=description,
        )
    except Exception as ex:
        print(f'Unable to create role {role_name}, trying to retrieve..')
        iam_response = boto3.client('iam').get_role(RoleName=role_name)

    # TODO: would be cool to dataclass this
    return iam_response['Role']


def maybe_create_policy_and_attach_role(policy_name, policy_document, aws_account_id, role):
    try:
        policy = boto3.client('iam').create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )
    except Exception as ex:
        print(f'Unable to create policy, deleting and recreating..')
        policy_arn = f'arn:aws:iam::{aws_account_id}:policy/{policy_name}'
        try:
            boto3.client('iam').detach_role_policy(
                RoleName=role['RoleName'],
                PolicyArn=policy_arn
            )
        except Exception as ex:
            print(f'Policy already detached. deleting..')

        # if policy has mutliple versions, you gotta delete those
        # before deleting the policy
        policy_versions = boto3.client('iam').list_policy_versions(
            PolicyArn=policy_arn
        )
        for pv in policy_versions['Versions']:
            if pv['IsDefaultVersion']:
                continue
            boto3.client('iam').delete_policy_version(
                PolicyArn=policy_arn,
                VersionId=pv['VersionId']
            )

        boto3.client('iam').delete_policy(
            PolicyArn=policy_arn
        )
        print(f'deleted {policy_arn}')
        policy = boto3.client('iam').create_policy(
            PolicyName=policy_name,
            PolicyDocument=policy_document
        )

    # attach role policy is idempotent, thx jeff
    boto3.client('iam').attach_role_policy(
        RoleName=role['RoleName'],
        PolicyArn=policy['Policy']['Arn']
    )
    return True


def maybe_build_container(cb_project_name, log=True):
    try:
        id = start_build(cb_project_name)
        if log:
            logs_for_build(id, wait=True)
        else:
            wait_for_build(id)
    except Exception as ex:
        raise ex


def maybe_create_secret(public_id, secret_key):
    client = boto3.client("secretsmanager")

    secret_name = 'numerai-api-keys'
    try:
        res = client.describe_secret(SecretId=secret_name)
    except Exception as ex:
        print('Secret not found. creating..')

        secret_dict = {'public_id': public_id, 'secret_key': secret_key}
        client.create_secret(
            Name='numerai-api-keys',
            SecretString=json.dumps(secret_dict)
        )


def start_build(cb_project_name):
    args = {"projectName": cb_project_name}
    session = boto3.session.Session()
    client = session.client("codebuild")

    response = client.start_build(**args)
    return response["build"]["id"]


def wait_for_build(id, poll_seconds=10):
    session = boto3.session.Session()
    client = session.client("codebuild")
    status = client.batch_get_builds(ids=[id])
    first = True
    while status["builds"][0]["buildStatus"] == "IN_PROGRESS":
        if not first:
            print(".", end="")
            sys.stdout.flush()
        first = False
        time.sleep(poll_seconds)
        status = client.batch_get_builds(ids=[id])
    print()
    print(f"Build complete, status = {status['builds'][0]['buildStatus']}")
    print(f"Logs at {status['builds'][0]['logs']['deepLink']}")


# Position is a tuple that includes the last read timestamp and the number of items that were read
# at that time. This is used to figure out which event to start with on the next read.
Position = collections.namedtuple("Position", ["timestamp", "skip"])


class LogState(object):
    STARTING = 1
    WAIT_IN_PROGRESS = 2
    TAILING = 3
    JOB_COMPLETE = 4
    COMPLETE = 5


def log_stream(client, log_group, stream_name, position):
    start_time, skip = position
    next_token = None

    event_count = 1
    while event_count > 0:
        if next_token is not None:
            token_arg = {"nextToken": next_token}
        else:
            token_arg = {}

        response = client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startTime=start_time,
            startFromHead=True,
            **token_arg,
        )
        next_token = response["nextForwardToken"]
        events = response["events"]
        event_count = len(events)
        if event_count > skip:
            events = events[skip:]
            skip = 0
        else:
            skip = skip - event_count
            events = []
        for ev in events:
            ts, count = position
            if ev["timestamp"] == ts:
                position = Position(timestamp=ts, skip=count + 1)
            else:
                position = Position(timestamp=ev["timestamp"], skip=1)
            yield ev, position


def logs_for_build(
        build_id, wait=False, poll=10, session=None
):  # noqa: C901 - suppress complexity warning for this method

    codebuild = boto3.client("codebuild")
    description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
    status = description["buildStatus"]

    log_group = description["logs"].get("groupName")
    stream_name = description["logs"].get("streamName")  # The list of log streams
    position = Position(
        timestamp=0, skip=0
    )  # The current position in each stream, map of stream name -> position

    # Increase retries allowed (from default of 4), as we don't want waiting for a build
    # to be interrupted by a transient exception.
    config = botocore.config.Config(retries={"max_attempts": 15})
    client = boto3.client("logs", config=config)

    job_already_completed = False if status == "IN_PROGRESS" else True

    state = (
        LogState.STARTING if wait and not job_already_completed else LogState.COMPLETE
    )
    dot = True

    while state == LogState.STARTING and log_group == None:
        time.sleep(poll)
        description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
        log_group = description["logs"].get("groupName")
        stream_name = description["logs"].get("streamName")

    if state == LogState.STARTING:
        state = LogState.TAILING

    # The loop below implements a state machine that alternates between checking the build status and
    # reading whatever is available in the logs at this point. Note, that if we were called with
    # wait == False, we never check the job status.
    #
    # If wait == TRUE and job is not completed, the initial state is STARTING
    # If wait == FALSE, the initial state is COMPLETE (doesn't matter if the job really is complete).
    #
    # The state table:
    #
    # STATE               ACTIONS                        CONDITION               NEW STATE
    # ----------------    ----------------               -------------------     ----------------
    # STARTING            Pause, Get Status              Valid LogStream Arn     TAILING
    #                                                    Else                    STARTING
    # TAILING             Read logs, Pause, Get status   Job complete            JOB_COMPLETE
    #                                                    Else                    TAILING
    # JOB_COMPLETE        Read logs, Pause               Any                     COMPLETE
    # COMPLETE            Read logs, Exit                                        N/A
    #
    # Notes:
    # - The JOB_COMPLETE state forces us to do an extra pause and read any items that got to Cloudwatch after
    #   the build was marked complete.
    last_describe_job_call = time.time()
    dot_printed = False
    while True:
        for event, position in log_stream(client, log_group, stream_name, position):
            print(event["message"].rstrip())
            if dot:
                dot = False
                if dot_printed:
                    print()
        if state == LogState.COMPLETE:
            break

        time.sleep(poll)
        if dot:
            print(".", end="")
            sys.stdout.flush()
            dot_printed = True
        if state == LogState.JOB_COMPLETE:
            state = LogState.COMPLETE
        elif time.time() - last_describe_job_call >= 30:
            description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
            status = description["buildStatus"]

            last_describe_job_call = time.time()

            status = description["buildStatus"]

            if status != "IN_PROGRESS":
                print()
                state = LogState.JOB_COMPLETE

    if wait:
        if dot:
            print()


def maybe_create_lambda_function(model_name, ecr, bucket_name, aws_account_id, model_id, external_id):
    lambda_role_name = 'numerai-compute-lambda-execution-role'

    assume_role_policy_document = f'''{{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Effect": "Allow",
                    "Principal": {{
                        "AWS": "arn:aws:iam::074996771758:root"
                    }},
                    "Action": "sts:AssumeRole",
                    "Condition": {{
                        "StringEquals": {{
                            "sts:ExternalId": "{external_id}"
                        }}
                    }}
                }},
                {{
                    "Effect": "Allow",
                    "Principal": {{
                        "Service": "lambda.amazonaws.com"
                    }},
                    "Action": "sts:AssumeRole"
                }}
            ]
        }}
    '''
    description = 'Lambda execution role created for Numerai Compute'
    lambda_role = create_or_get_role(lambda_role_name, assume_role_policy_document, description)

    cleaned_model_name = model_name.replace('_', '-')

    function_name = f'numerai-compute-{cleaned_model_name}-submit'

    lambda_policy_doc = f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "arn:aws:logs:us-west-2:{aws_account_id}:log-group:/aws/lambda/{function_name}:*"
                    }},
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "s3:*",
                            "logs:*"
                        ],
                        "Resource": [
                            "arn:aws:logs:us-west-2:{aws_account_id}:*",
                            "arn:aws:s3:::{bucket_name}",
                            "arn:aws:s3:::{bucket_name}/*"
                        ]
                    }},
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "lambda:*",
                            "secretsmanager:*"
                        ],
                        "Resource": "*"
                    }}
                ]
            }}
    '''
    lambda_policy_name = 'numerai-compute-lambda-execution-policy'
    maybe_create_policy_and_attach_role(lambda_policy_name, lambda_policy_doc, aws_account_id, lambda_role)

    client = boto3.client('lambda')

    repo_uri = ecr['repositoryUri']
    image_uri = f'{repo_uri}:latest'

    try:
        resp = client.create_function(
            FunctionName=function_name,
            PackageType='Image',
            Code={
                'ImageUri': image_uri
            },
            Role=lambda_role['Arn'],
            MemorySize=512,
            Timeout=300
        )
    except Exception as ex:
        print('Unable to create function, trying update to latest ECR image..')
        resp = client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri
        )
        print('Function updated')

    return lambda_role['Arn'], function_name
