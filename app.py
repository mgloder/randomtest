import logging
import os

import chainlit as cl
from azure.ai.agents.models import ListSortOrder, MessageRole
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable verbose connection logs
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

AIPROJECT_ENDPOINT = os.getenv("AIPROJECT_ENDPOINT")
AGENT_ID = os.getenv("AGENT_ID")

# Validate required environment variables
if not AIPROJECT_ENDPOINT:
    raise ValueError("AIPROJECT_ENDPOINT environment variable is required")
if not AGENT_ID:
    raise ValueError("AGENT_ID environment variable is required")

# Create an instance of the AIProjectClient using DefaultAzureCredential
project = AIProjectClient(endpoint=AIPROJECT_ENDPOINT, credential=DefaultAzureCredential())


# Chainlit setup
@cl.on_chat_start
async def on_chat_start():
    # Create a thread for the agent
    if not cl.user_session.get("thread_id"):
        thread = project.agents.threads.create()

        cl.user_session.set("thread_id", thread.id)
        print(f"New Thread ID: {thread.id}")


@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    try:
        # Show thinking message to user
        msg = await cl.Message("thinking...", author="agent").send()

        project.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.content,
        )

        # Run the agent to process the message in the thread
        run = project.agents.runs.create_and_process(thread_id=thread_id, agent_id=AGENT_ID)
        print(f"Run finished with status: {run.status}")

        # Check if you got "Rate limit is exceeded.", then you want to increase the token limit
        if run.status == "failed":
            raise Exception(run.last_error)

        # Get all messages from the thread
        messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

        # Find the last message from the agent by iterating through the messages
        last_msg = None
        for message in messages:
            if message.role == MessageRole.AGENT:
                last_msg = message
        
        if not last_msg:
            raise Exception("No response from the model.")

        # Extract text content from the message
        text_contents = []
        for content in last_msg.content:
            if hasattr(content, 'text') and hasattr(content.text, 'value'):
                text_contents.append(content.text.value)
        
        # Join all text parts into a single string
        full_text = ' '.join(text_contents)
        msg.content = full_text
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()


if __name__ == "__main__":
    # Chainlit will automatically run the application
    pass
