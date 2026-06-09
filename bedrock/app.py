import boto3
import json

region = boto3.Session().region_name

# Initialize the Bedrock AgentCore client
client = boto3.client('bedrock-agentcore', region_name=region)

input_text = "What places can I visit in India?"

# Make request to the agent
response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:eu-north-1:805393736710:runtime/atlas_travel_agent-YAsGEs81TC",
    qualifier="DEFAULT",
    payload=json.dumps({"prompt": input_text})
)

# Extract and display the response
raw_content = response['response'].read()
decoded_content = raw_content.decode('utf-8')

print("Raw decoded content:", repr(decoded_content))

# The content is JSON-encoded, so we need to parse it to get the actual text
if decoded_content.startswith('"') and decoded_content.endswith('"'):
    agent_response = json.loads(decoded_content)
else:
    agent_response = decoded_content

print("Agent Response:")
print(agent_response)