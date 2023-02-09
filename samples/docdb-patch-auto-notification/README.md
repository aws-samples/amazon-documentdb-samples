# DocumentDB Patch Auto Notification
**Automatically query available DocumentDB Patch**
## Architecture Diagram：

<img width="422" alt="image" src="images/architecture_diagram.png">

## Create an IAM Policy for Lambda
**Policy name: query-pending-maintenance**

**Policy  Json definition：**

**Please refer to Policy Json defefinition from the file deploy/policy.json**
## Create Role for Lambda
**Role Name: lambda-query-maintenance**

**Policy: query-pending-maintenance**
## Configure SNS service
1. **Create sns topic**

**docdb-patch-notification**

<img width="422" alt="image" src="images/create_sns_topic.png">

2. **Create topic subscription**
<img width="422" alt="image" src="images/create_topic_subscription.png">


<img width="422" alt="image" src="images/create_topic_subscription_detail.png">

3. **Confirm subscription in the email：**

<img width="468" alt="image" src="images/confirm_subscription.png">


## Create Lambda
**Lambda Configuration：**

**Lambda name:** 
**query_docdb_maintenance**

**Lambda role:** 
**lambda-query-maintenance**

**Lambda Timeout:  7 Minutes（Change default timeout:  from 3 seconds to 7 minutes）：**

<img width="422" alt="image" src="images/set_lambda_timeout.png">

**Lambda Runtime: Python 3.7**

**Lambda Code:**

**Please refer to Lambda Python Code from the file deploy/lamda.py**

**Change the python code：TargetArn = "arn:aws:sns:us-east-1:02818***:docdb-patch-notification" 
**change Account id to your Account id)**

## Create event bridge
1. **Create event rule:**

**Rule_name: docdb-patch-notification_rule**

**Rule type: schedule**

<img width="422" alt="image" src="images/create_event_rules.png">

2.	**Create event schedule:**

**Schedule_name: docdb-patch-notification-schedule (executed once a day)**

<img width="422" alt="image" src="images/create_events_schedule.png">

**Schedule Targe: Select the created Lambda function (invoke)**

<img width="422" alt="image" src="images/schedule_target_lambda.png">

**Create successfully：**

**Once create successfully, the lambda function would be executed, then executed once a day**

## Email Notification Example：

<img width="422" alt="image" src="images/email_notification_example.png">

