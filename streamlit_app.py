import os
import streamlit as st
from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler

from openai.types.beta.assistant_stream_event import (
    ThreadRunStepCreated,
    ThreadRunStepDelta,
    ThreadRunStepCompleted,
    ThreadMessageCreated,
    ThreadMessageDelta
    )
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
from openai.types.beta.threads.runs.tool_calls_step_details import ToolCallsStepDetails
from openai.types.beta.threads.runs.code_interpreter_tool_call import (
    CodeInterpreterOutputImage,
    CodeInterpreterOutputLogs
    )


OPENAI_ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID", st.secrets["OPENAI_ASSISTANT_ID"])
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", st.secrets["OPENAI_API_KEY"])

# Moderation check
def moderation_endpoint(text) -> bool:
    """
    Checks if the text is triggers the moderation endpoint

    Args:
    - text (str): The text to check

    Returns:
    - bool: True if the text is flagged
    """
    response = client.moderations.create(input=text)
    return response.results[0].flagged


def delete_thread(thread_id) -> None:
    """
    Delete the thread

    Args:
    - thread_id (str): The id of the thread to delete
    """
    client.beta.threads.delete(thread_id)
    print(f"Deleted thread: \t {thread_id}")


# hide_streamlit_style = """
# <style>
# #MainMenu {visibility: hidden;}
# footer {visibility: hidden;}
# </style>
# """
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

#  apply custom CSS to hide the Streamlit menu, header, and footer
st.html("""
        <style>
            #MainMenu {visibility: hidden}
            #header {visibility: hidden}
            #footer {visibility: hidden}
            .block-container {
                padding-top: 3rem;
                padding-bottom: 2rem;
                padding-left: 3rem;
                padding-right: 3rem;
                }
        </style>
        """)


# Show title and greetings.
st.title("🏂 Snowboard Guru")
if "messages" not in st.session_state:
    greetings = {
        "role": "assistant",
        "items": [{
            "type": "text",
            "content": "Hi! I'm here to assist you in finding the perfect snowboard gear. Can you provide details "
                       "about your gender, riding style, experience, or budget, then we can get started?"
        }]
    }
    st.session_state["messages"] = [greetings]


# Create a new open ai thread
client = OpenAI(api_key=OPENAI_API_KEY)
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    print(st.session_state.thread_id)


# UI rendering
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "items" in message:
            for item in message["items"]:
                item_type = item["type"]
                if item_type == "text":
                    st.markdown(item["content"])
                elif item_type == "image":
                    for image in item["content"]:
                        st.html(image)
                elif item_type == "code_input":
                    with st.status("Code", state="complete"):
                        st.code(item["content"])
                elif item_type == "code_output":
                    with st.status("Results", state="complete"):
                        st.code(item["content"])

if prompt := st.chat_input("Ask me anything about snowboarding!"):
    if moderation_endpoint(prompt):
        st.toast("Your message was flagged. Please try again.", icon="⚠️")
        st.stop

    st.session_state.messages.append({"role": "user", "items": [{"type": "text","content": prompt}]})

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=OPENAI_ASSISTANT_ID,
            stream=True
        )

        assistant_output = []

        for event in stream:
            print(event)
            if isinstance(event, ThreadMessageCreated):
                assistant_output.append({"type": "text",
                                         "content": ""})
                assistant_text_box = st.empty()

            elif isinstance(event, ThreadMessageDelta):
                if isinstance(event.data.delta.content[0], TextDeltaBlock):
                    assistant_text_box.empty()
                    assistant_output[-1]["content"] += event.data.delta.content[0].text.value
                    assistant_text_box.markdown(assistant_output[-1]["content"])

        st.session_state.messages.append({"role": "assistant", "items": assistant_output})

