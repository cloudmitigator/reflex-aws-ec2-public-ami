""" Module for Ec2PublicAmi """

import json

import boto3

from reflex_core import AWSRule, subscription_confirmation


class Ec2PublicAmi(AWSRule):
    """ AWS rule for ensuring non-public AMIs """

    client = boto3.client("ec2")

    def __init__(self, event):
        super().__init__(event)

    def extract_event_data(self, event):
        """ Extract required data from the CloudWatch event """
        self.raw_event = event
        self.ami_image_id = event["detail"]["requestParameters"]["imageId"]

    def resource_compliant(self):
        is_compliant = True
        response = self.client.describe_image_attribute(
            Attribute="launchPermission", ImageId=self.ami_image_id
        )

        for permission in response["LaunchPermissions"]:
            try:
                if permission["Group"] == "all":
                    is_compliant = False
            except KeyError:
                continue

        return is_compliant

    def remediate(self):
        self.client.modify_image_attribute(
            Attribute="launchPermission",
            ImageId=self.ami_image_id,
            LaunchPermission={"Remove": [{"Group": "all"}]},
        )

    def get_remediation_message(self):
        """ Returns a message about the remediation action that occurred """
        message = f"The AMI with ID: {self.ami_image_id} was made public. "
        if self.should_remediate():
            message += "Public access has been disabled."

        return message


def lambda_handler(event, _):
    """ Handles the incoming event """
    print(event)
    event_payload = json.loads(event["Records"][0]["body"])
    if subscription_confirmation.is_subscription_confirmation(event_payload):
        subscription_confirmation.confirm_subscription(event_payload)
        return
    rule = Ec2PublicAmi(event_payload)
    rule.run_compliance_rule()
