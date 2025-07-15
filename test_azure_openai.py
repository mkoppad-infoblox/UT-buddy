from openai import AzureOpenAI


# Replace these with your actual values
api_key = "My API_KEY"
endpoint = "https://hackfest25.openai.azure.com/"
api_version = "2025-01-01-preview"
deployment_name = "gpt-4o"


client = AzureOpenAI(api_key=api_key,
azure_endpoint=endpoint,
api_version=api_version)

# Configure the OpenAI client

# Multi-turn conversation loop
messages = [
	{"role": "system", "content": "You are a helpful assistant."}
]

print("Type 'exit' to end the conversation.")
while True:
	user_input = input("You: ")
	if user_input.strip().lower() == "exit":
		print("Conversation ended.")
		break
	messages.append({"role": "user", "content": user_input})
	try:
		response = client.chat.completions.create(
			model=deployment_name,
			messages=messages
		)
		reply = response.choices[0].message.content
		print("Assistant:", reply)
		messages.append({"role": "assistant", "content": reply})
	except Exception as e:
		print("Error communicating with Azure OpenAI:", e)
