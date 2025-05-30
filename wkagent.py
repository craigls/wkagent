import types
import gradio as gr
import random
import asyncio
import wanikani
from dotenv import load_dotenv
from typing import AsyncGenerator
import openai

WANIKANI_MIN_SRS_STAGE = 5  # Gur
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

load_dotenv()

state = types.SimpleNamespace(
    wanikani_user=None,
    wanikani_vocab=[],
    openai_client=None,
)


def _create_prompt(learned_vocab: list[dict]) -> str:
    # Shuffling the vocabulary seems to give better results
    shuffled_vocab = random.sample(learned_vocab, k=len(learned_vocab))

    system_prompt = f"""
        You are a Japanese kanji learning assistant.
        You are given a list of vocabulary in kanji. The student has learned the words in this vocabulary using WaniKani's SRS method. 
        You should create complex sentences by randomly selecting words from the list.
        After the student responds, give a brief reply, then add additional sentences using randomly selected words from the list. 
        Continue this loop indefinitely. 
        You should not use English unless asked, or when you are correcting a student's grammar.
        You should give concise corrections only, and provide hiragana pronunciations when correcting.
        
        Here is a comma-separated vocabulary of words to use:

        {",".join([word["characters"] for word in shuffled_vocab])}
        
        Use as many words from the provided vocabulary list as possible, as the primary goal is kanji exposure.
        Do not use words outside of this list, as the student won't be able to understand them.
        However, using very basic words is OK, and these words should be written using hiragana only.

        Please start a conversation using the vocabulary list.
    """
    return system_prompt


async def _start_conversation() -> None:
    # Weird hack to send the system prompt and set the response in the chatbot
    initial = [
        message
        async for message in chat(
            [{"role": "system", "content": _create_prompt(state.wanikani_vocab)}]
        )
    ][0]
    return (gr.update(value=initial), gr.update(interactive=True))


def _load_wanikani_data() -> list[dict]:
    # TODO: What happens if user hasn't learned any words yet?
    try:
        # Pull data from WaniKani API
        state.wanikani_user = wanikani.get_user()

        # Get learned subject ids where type is kanji_vocabulary and SRS stage is "guru"
        subject_ids = [
            assignment["subject_id"]
            for (assignment_id, assignment) in wanikani.get_assignments(
                srs_stage=WANIKANI_MIN_SRS_STAGE
            )
        ]

        # Get vocabulary up to and including <level> then filter out words that haven't been learned yet.
        state.wanikani_vocab = [
            subject
            for (subject_id, subject) in wanikani.get_subjects(
                level=state.wanikani_user["level"]
            )
            if subject_id in subject_ids and subject["characters"]
        ]
    except Exception as e:
        gr.Error(f"Error loading WaniKani data: {e}")

    success = f"Success! {len(state.wanikani_vocab)} vocabulary words loaded. Your current WaniKani level is: {state.wanikani_user['level']}"
    return gr.update(value=success, interactive=True)


async def chat(history: list[dict[str, str]]) -> AsyncGenerator[str, None]:
    try:
        stream = await state.openai_client.chat.completions.create(
            model=DEFAULT_OPENAI_MODEL,
            messages=history,
            stream=True,
        )
        history.append({"role": "assistant", "content": ""})

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                history[-1]["content"] += chunk.choices[0].delta.content
                yield history
    except Exception as e:
        raise gr.Error(f"Error with chatbot: {e}")


async def main() -> None:
    state.openai_client = openai.AsyncOpenAI()

    def user_input(message, history: list):
        return ("", history + [{"role": "user", "content": message}])

    # Run Gradio's chat interface
    with gr.Blocks() as app:
        gr.Markdown(
            """
            # Japanese Kanji Learning Assistant
            ## 日本の漢字学習アシスタント
            """
        )
        submit = gr.Button("Load your WaniKani data")
        chatbot = gr.Chatbot(
            type="messages",
        )

        text = gr.Textbox(label="Write your message here:", interactive=False)
        text.submit(user_input, inputs=[text, chatbot], outputs=[text, chatbot]).then(
            chat, inputs=chatbot, outputs=chatbot
        )
        submit.click(
            lambda: gr.update(interactive=False, value="Loading..."),
            outputs=submit,
        ).then(_load_wanikani_data, outputs=submit).then(
            _start_conversation, outputs=[chatbot, text]
        )

    app.launch()


if __name__ == "__main__":
    asyncio.run(main())
