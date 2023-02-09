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


<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217127664-effd86cb-2d86-44a7-8914-57159a5715e1.png">

3. **Confirm subscription in the email：**

<img width="468" alt="image" src="https://user-images.githubusercontent.com/50776512/217141783-97d1714f-8d86-4480-8bb4-1133065893c6.png">


## Create Lambda
**Lambda Configuration：**

**Lambda name:** 
**query_docdb_maintenance**

**Lambda role:** 
**lambda-query-maintenance**

**Lambda Timeout:  7 Minutes（Change default timeout:  from 3 seconds to 7 minutes）：**

<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217133071-05cf3be8-4b3b-4aba-a33f-ecbb509c98c3.png">

**Lambda Runtime: Python 3.7**

**Lambda Code:**

**Please refer to Lambda Python Code from the file deploy/lamda.py**

**Change the python code：TargetArn = "arn:aws:sns:us-east-1:02818***:docdb-patch-notification" 
**change Account id to your Account id)**

## Create event bridge
1. **Create event rule:**

**Rule_name: docdb-patch-notification_rule**

**Rule type: schedule**

<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217153322-31abafcc-c40f-4904-b817-87fb1a614e77.png">

2.	**Create event schedule:**

**Schedule_name: docdb-patch-notification-schedule (executed once a day)**

<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217153808-26803180-5ce1-47cf-9622-6ed9aafe7247.png">

**Schedule Targe: Select the created Lambda function (invoke)**

<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217154493-909176a9-6bf0-4cc5-836f-4271af5aabd0.png">

**Create successfully：**

**Once create successfully, the lambda function would be executed, then executed once a day**

## Email Notification Example：

<img width="422" alt="image" src="https://user-images.githubusercontent.com/50776512/217155276-19802738-c6a1-40cb-af8b-f755ff2d8539.png">

