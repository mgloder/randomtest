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

        # Run the agent to process tne message in the thread
        run = project.agents.runs.create_and_process_run(thread_id=thread_id, agent_id=AGENT_ID)
        print(f"Run finished with status: {run.status}")

        # Check if you got "Rate limit is exceeded.", then you want to increase the token limit
        if run.status == "failed":
            raise Exception(run.last_error)

        # Get all messages from the thread
        messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)

        # Get the last message from the agent
        last_msg = messages.get_last_text_message_by_role(MessageRole.AGENT)
        if not last_msg:
            raise Exception("No response from the model.")

        msg.content = last_msg.text.value
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()


if __name__ == "__main__":
    # Chainlit will automatically run the application
    pass
